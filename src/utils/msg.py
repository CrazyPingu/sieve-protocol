#!/bin/bash

from utils.utils import signp
from utils.msg_variables import MsgKey, MsgType


class MessageComposer:
    """
    Class providing a message sending composer.
    """

    @staticmethod
    def compose_operation(index, value) -> tuple:
        """
        Compose an operation.

        :param index: the index of the dictionary to be updated
        :param value: the value to be inserted
        :return: the composed operation
        """

        return index, value

    @staticmethod
    def compose_client_invoke(o):
        """
        Compose a CLIENT_INVOKE message.

        :param o: operation
        :return: the message composed
        """

        message = {
            MsgKey.TYPE.value: MsgType.CLIENT_INVOKE.value,
            MsgKey.OPERATION.value: o
        }

        return message

    @staticmethod
    def compose_debug(command):
        """
        Compose a DEBUG message.

        :param command: command to execute
        :return: the message composed
        """

        message = {
            MsgKey.TYPE.value: MsgType.DEBUG.value,
            MsgKey.DEBUG_FAULTY.value: None,
            MsgKey.DEBUG_EX_TIME.value: None
        }

        message[command[0]] = command[1]

        return message

    @staticmethod
    def compose_close():
        """
        Compose a CLOSE message.

        :return: the message composed
        """

        message = {
            MsgKey.TYPE.value: MsgType.CLOSE.value
        }

        return message

    @staticmethod
    def compose_start():
        """
        Compose a START message.

        :return: the message composed
        """

        message = {
            MsgKey.TYPE.value: MsgType.START.value
        }

        return message

    @staticmethod
    def compose_validation(decision, c, o):
        """
        Compose a VALIDATION message.

        :param decision: decision of the validation
        :param c: current config (current turn)
        :param o: operation
        :return: the message composed
        """

        message = {
            MsgKey.TYPE.value: MsgType.VALIDATION.value,
            MsgKey.DECISION.value: decision,
            MsgKey.CONFIG.value: c,
            MsgKey.OPERATION.value: o
        }

        return message

    @staticmethod
    def compose_output(type, c, data):
        """
        Compose an OUTPUT message.

        :param type: type of the message
        :param c: current config (current turn)
        :param data: generic data to be sent
        :return: the message composed
        """

        message = {
            MsgKey.TYPE.value: type,
            MsgKey.CONFIG.value: c,
            MsgKey.DATA.value: data
        }

        return message

    @staticmethod
    def compose_commit(c, o):
        """
        Compose a COMMIT message.

        :param c: current config (current turn)
        :param o: operation
        :return: the message composed
        """

        message = {
            MsgKey.TYPE.value: MsgType.COMMIT.value,
            MsgKey.CONFIG.value: c,
            MsgKey.OPERATION.value: o
        }

        return message

    @staticmethod
    def compose_abort(c, o):
        """
        Compose an ABORT message.

        :param c: current config (current turn)
        :param o: operation
        :return: the message composed
        """

        message = {
            MsgKey.TYPE.value: MsgType.ABORT.value,
            MsgKey.CONFIG.value: c,
            MsgKey.OPERATION.value: o
        }

        return message

    @staticmethod
    def compose_complain(c, o, pid):
        """
        Compose a COMPLAIN message.

        :param c: current config (current turn)
        :param o: operation
        :param pid: process id of the process that sent the complain
        :return: the message composed
        """

        message = {
            MsgKey.TYPE.value: MsgType.COMPLAIN.value,
            MsgKey.CONFIG.value: c,
            MsgKey.OPERATION.value: o,
            MsgKey.PID.value: pid
        }

        return message

    @staticmethod
    def compose_invoke(c, o, pid=None):
        """
        Compose an INVOKE message.

        :param c: current config (current turn)
        :param o: operation
        :param pid: process id of the process that sent the invoke
        :return: the message composed
        """

        message = {
            MsgKey.TYPE.value: MsgType.INVOKE.value,
            MsgKey.CONFIG.value: c,
            MsgKey.OPERATION.value: o
        }

        if pid is not None:
            message[MsgKey.PID.value] = pid

        return message

    @staticmethod
    def compose_execute(c, o):
        """
        Compose an EXECUTE message.

        :param c: current config (current turn)
        :param o: operation
        :return: the message composed
        """

        message = {
            MsgKey.TYPE.value: MsgType.EXECUTE.value,
            MsgKey.CONFIG.value: c,
            MsgKey.OPERATION.value: o
        }

        return message

    @staticmethod
    def compose_approve(c, o, res):
        """
        Compose an APPROVE message.

        :param c: current config (current turn)
        :param o: operation
        :param res: result to sign
        :return: the message composed
        """

        message = {
            MsgKey.TYPE.value: MsgType.APPROVE.value,
            MsgKey.CONFIG.value: c,
            MsgKey.OPERATION.value: o,
            MsgKey.SIGN.value: res
        }

        return message

    @staticmethod
    def compose_order(decision, c, o, tc, rc, pid_set):
        """
        Compose an ORDER message.
        :param decision: decision to sign
        :param c: current config (current turn)
        :param o: operation
        :param tc: speculative state
        :param rc: speculative response
        :param pid_set: if decision == CONFIRM set of correct processes else set of all processes that replied
        :return: the message composed
        """

        message = {
            MsgKey.TYPE.value: MsgType.ORDER.value,
            MsgKey.DECISION.value: decision,
            MsgKey.CONFIG.value: c,
            MsgKey.OPERATION.value: o,
            MsgKey.S_STATE.value: tc,
            MsgKey.S_RES.value: rc,
            MsgKey.MSG_SET.value: pid_set
        }

        return message

    @staticmethod
    def compose_new_sieve_config(c, p):
        """
        Compose a NEW_SIEVE_CONFIG message.

        :param c: current config (current turn)
        :param p: next leader
        :return: the message composed
        """

        message = {
            MsgKey.TYPE.value: MsgType.NEW_SIEVE_CONFIG.value,
            MsgKey.CONFIG.value: c,
            MsgKey.PID.value: p
        }

        return message
