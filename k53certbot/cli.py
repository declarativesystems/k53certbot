"""k53certbot

Usage:
  k53certbot [--debug] [--test-cert] [--certbot-admin-email <email>]
  k53certbot --version

Options:
  -h --help             Show this screen.
  --version             Show version.
  --debug               Extra debugging messages
  --test-cert           Obtain a test certificate from a staging server
                        (passed to certbot command)
  --certbot-admin-email Use this email address when registering certificates
                        default is to use environment variable:
                        CERTBOT_ADMIN_EMAIL
"""

from loguru import logger
from docopt import docopt
import traceback
import pkg_resources
import sys
import k53certbot.api as api
import os



# color logs
# https://stackoverflow.com/a/56944256/3441106
def setup_logging(level, logger_name=None):
    logger_name = logger_name or __name__.split(".")[0]
    log_formats = {
        "DEBUG": "{time} {level} {message}",
        "INFO": "{message}",
    }


    logger.remove()
    logger.add(sys.stdout, format=log_formats[level], filter=logger_name, level=level)
    logger.debug("====[debug mode enabled]====")


def version():
    return pkg_resources.require("k53certbot")[0].version


def main():
    arguments = docopt(__doc__, version=pkg_resources.require("k53certbot")[0].version)
    setup_logging("DEBUG" if arguments['--debug'] else "INFO")
    logger.debug(f"parsed arguments: ${arguments}")
    exit_status = 1

    certbot_admin_email = arguments["--certbot-admin-email"] or os.environ.get("CERTBOT_ADMIN_EMAIL")
    if not certbot_admin_email:
        raise RuntimeError("Must supply one of --certbot-admin-email or environment variable CERTBOT_ADMIN_EMAIL")

    test_cert = arguments["--test-cert"] or False

    try:
        api.watch_kubernetes(certbot_admin_email, test_cert)
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.error(str(exc_value))
        if arguments['--debug']:
            logger.exception(e)

    sys.exit(exit_status)
