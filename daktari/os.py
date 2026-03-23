import logging
from os import environ

import distro


class OS:
    OS_X = "osx"
    GENERIC = "generic"
    UBUNTU = "ubuntu"


def detect_os() -> str:
    id_name, _, _ = distro.linux_distribution()
    if id_name == "Darwin":
        return OS.OS_X
    elif id_name == "Ubuntu":
        return OS.UBUNTU
    else:
        return OS.GENERIC


def check_env_var_exists(variable) -> bool:
    if environ.get(variable) is not None:
        return True
    else:
        logging.debug("Variable has returned empty", exc_info=True)
        return False


def get_env_var_value(variable) -> str:
    if environ.get(variable) is not None:
        return str(environ.get(variable))
    else:
        logging.debug("Variable is not set", exc_info=True)
        return ""
