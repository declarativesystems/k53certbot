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

"""k53certbot

Usage:
  k53certbot [--debug] [--test-cert] [--namespace <namespace>] [--provider <provider>]
  k53certbot --version

Options:
  -h --help                     Show this screen.
  --version                     Show version.
  --debug                       Extra debugging messages
  --test-cert                   Obtain a test certificate from a staging server
                                (passed to certbot command)
  --namespace <namespace>       Namespace to store TLS secrets [default: default]
  --provider <provider>         SSL signing provider (letsencrypt or zerossl)


Notes:
  * letsencrypt requires environment variable CERTBOT_ADMIN_EMAIL
  * zeross requires environment variables ZEROSSL_API_KEY and CERTBOT_ADMIN_EMAIL

"""

from loguru import logger
from docopt import docopt
import pkg_resources
import sys
import k53certbot.api as api
import os
import k53certbot.version as version


# color logs
# https://stackoverflow.com/a/56944256/3441106
def setup_logging(level, logger_name=None):
    logger_name = logger_name or __name__.split(".")[0]
    log_formats = {
        "DEBUG": "{time} {level} {message}",
        "INFO": "{message}",
    }

    logger.add(sys.stdout, format=log_formats[level], filter=logger_name, level=level)
    logger.debug("====[debug mode enabled]====")


def main():
    arguments = docopt(__doc__, version=version.version)
    setup_logging("DEBUG" if arguments['--debug'] else "INFO")
    logger.debug(f"parsed arguments: ${arguments}")
    exit_status = 1

    provider = arguments["--provider"]
    if provider not in api.cert_providers:
        raise RuntimeError(f"Invalid provider:{provider} - allowed: {api.PROVIDER_LETSENCRYPT}, {api.PROVIDER_ZEROSSL}")

    test_cert = arguments["--test-cert"] or False

    try:
        api.watch_kubernetes(provider, test_cert, arguments["--namespace"])
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.error(str(exc_value))
        if arguments['--debug']:
            logger.exception(e)

    sys.exit(exit_status)
