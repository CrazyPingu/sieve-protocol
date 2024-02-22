#!/bin/bash

from enum import Enum


class MsgType(Enum):
    """
    Enum representing the type of message.
    """

    INVOKE = 0
    EXECUTE = 1
    APPROVE = 2
    ORDER = 3
    NEW_SIEVE_CONFIG = 4
    CONFIRM = 5  # decision
    ABORT = 6  # decision
    COMPLAIN = 7
    CLIENT_INVOKE = 8
    CLOSE = 9
    VALIDATION = 10
    COMMIT = 11
    START = 12
    DEBUG = 13
    ROLLBACK = 14


class MsgKey(Enum):
    """
    Enum representing the keys of the message.
    """

    TYPE = "type"
    CONFIG = "c"
    OPERATION = "o"
    PID = "p"
    SIGN = "sign"
    DECISION = "decision"
    S_STATE = "tc"  # speculative state
    S_RES = "rc"  # speculative response
    MSG_SET = "msg-set"  # set of messages
    LEADER_BUFFER = "leader-buffer"
    DEBUG_FAULTY = "debug-faulty"
    DEBUG_EX_TIME = "debug-ex-time"  # debug option for execution time simulation
    DATA = "generic-data"
