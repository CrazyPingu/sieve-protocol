#!/bin/bash

from enum import Enum
from hashlib import sha256
from time import time


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


def dict_to_list(dictionary: dict) -> list:
    """
    Convert a dictionary into a list.

    Parameters:
        dictionary: dictionary to convert

    Returns:
        the list containing the dictionary values
    """

    return list(dictionary.items())


def check_approve(message_buffer: dict, config: int, operation) -> dict:
    """
    Check if the message buffer contains enough equal approve messages.

    Parameters:
        message_buffer: buffer of the received messages
        config: current epoch
        operation: current operation

    Returns:
        The list of most approve messages with the same signature
    """

    pid_count = {}

    for pid, message in message_buffer.items():
        if message.c == config and message.o == operation:
            sign = message.sign
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


def check_validation_confirm(message_buffer: dict, res, n_faulty_processes: int) -> bool:
    """
    Check if the message buffer contains all equal approve messages.

    Parameters:
        message_buffer: buffer of the received messages
        res: speculative response to validate
        n_faulty_processes: number of faulty processes

    Returns:
        True if the message buffer contains all approve messages with the same signature, False otherwise
    """

    if len(message_buffer) < n_faulty_processes + 1:
        return False

    n_approve = 0
    first_message = next(iter(message_buffer.values()))

    for _, message in message_buffer.items():
        if message == first_message and verifyp(res, message.sign):
            n_approve += 1

    return n_approve == len(message_buffer)


def check_validation_abort(message_buffer: dict, n_faulty_processes: int, config: int, operation) -> bool:
    """
    Check if the message buffer contains enough approve messages with incorrect signature.
    
    Parameters:
        message_buffer: buffer of the received messages
        n_faulty_processes: number of faulty processes
        config: current epoch
        operation: current operation
        
    Returns:
        True if the message buffer contains enough approve messages with incorrect signature, False otherwise
    """

    if len(message_buffer) < (2 * n_faulty_processes) + 1:
        return False

    return len(check_approve(message_buffer, config, operation)) < n_faulty_processes + 1


def remove_unwanted_messages(message_buffer: dict, msg_type: int) -> dict:
    """
    Remove unwanted messages from the message buffer.

    Parameters:
        message_buffer: buffer of the received messages
        msg_type: type of the message to remove
    """

    res = {}

    for pid, message in message_buffer.items():
        if message.type != msg_type:
            res[pid] = message

    return res


def compute_correct_rs(operation) -> object:
    """
    Compute the correct response to the operation.

    Parameters:
        operation: operation to compute the response

    Returns:
        the correct response to the operation
    """

    return operation


def encode_data(data) -> bytes:
    """
    Encode data into utf-8 string.

    Parameters:
        data: data to encode

    Returns:
        encoded data
    """

    return str(data).encode()


def signp(data) -> str:
    """
    Sign the data.

    Parameters:
        data: data to sign

    Returns:
        signed data
    """

    return sha256(encode_data(data)).hexdigest()


def verifyp(data, signature) -> bool:
    """
    Verify the data.

    Parameters:
        data: data to verify
        signature: signature to verify

    Returns:
        True if the signature is valid, False otherwise
    """

    return signp(data) == signature


class OpQueue:
    """
    Class representing the operation queue to execute to update the shared dictionary.
    It contains the operation queue and the relative ages.

    Attributes:
        queue (list): list of operations to execute
        ages (dict): dictionary containing the ages of the operations
    """

    def __init__(self):
        self.queue = []
        self.ages = {}
        self.clients = {}

    def add(self, op: list, sender_id: int) -> None:
        """
        Add an operation to the queue.

        Parameters:
            op: operation to add
            sender_id: id of the client sender
        """

        self.queue.append(tuple(op))
        self.ages[tuple(op)] = time()
        self.clients[tuple(op)] = sender_id

    def pop_left(self) -> list:
        """
        Pop the first operation in the queue.

        Returns:
            the first operation in the queue
        """

        op = self.queue.pop(0)
        self.ages.pop(tuple(op))
        return op

    def remove(self, op: list) -> None:
        """
        Remove an operation from the queue.

        Parameters:
            op: operation to remove
        """

        self.queue.remove(tuple(op))
        self.ages.pop(tuple(op))

    def get_first(self) -> tuple:
        """
        Get the first operation in the queue.

        Returns:
            the first operation in the queue
        """

        return self.queue[0]

    def get(self, index: int) -> tuple:
        """
        Get the first operation in the queue.

        Parameters:
            index: index of the operation to get

        Returns:
            the operation at the given index
        """

        return self.queue[index]

    def get_client_id(self, op: list) -> int:
        """
        Get the client id of the operation.

        Parameters:
            op: operation to get the client id

        Returns:
            the client id of the operation
        """

        return self.clients[tuple(op)]

    def is_empty(self) -> bool:
        """
        Check if the queue is empty.

        Returns:
            True if the queue is empty, False otherwise
        """

        return len(self.queue) == 0

    def size(self) -> int:
        """
        Get the number of element in the queue.
        """

        return len(self.queue)

    def check_presence(self, op: list) -> bool:
        """
        Check if the operation is in the queue.

        Parameters:
            op: operation to check

        Returns:
            True if the operation is in the queue, False otherwise
        """

        return tuple(op) in self.queue

    def get_queue(self) -> list:
        """
        Get the queue.

        Returns:
            the queue
        """

        return self.queue

    def get_ages(self) -> dict:
        """
        Get the ages.

        Returns:
            the ages
        """

        return self.ages

    def reset_operations_ages(self) -> None:
        """
        Reset the age of the operations.
        """

        for op in self.get_ages():
            self.ages[op] = time()
