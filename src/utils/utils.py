#!/bin/bash

from time import time
from enum import Enum
from utils.msg_variables import MsgKey
from hashlib import sha256


class State(Enum):
    """
    Enum representing the state of the process.
    """

    S0 = 0  # initial state
    DELIVER_OPERATION = 1  # deliver the operation (leader)
    ELABORATION = 2  # elaborating the operation
    WAITING_APPROVAL = 3  # waiting for the approval (leader)
    COMPLAIN = 4  # complaint to the leader
    LEADER_ELECTION = 5  # send trust broadcast (leader) / waiting for trust broadcast (non-leader)
    NEW_CONFIG = 6  # sending the new config (leader) / waiting for the new config (non-leader)
    WAITING_ORDER = 7  # waiting for the order (non-leader)
    COMMIT = 8  # commit the operation
    ABORT = 9  # abort the operation
    CLOSING = 10  # closing the program
    WAITING_VALIDATION = 11  # waiting for the validation (leader)
    RUNNING = 12  # state for the gui


def check_approve(message_buffer, config, o):
    """
    Check if the message buffer contains enough equal approve messages.

    :param message_buffer: message buffer
    :param config: epoch
    :param o: operation
    :return: The list of most approve messages with the same signature
    """

    pid_count = {}

    for pid, message in message_buffer.items():
        if message[MsgKey.CONFIG.value] == config and message[MsgKey.OPERATION.value] == o:
            sign = message[MsgKey.SIGN.value]
            if sign not in pid_count.keys():
                pid_count[sign] = [pid]
            else:
                pid_count[sign].append(pid)

    pid_res = []
    max_equal_signs = 0

    for sign in pid_count.keys():
        equal_signs = len(pid_count[sign])
        if equal_signs > max_equal_signs:
            max_equal_signs = equal_signs
            pid_res = pid_count[sign]

    res = {}
    for pid in pid_res:
        res[pid] = message_buffer[pid]

    return res


def check_validation_confirm(message_buffer, res, n_faulty_processes) -> bool:
    """
    Check if the message buffer contains all equal approve messages.

    :param message_buffer: buffer of the received messages
    :param res: speculative response to validate
    :param n_faulty_processes: number of faulty processes
    :return: True if the message buffer contains all approve messages with the same signature, False otherwise
    """

    if len(message_buffer) < n_faulty_processes + 1:
        return False

    n_approve = 0
    first_message = next(iter(message_buffer.values()))

    for _, message in message_buffer.items():
        if message == first_message and verifyp(res, message[MsgKey.SIGN.value]):
            n_approve += 1

    return n_approve == len(message_buffer)


def check_validation_abort(message_buffer, n_faulty_processes, config, o) -> bool:
    """
    Check if the message buffer contains enough approve messages with incorrect signature.

    :param message_buffer: buffer of the received messages
    :param n_faulty_processes: number of faulty processes
    :param config: current epoch
    :param o: current operation
    :return: True if the message buffer contains enough approve messages with incorrect signature, False otherwise
    """

    if len(message_buffer) < (2 * n_faulty_processes) + 1:
        return False

    return len(check_approve(message_buffer, config, o)) < n_faulty_processes + 1


def remove_unwanted_messages(message_buffer, type):
    """
    Remove unwanted messages from the message buffer.

    :param message_buffer: buffer of the received messages
    :param type: type of the message to remove
    """

    res = {}

    for pid, message in message_buffer.items():
        if message[MsgKey.TYPE.value] != type:
            res[pid] = message

    return res


def encode_data(data):
    """
    Encode data into utf-8 string.

    :param data: data to encode
    :return: encoded data
    """

    return str(data).encode()

def signp(data):
    """
    Sign the data.

    :param data: data to sign
    :return: signed data
    """

    return sha256(encode_data(data)).hexdigest()


def verifyp(data, signature):
    """
    Verify the data.

    :param data: data to verify
    :param signature: signature to verify
    :return: True if the signature is valid, False otherwise
    """

    return signp(data) == signature


class OpQueue:
    """
    Class representing the operation queue. It contains the operation queue and the relative ages.
    """

    def __init__(self):
        self.queue = []
        self.ages = {}

    def add(self, op):
        """
        Add an operation to the queue.

        :param op: operation to add
        """

        self.queue.append(tuple(op))
        self.ages[tuple(op)] = time()

    def pop_left(self):
        """
        Pop the first operation in the queue.

        :return: the first operation in the queue
        """

        op = self.queue.pop(0)
        self.ages.pop(tuple(op))
        return op

    def remove(self, op):
        """
        Remove an operation from the queue.

        :param op: operation to remove
        """

        self.queue.remove(tuple(op))
        self.ages.pop(tuple(op))

    def get_first(self):
        """
        Get the first operation in the queue.

        :return: the first operation in the queue
        """

        return self.queue[0]

    def get(self, index):
        """
        Get the first operation in the queue.

        :return: the operation at the given index in the queue
        """

        return self.queue[index]

    def is_empty(self):
        """
        Check if the queue is empty.

        :return: True if the queue is empty, False otherwise
        """

        return len(self.queue) == 0

    def check_presence(self, op):
        """
        Check if the operation is in the queue.

        :param op: operation to check
        :return: True if the operation is in the queue, False otherwise
        """

        return tuple(op) in self.queue

    def get_queue(self):
        """
        Get the queue.

        :return: the queue
        """

        return self.queue

    def get_ages(self):
        """
        Get the ages.

        :return: the ages
        """

        return self.ages
