# Copyright 2020 Declarative Systems Pty Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import certbot.main as cb
import kubernetes.client
import kubernetes.config
import kubernetes.watch
import base64
import requests
from kubernetes.client.rest import ApiException
from loguru import logger

ADDED = "ADDED"
DELETED = "DELETED"
MODIFIED = "MODIFIED"
TLS_DIR = "/etc/letsencrypt/live"
PROVIDER_LETSENCRYPT = "letsencrypt"
PROVIDER_ZEROSSL = "zerossl"

settings = {}


def k8s_event_fqdns(event):
    fqdns = []
    if event["type"] == ADDED or event["type"] == MODIFIED or event["type"] == DELETED:

        k8s_obj = event["object"]

        for rule in k8s_obj.spec.rules:
            if rule.host:
                fqdn = rule.host
                logger.debug(f"found ingress fqdn: {fqdn}")
                fqdns.append({
                    "fqdn": fqdn,
                    "action": event["type"]
                })
    else:
        logger.warning(f"FIXME unhandled k8s event: {event}")
    return fqdns


def setup_zerossl():
    """get the external binding credentials to use for the duration this
    script runs"""
    logger.info("setting up zerossl...")
    try:
        zerossl_api_key = os.environ["ZEROSSL_API_KEY"]
    except KeyError:
        raise RuntimeError("missing environment variable ZEROSSL_API_KEY")

    response = requests.post(
        f"https://api.zerossl.com/acme/eab-credentials?access_key={zerossl_api_key}"
    )
    response_json = response.json()
    if response_json and response_json["success"]:
        settings["eab_kid"] = response_json["eab_kid"]
        settings["eab_hmac_key"] = response_json["eab_hmac_key"]
        logger.info("zerossl setup ok!")
    else:
        raise RuntimeError(f"error setting up zerossl:{response.content}")


def watch_kubernetes(cert_provider, test_cert, namespace):
    try:
        settings["email"] = os.environ["CERTBOT_ADMIN_EMAIL"]
    except KeyError:
        raise RuntimeError("missing environment variable CERTBOT_ADMIN_EMAIL")

    if cert_provider == PROVIDER_ZEROSSL:
        setup_zerossl()

    logger.debug("loading in-cluster kubernetes config...")
    kubernetes.config.load_incluster_config()
    logger.debug("...done")


    with kubernetes.client.ApiClient() as api_client:
        # scan all ingress instances
        api_instance = kubernetes.client.ExtensionsV1beta1Api(api_client)
        _continue = '_continue_example'
        limit = 56
        timeout_seconds = 56
        logger.debug("starting watch kubernetes...")
        w = kubernetes.watch.Watch()

        while True:
            try:
                logger.debug("(re)start streaming....")
                for event in w.stream(
                        api_instance.list_ingress_for_all_namespaces,
                        # allow_watch_bookmarks=allow_watch_bookmarks,
                        # _continue=_continue,
                        # field_selector=field_selector,
                        limit=limit,
                        pretty=True,
                        #timeout_seconds=timeout_seconds,
                        watch=True,
                ):
                    logger.debug(f"kubernetes event: {event}")
                    # its only possible to filter on metadata so we need to get all ingress
                    # changes and loop over them to find ones we need to act on
                    for data in k8s_event_fqdns(event):
                        cert_providers[cert_provider](test_cert, data["fqdn"], data["action"])
                        ensure_k8s_secret(api_client, namespace, data["fqdn"])

            except Exception as e:
                logger.error(f"FIXME caught and ignored:{type(e)} - message:{e} (to avoid crash)")


def dump_file_base64(filename):
    with open(filename, 'r') as file:
        data = file.read()

    string_bytes = data.encode('ascii')
    base64_bytes = base64.b64encode(string_bytes)
    return base64_bytes.decode('ascii')


def ensure_k8s_secret(api_client, namespace, fqdn):
    """create/update kubernetes secret from the certificate files"""

    # secrets with periods do weird shit unless u reconfigure stuffs
    # https://github.com/datawire/ambassador/issues/1255
    fqdn_safe = fqdn.replace(".", "-")
    secret_name = f"tls-{fqdn_safe}"
    logger.debug(f"creating secret:{secret_name}")

    api_instance = kubernetes.client.CoreV1Api(api_client)

    # step 1 - get the existing secret (if any)
    try:
        existing_secret = api_instance.read_namespaced_secret(
            secret_name,
            namespace,
            pretty=True,
            exact=True,
        )
        logger.debug(f"existing secret: {existing_secret}")
        logger.info(f"removing existing secret: {existing_secret}")

        delete_secret = api_instance.delete_namespaced_secret(
            secret_name,
            namespace,
            pretty=True,
        )
        logger.debug(f"delete existing secret response:{delete_secret}")
    except Exception as e:
        logger.error(f"FIXME exception type:{type(e)} - {e}")
        logger.debug("secret doesn't exist yet...")

    body = kubernetes.client.V1Secret(
        metadata={
            "name": secret_name,
            # "namespace": namespace,
        },
        data={
            # "ca.crt": dump_file_base64(f"{TLS_DIR}/{fqdn}/.pem"),
            "tls.crt": dump_file_base64(f"{TLS_DIR}/{fqdn}/fullchain.pem"),
            "tls.key": dump_file_base64(f"{TLS_DIR}/{fqdn}/privkey.pem")
        },
        type="kubernetes.io/tls",
    )
    resp = api_instance.create_namespaced_secret(
        namespace,
        body,
        pretty=True,
    )
    logger.debug(f"secret created! {resp}")


def run_certbot(args):
    logger.info(f"running certbot {' '.join(args)}")
    # certbot doesnt provide a public API so just call `main()` to avoid shell
    # https://certbot.eff.org/docs/api/certbot.main.html
    cb.main(args)
    logger.info(f"finished certbot!")


def ensure_letsencrypt_cert(test_cert, fqdn, action):
    """request cert via ACME and answer DNS01 challenge via route53 - letsencrypt"""

    if action == ADDED or action == MODIFIED:
        args = [
            "certonly",
            "-n",
            "--agree-tos",
            "--email",
            settings["email"],
            "--dns-route53",
            "-d",
            fqdn,
        ]
    elif action == DELETED:
        args = [
            "delete",
            "-n",
            "-d",
            fqdn,
            "--cert-name",
            fqdn,
        ]
    else:
        raise RuntimeError(f"Invalid action for certbot command: {action}")
    if test_cert:
        args.append("--test-cert")

    run_certbot(args)


def ensure_zerossl_cert(test_cert, fqdn, action):
    """request cert via ACME and answer DNS01 challenge via route53 - zerossl"""

    if action == ADDED or action == MODIFIED:
        args = [
            "certonly",
            "-n",
            "--server",
            "https://acme.zerossl.com/v2/DV90",
            "--agree-tos",
            "--email",
            settings["email"],
            "--eab-kid",
            settings["eab_kid"],
            "--eab-hmac-key",
            settings["eab_hmac_key"],
            "--dns-route53",
            "-d",
            fqdn,
        ]
    elif action == DELETED:
        args = [
            "delete",
            "-n",
            "--server",
            "https://acme.zerossl.com/v2/DV90",
            "-d",
            fqdn,
            "--cert-name",
            fqdn,
        ]
    else:
        raise RuntimeError(f"Invalid action for certbot command: {action}")
    if test_cert:
        args.append("--test-cert")

    run_certbot(args)


cert_providers = {
    PROVIDER_LETSENCRYPT: ensure_letsencrypt_cert,
    PROVIDER_ZEROSSL: ensure_zerossl_cert,
}

