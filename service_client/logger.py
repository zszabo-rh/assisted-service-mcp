# -*- coding: utf-8 -*-
import logging
import os
import re
import sys


class SensitiveFormatter(logging.Formatter):
    """Formatter that removes sensitive info."""

    @staticmethod
    def _filter(s):
        # Dict filter
        s = re.sub(r"('_pull_secret':\s+)'(.*?)'", r"\g<1>'*** PULL_SECRET ***'", s)
        s = re.sub(r"('_ssh_public_key':\s+)'(.*?)'", r"\g<1>'*** SSH_KEY ***'", s)
        s = re.sub(
            r"('_vsphere_username':\s+)'(.*?)'", r"\g<1>'*** VSPHERE_USER ***'", s
        )
        s = re.sub(
            r"('_vsphere_password':\s+)'(.*?)'", r"\g<1>'*** VSPHERE_PASSWORD ***'", s
        )

        # Object filter
        s = re.sub(
            r"(pull_secret='[^']*(?=')')", "pull_secret = *** PULL_SECRET ***", s
        )
        s = re.sub(
            r"(ssh_public_key='[^']*(?=')')", "ssh_public_key = *** SSH_KEY ***", s
        )
        s = re.sub(
            r"(vsphere_username='[^']*(?=')')",
            "vsphere_username = *** VSPHERE_USER ***",
            s,
        )
        s = re.sub(
            r"(vsphere_password='[^']*(?=')')",
            "vsphere_password = *** VSPHERE_PASSWORD ***",
            s,
        )

        return s

    def format(self, record):
        original = logging.Formatter.format(self, record)
        return self._filter(original)


def get_logging_level():
    level = os.environ.get("LOGGING_LEVEL", "")
    return logging.getLevelName(level.upper()) if level else logging.INFO


logging.getLogger("requests").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("asyncio").setLevel(logging.ERROR)


def add_log_file_handler(logger: logging.Logger, filename: str) -> logging.FileHandler:
    fmt = SensitiveFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(thread)d:%(process)d - %(message)s"
    )
    fh = logging.FileHandler(filename)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return fh


def add_stream_handler(logger: logging.Logger):
    fmt = SensitiveFormatter(
        "%(asctime)s  %(name)s %(levelname)-10s - %(thread)d - %(message)s \t"
        "(%(pathname)s:%(lineno)d)->%(funcName)s"
    )
    ch = logging.StreamHandler(sys.stderr)
    ch.setFormatter(fmt)
    logger.addHandler(ch)


logger_name = os.environ.get("LOGGER_NAME", "")
urllib3_logger = logging.getLogger("urllib3")
urllib3_logger.handlers = [logging.NullHandler()]

logging.getLogger("requests").setLevel(logging.ERROR)
urllib3_logger.setLevel(logging.ERROR)

log = logging.getLogger(logger_name)
log.setLevel(get_logging_level())

add_log_file_handler(log, "assisted-service-mcp.log")
add_log_file_handler(urllib3_logger, "assisted-service-mcp.log")
add_stream_handler(log)
add_stream_handler(urllib3_logger)
