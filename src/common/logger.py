import logging
import os
import socket
import sys
from logging.handlers import RotatingFileHandler

PLATFORM_ENV = os.environ.get('PLATFORM_ENV', 'development').lower()
TEST_MODE = PLATFORM_ENV == "test"

LOG_FILE = "pencil_model_server.log"
HOSTNAME = os.environ.get("DOCKER_HOSTNAME", socket.gethostname())


class DistributedLogger(object):
    _tag = ""
    _silent = False

    @property
    def logger(self):
        return self._logger

    @logger.setter
    def logger(self, logger):
        self._logger = logger

    @property
    def tag(self):
        return self._tag

    @tag.setter
    def tag(self, tag):
        self._tag = tag

    @property
    def silent(self):
        return self._silent

    @silent.setter
    def silent(self, silent):
        self._silent = silent

    def log(self, level, msg, *args, **kwargs):
        self._logger.log(level, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        msg = f"{self._tag}::{msg}"
        if not self._silent:
            self._logger.info(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        msg = f"{self._tag}::{msg}"
        if not self._silent:
            self._logger.debug(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        msg = f"{self._tag}::{msg}"
        if not self._silent:
            self._logger.error(msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        msg = f"{self._tag}::{msg}"
        if not self._silent:
            self._logger.warning(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        msg = f"{self._tag}::{msg}"
        if not self._silent:
            self._logger.warning(msg, *args, **kwargs)


log_wrapper = DistributedLogger()


def get_formatter():
    formatter = "%(asctime)s — %(name)s — %(levelname)s — %(message)s"
    env = os.environ.get('PLATFORM_ENV', "dev")
    if env in ["staging", "production"]:
        formatter = "%(levelname)s — %(message)s"

    return formatter


def get_console_handler(formatter):
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(formatter))
    return console_handler


def get_file_handler(formatter):
    file_handler = RotatingFileHandler(
        '/tmp/' + LOG_FILE, maxBytes=(20 * 1000 * 1000), backupCount=20)
    file_handler.setFormatter(logging.Formatter(formatter))
    return file_handler


def get_local_file_handler(formatter):
    os.makedirs('tmp/', exist_ok=True)
    file_handler = RotatingFileHandler(
        'tmp/' + LOG_FILE, maxBytes=(20 * 1000 * 1000), backupCount=20)
    file_handler.setFormatter(logging.Formatter(formatter))
    return file_handler


def get_logger(logger_name='log'):
    root_logger = logging.getLogger(logger_name)
    root_logger.setLevel(logging.INFO)

    if not root_logger.handlers:
        formatter = get_formatter()

        try:
            root_logger.addHandler(get_file_handler(formatter))
        except:
            pass

        root_logger.addHandler(get_console_handler(formatter))

        if not TEST_MODE:
            try:
                root_logger.addHandler(get_local_file_handler(formatter))
            except:
                pass

        # with this pattern, it's rarely necessary to propagate the error up to parent
        root_logger.propagate = False

    log_wrapper.logger = root_logger
    return log_wrapper


def set_logger_tag(log_tag):
    log_wrapper.tag = log_tag


def set_logger_silent(log_silent):
    log_wrapper.silent = log_silent
