#!/bin/bash

import os


def get_env_variable(var_name):
    """
    Read environment variable.

    :param var_name: name of the environment variable
    """

    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = "Set the {} environment variable".format(var_name)
        raise EnvironmentError(error_msg)


# Global variables
from gui.client_config import CLIENT_PID, CLIENT_SOCKET
N_PROCESSES = int(get_env_variable("N_PROCESSES"))
N_FAULTY_PROCESSES = (N_PROCESSES - 1) // 3
BUFFER_SIZE = int(get_env_variable("BUFFER_SIZE"))
PROCESS_ID = int(get_env_variable("PROCESS_ID"))
FAULTY = int(get_env_variable("FAULTY"))
CRYPTO_KEYS = {}  # {process_id: key}
HOST_MAP = {}  # {process_id: host}
PORT_MAP = {}  # {process_id: port}

# Get crypto key values
for i in range(1, N_PROCESSES + 1):
    if i != PROCESS_ID:
        CRYPTO_KEYS[str(i)] = get_env_variable("KEY" + str(i))

    # Set port values
    PORT_MAP[str(i)] = 8000 + i
    HOST_MAP[str(i)] = "process" + str(i)

# PORT_MAP[str(CLIENT_PID)] = CLIENT_SOCKET[1]
# HOST_MAP[str(CLIENT_PID)] = CLIENT_SOCKET[0]
CRYPTO_KEYS[str(CLIENT_PID)] = str(PROCESS_ID)
