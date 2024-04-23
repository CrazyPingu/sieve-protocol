#!/bin/bash

from dataclasses import dataclass, field
from typing import Optional

from dataclasses_json import config, dataclass_json

from utils.msg_variables import MsgKey, MsgType


@dataclass_json
@dataclass
class Message:
    """
    Class representing a message.

    Attributes:
        type (int): type of the message
        c (Optional[int]): config (epoch)
        o (Optional[list]): operation
        pid (Optional[int]): process id
        sign (Optional[str]): signature of the result
        decision (Optional[int]): decision of the validation
        tc (Optional[State]): speculative state
        rc (Optional[object]): speculative response
        msg_set (Optional[object]): set of messages
        leader_buffer (Optional[object]): leader buffer
        debug_faulty (Optional[int]): debug option for faulty process simulation
        debug_ex_time (Optional[object]): debug option for execution time simulation
        generic_data (Optional[object]): generic data to be sent
    """

    type: int = field(default=None, metadata=config(field_name=MsgKey.TYPE.value))
    c: Optional[int] = field(default=None, metadata=config(field_name=MsgKey.CONFIG.value))
    o: Optional[list] = field(default=None, metadata=config(field_name=MsgKey.OPERATION.value))
    pid: Optional[int] = field(default=None, metadata=config(field_name=MsgKey.PID.value))
    sign: Optional[str] = field(default=None, metadata=config(field_name=MsgKey.SIGN.value))
    decision: Optional[int] = field(default=None, metadata=config(field_name=MsgKey.DECISION.value))
    tc: Optional[object] = field(default=None, metadata=config(field_name=MsgKey.S_STATE.value))
    rc: Optional[object] = field(default=None, metadata=config(field_name=MsgKey.S_RES.value))
    msg_set: Optional[dict] = field(default=None, metadata=config(field_name=MsgKey.MSG_SET.value,
                                                                  decoder=lambda messages: dict(
                                                                      (pid, unmarshall_message(msg)) for pid, msg in
                                                                      messages.items())))
    leader_buffer: Optional[list] = field(default=None, metadata=config(field_name=MsgKey.LEADER_BUFFER.value,
                                                                        decoder=lambda items: [dict(
                                                                            (int(pid), op) for pid, op
                                                                            in
                                                                            items[0].items()),
                                                                            items[1],
                                                                            dict(
                                                                            (tuple(item[0]), item[1]) for item
                                                                            in
                                                                            items[2])]))
    debug_faulty: Optional[int] = field(default=None, metadata=config(field_name=MsgKey.DEBUG_FAULTY.value))
    debug_ex_time: Optional[object] = field(default=None, metadata=config(field_name=MsgKey.DEBUG_EX_TIME.value))
    generic_data: Optional[object] = field(default=None, metadata=config(field_name=MsgKey.DATA.value))


class MessageComposer:
    """
    Class providing a message sending composer.
    """

    @staticmethod
    def compose_operation(index, value) -> tuple:
        """
        Compose an operation.

        Parameters:
            index: the index of the dictionary to be updated
            value: the value to be inserted

        Returns:
            the composed operation
        """

        return index, value

    @staticmethod
    def compose_client_invoke(operation) -> Message:
        """
        Compose a CLIENT_INVOKE message.

        Parameters:
            operation: the operation to be invoked

        Returns:
            the message composed
        """

        return Message(type=MsgType.CLIENT_INVOKE.value, o=operation)

    @staticmethod
    def compose_debug(command: tuple) -> Message:
        """
        Compose a DEBUG message.

        Parameters:
            command: the debug command

        Returns:
            the message composed
        """

        message = {
            MsgKey.TYPE.value: MsgType.DEBUG.value,
            MsgKey.DEBUG_FAULTY.value: False,
            MsgKey.DEBUG_EX_TIME.value: False
        }

        message[command[0]] = command[1]

        return unmarshall_message(message)

    @staticmethod
    def compose_close() -> Message:
        """
        Compose a CLOSE message.

        Returns:
            the message composed
        """

        return Message(type=MsgType.CLOSE.value)

    @staticmethod
    def compose_start() -> Message:
        """
        Compose a START message.

        Returns:
            the message composed
        """

        return Message(type=MsgType.START.value)

    @staticmethod
    def compose_validation(decision: MsgType, c: int, operation) -> Message:
        """
        Compose a VALIDATION message.

        Parameters:
            decision: decision of the validation
            c: current config (current turn)
            operation: operation to validate

        Returns:
            the message composed
        """

        return Message(type=MsgType.VALIDATION.value, decision=decision, c=c, o=operation)

    @staticmethod
    def compose_request_value(key: object) -> Message:
        """
        Compose a REQUEST_VALUE message.

        Parameters:
            key: key of the value to request

        Returns:
            the message composed
        """

        return Message(type=MsgType.REQUEST_VALUE.value, generic_data=key)

    @staticmethod
    def compose_output(msg_type: MsgType, c: int, data) -> Message:
        """
        Compose an OUTPUT message.

        Parameters:
            msg_type: type of the message
            c: current config (current turn)
            data: generic data to be sent

        Returns:
            the message composed
        """

        return Message(type=msg_type, c=c, generic_data=data)

    @staticmethod
    def compose_commit(c: int, operation) -> Message:
        """
        Compose a COMMIT message.

        Parameters:
            c: current config (current turn)
            operation: the operation to commit

        Returns:
            the message composed
        """

        return Message(type=MsgType.COMMIT.value, c=c, o=operation)

    @staticmethod
    def compose_abort(c: int, operation) -> Message:
        """
        Compose an ABORT message.

        Parameters:
            c: current config (current turn)
            operation: the operation to abort

        Returns:
            the message composed
        """

        return Message(type=MsgType.ABORT.value, c=c, o=operation)

    @staticmethod
    def compose_complain(c: int, operation, pid: int) -> Message:
        """
        Compose a COMPLAIN message.

        Parameters:
            c: current config (current turn)
            operation: the operation to complain about
            pid: process id of the process that sent the complaint

        Returns:
            the message composed
        """

        return Message(type=MsgType.COMPLAIN.value, c=c, o=operation, pid=pid)

    @staticmethod
    def compose_invoke(c: int, operation, pid=None) -> Message:
        """
        Compose an INVOKE message.

        Parameters:
            c: current config (current turn)
            operation: the operation to invoke
            pid: process id of the process that sent the message invoke

        Returns:
            the message composed
        """

        message = {
            MsgKey.TYPE.value: MsgType.INVOKE.value,
            MsgKey.CONFIG.value: c,
            MsgKey.OPERATION.value: operation
        }

        if pid is not None:
            message[MsgKey.PID.value] = pid

        return unmarshall_message(message)

    @staticmethod
    def compose_execute(c: int, operation):
        """
        Compose an EXECUTE message.

        Parameters:
            c: current config (current turn)
            operation: the operation to execute

        Returns:
            the message composed
        """

        return Message(type=MsgType.EXECUTE.value, c=c, o=operation)

    @staticmethod
    def compose_approve(c: int, operation, sign: str) -> Message:
        """
        Compose an APPROVAL message.

        Parameters:
            c: current config (current turn)
            operation: the operation to approve
            sign: signature of the result

        Returns:
            the message composed
        """

        return Message(type=MsgType.APPROVE.value, c=c, o=operation, sign=sign)

    @staticmethod
    def compose_order(decision, c: int, operation, tc: int, rc, msg_set: dict) -> Message:
        """
        Compose an ORDER message.

        Parameters:
            decision: decision to sign
            c: current config (current turn)
            operation: the operation to order
            tc: speculative state
            rc: speculative response
            msg_set: if the decision value is CONFIRM, it contains a set of correct APPROVAL messages
                else it must contain a set of all replies

        Returns:
            the message composed
        """

        return Message(type=MsgType.ORDER.value, decision=decision, c=c, o=operation, tc=tc, rc=rc, msg_set=msg_set)

    @staticmethod
    def compose_new_sieve_config(c: int, pid: int) -> Message:
        """
        Compose a NEW_SIEVE_CONFIG message.

        Parameters:
            c: current config (current turn)
            pid: next leader

        Returns:
            the message composed
        """

        return Message(type=MsgType.NEW_SIEVE_CONFIG.value, c=c, pid=pid, generic_data=False)


def marshall_message(message: Message) -> dict:
    """
    Marshall the message into json format.

    Parameters:
        message: message to marshall

    Returns:
        marshalled message
    """

    return {key: value for key, value in message.to_dict().items() if value is not None}


def unmarshall_message(message_dict: dict) -> Message:
    """
    Unmarshall the message from json format.

    Parameters:
        message_dict: message to unmarshall

    Returns:
        unmarshalled message
    """

    return Message.from_dict(message_dict)
