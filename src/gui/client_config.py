#!/bin/bash

import sys

# Global variables
CLIENT_PID = 1000
CLIENT_SOCKET = ("127.0.0.1", 8000 + CLIENT_PID)
N_PROCESSES = int(sys.argv[1]) if len(sys.argv) > 1 else 7
BUFFER_SIZE = int(sys.argv[2]) if len(sys.argv) > 2 else 2048
CRYPTO_KEYS = {}  # {process_id: key}
HOST_MAP = {}  # {process_id: host}
PORT_MAP = {}  # {process_id: port}

# Get crypto key values
for i in range(1, N_PROCESSES + 1):
    CRYPTO_KEYS[str(i)] = str(i)

    # Set port values
    PORT_MAP[str(i)] = 8000 + i
    HOST_MAP[str(i)] = "process" + str(i)

PORT_MAP[str(CLIENT_PID)] = CLIENT_SOCKET[1]
HOST_MAP[str(CLIENT_PID)] = CLIENT_SOCKET[0]
