#!/bin/bash

from threading import Thread
from random import randint
from utils.communication import Communication
from gui.client_config import HOST_MAP, PORT_MAP, CLIENT_PID, CRYPTO_KEYS, BUFFER_SIZE, N_PROCESSES
from utils.utils import State
from utils.msg import MessageComposer
from utils.msg_variables import MsgType, MsgKey
from gui.gui import GuiGenerator
from time import sleep


class Client:
    """
    Class representing a gui.
    """

    def __init__(self):
        self.communication = Communication(HOST_MAP, PORT_MAP, CRYPTO_KEYS, CLIENT_PID, BUFFER_SIZE)
        self.gui = None
        self.s = State.RUNNING
        self.dictionary = {}
        self.history = None

    def run_listener(self):
        """
        Run the listener.
        """

        while self.s == State.RUNNING:
            message, sender_id = self.communication.receive()
            try:
                self.route(message, sender_id)
            except TypeError as e:
                pass
            except Exception as e:
                print(f"Error in message type: {e}")

            sleep(0.01)

    def route(self, message, sender_id):
        """
        Route the message to the right handler.

        :param message: message to route
        :param sender_id: id of the sender
        """

        self.history = sender_id, message

        if message["type"] == MsgType.COMMIT.value:
            self.__receive_commit(message)
        elif message["type"] == MsgType.ABORT.value:
            self.__receive_abort(message)
        elif message["type"] == MsgType.COMPLAIN.value:
            self.__receive_complain(message)
        elif message["type"] == MsgType.NEW_SIEVE_CONFIG.value:
            self.__receive_new_sieve_config(message)
        elif message["type"] == MsgType.CLOSE.value:
            self.__receive_close(message)
        elif message["type"] == MsgType.ROLLBACK.value:
            self.__receive_rollback(message)
        else:
            raise Exception(f"Unknown type {message['type']}")

    def __receive_commit(self, message):
        """
        Receive the commit message.

        :param message: message to receive
        """

        self.dictionary[message[MsgKey.OPERATION.value][0]] = message[MsgKey.OPERATION.value][1]

        if self.gui:
            self.gui.show_commit()
            self.gui.update_table(self.dictionary)
        else:
            print(f"Received commit message: {message}")

    def __receive_abort(self, message):
        """
        Receive the abort message.

        :param message: message to receive
        """

        if self.gui:
            self.gui.show_abort()
        else:
            print(f"Received abort message: {message}")

    def __receive_complain(self, message):
        """
        Receive the complain message.

        :param message: message to receive
        """

        if self.gui:
            self.gui.show_complain()
        else:
            print(f"Received complain message: {message}")

    def __receive_new_sieve_config(self, message):
        """
        Receive the new sieve config message.

        :param message: message to receive
        """

        if self.gui:
            self.gui.show_new_sieve_config()
        else:
            print(f"Received new sieve config message: {message}")

    def __receive_rollback(self, message):
        """
        Receive the rollback message.

        :param message: message to receive
        """

        if self.gui:
            self.gui.show_rollback()
        else:
            print(f"Received rollback message: {message}")

    def __receive_close(self, message):
        """
        Receive the close message.

        :param message: message to receive
        """

        if self.gui:
            self.gui.show_close()
        else:
            print(f"Received close message: {message}. The RSM is closing.")

    def send_start(self):
        """
        Send the start message.
        """

        self.communication.broadcast(MessageComposer.compose_start())

    def send_invoke(self, message, receiver_id=None):
        """
        Send the invoke message to a random process.

        :param message: message to send
        """

        self.communication.send(message, randint(1, N_PROCESSES) if receiver_id is None else receiver_id)

    def build_invoke(self, key, value):
        """
        Build the invoke message.

        :param operation: operation to perform
        :return: the invoke message
        """

        operation = MessageComposer.compose_operation(key, value)

        return MessageComposer.compose_client_invoke(operation)

    def start_gui(self):
        """
        Start the gui.
        """

        self.gui = GuiGenerator(self)
        self.gui.start()

    def close(self):
        """
        Close the gui.
        """

        self.s = State.CLOSING
        self.communication.close()

    def broadcast(self, message):
        """
        Broadcast the message.

        :param message: message to broadcast
        """

        self.communication.broadcast(message)


if __name__ == "__main__":
    client = Client()

    listening_thread = Thread(target=client.run_listener)
    listening_thread.start()

    client.start_gui()

    listening_thread.join()
