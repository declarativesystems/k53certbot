import os
import certbot.main as cb
import kubernetes.client
import kubernetes.config
import kubernetes.watch
from kubernetes.client.rest import ApiException
from loguru import logger

ADDED = "ADDED"
DELETED = "DELETED"
MODIFIED = "MODIFIED"


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


def watch_kubernetes(certbot_admin_email, test_cert):
    logger.debug("loadin in-cluster kubernetes config...")
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
                        certbot_route53_tls_cert(certbot_admin_email, test_cert, data["fqdn"], data["action"])
            except ValueError as e:
                logger.warning(f"ignoring random error from kubernetes client: {e}")


def certbot_route53_tls_cert(certbot_admin_email, test_cert, fqdn, action):
    """request cert via ACME and answer DNS01 challenge via route53"""

    if action == ADDED or action == MODIFIED:
        args = [
            "certonly",
            "-n",
            "--agree-tos",
            "--email",
            certbot_admin_email,
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

    logger.info(f"running certbot {' '.join(args)}")
    # certbot doesnt provide a public API so just call `main()` to avoid shell
    # https://certbot.eff.org/docs/api/certbot.main.html
    cb.main(args)
    logger.info(f"finished certbot for {fqdn}")
