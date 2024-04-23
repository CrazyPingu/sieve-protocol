#!/bin/bash

from threading import Thread
from random import randint
from utils.communication import Communication
from gui.client_config import HOST_MAP, PORT_MAP, CLIENT_PID, CRYPTO_KEYS, BUFFER_SIZE, N_PROCESSES, CLIENT_SOCKET
from utils.utils import State
from utils.msg import MessageComposer, Message
from utils.msg_variables import MsgType
from gui.gui import Gui
from time import sleep


class Client:
    """
    Class representing the client.
    """

    def __init__(self, pid: int = CLIENT_PID, port: int = None):
        """
        Initialize the client.

        Parameters:
            port: port of the client
        """
        if pid != CLIENT_PID:
            HOST_MAP.pop(str(CLIENT_PID))
            PORT_MAP.pop(str(CLIENT_PID))
            HOST_MAP[str(pid)] = CLIENT_SOCKET[0]
            PORT_MAP[str(pid)] = CLIENT_SOCKET[1]

        self.communication = Communication(HOST_MAP, PORT_MAP, CRYPTO_KEYS, pid, BUFFER_SIZE, port)
        self.gui = None
        self.s = State.RUNNING
        self.history = None

    def run_listener(self) -> None:
        """
        Run the listener.
        """

        while self.s == State.RUNNING:
            message, sender_id = self.communication.receive()
            try:
                self.__route(message, sender_id)
            except TypeError:
                pass
            except Exception as e:
                print(f"Error in message type: {e}")

            sleep(0.01)

    def __route(self, message: Message, sender_id: int) -> None:
        """
        Route the message to the right handler.

        Parameters:
            message:
                The message to route.
            sender_id:
                The id of the sender.
        """

        self.history = sender_id, message

        match message.type:
            case MsgType.COMMIT.value:
                self.__receive_commit(message)
            case MsgType.ABORT.value:
                self.__receive_abort(message)
            case MsgType.COMPLAIN.value:
                self.__receive_complain(message)
            case MsgType.NEW_SIEVE_CONFIG.value:
                self.__receive_new_sieve_config(message)
            case MsgType.CLOSE.value:
                self.__receive_close(message)
            case MsgType.ROLLBACK.value:
                self.__receive_rollback(message)
            case MsgType.REQUEST_VALUE.value:
                self.__receive_value(message)
            case MsgType.OPERATION_NOT_QUEUED.value:
                self.__receive_operation_not_queued(message)
            case _:
                raise Exception(f"Unknown message type {message.type}")

    def __receive_operation_not_queued(self, message: Message) -> None:
        """
        Receive the notification that a requested operation won't be executed.

        Parameters:
            message: operation not queued message received
        """

        if self.gui:
            self.gui.show_operation_not_queued()
        else:
            print(f"Received operation not queued message: {message}")

    def __receive_value(self, message: Message) -> None:
        """
        Receive the value requested.

        Parameters:
            message: request value message received
        """
        key = message.generic_data[0]
        value = message.generic_data[1]

        if key is not None:
            rcv_message = (key, value)
        else:
            rcv_message = None

        if self.gui and rcv_message is not None:
            self.gui.update_table(rcv_message)
        else:
            print(f"Received value response message: {message}")

    def __receive_commit(self, message: Message) -> None:
        """
        Execute the commit.

        Parameters:
            message: commit message received
        """

        if self.gui:
            self.gui.show_commit()
        else:
            print(f"Received commit message: {message}")

    def __receive_abort(self, message: Message) -> None:
        """
        Execute the abort.

        Parameters:
            message: abort message received
        """

        if self.gui:
            self.gui.show_abort()
        else:
            print(f"Received abort message: {message}")

    def __receive_complain(self, message: Message) -> None:
        """
        Execute the complain.

        Parameters:
            message: complain message received
        """

        if self.gui:
            self.gui.show_complain()
        else:
            print(f"Received complain message: {message}")

    def __receive_new_sieve_config(self, message: Message) -> None:
        """
        Execute the new sieve config.

        Parameters:
            message: new sieve config message received
        """

        if self.gui:
            self.gui.show_new_sieve_config()
        else:
            print(f"Received new sieve config message: {message}")

    def __receive_rollback(self, message: Message) -> None:
        """
        Execute the rollback.

        Parameters:
            message: rollback message received
        """

        if self.gui:
            self.gui.show_rollback()
        else:
            print(f"Received rollback message: {message}")

    def __receive_close(self, message: Message) -> None:
        """
        Close the RSM.

        Parameters:
            message: close message received
        """

        if self.gui:
            self.gui.show_close()
        else:
            print(f"Received close message: {message}. The RSM is closing.")

    def send_start(self) -> None:
        """
        Send the start message.
        """

        self.communication.broadcast(MessageComposer.compose_start())

    def send_to_server(self, message: Message, receiver_id: int = None) -> None:
        """
        Send the invoke message to a random process, if no receiver_id is specified.

        Parameters:
            message: invoke message to send
            receiver_id: id of the receiver
        """

        self.communication.send(message, randint(1, N_PROCESSES) if receiver_id is None else receiver_id)

    def build_invoke(self, key: object, value: object) -> Message:
        """
        Build the invoke message.

        Parameters:
            key: key of the operation
            value: value of the operation

        Returns:
            The invoke message.
        """

        operation = MessageComposer.compose_operation(key, value)

        return MessageComposer.compose_client_invoke(operation)

    def request_value(self, key: object) -> None:
        """
        Request the value associated to the key.

        Parameters:
            key: key of the value to request
        """

        self.send_to_server(MessageComposer.compose_request_value(key))

    def start_gui(self) -> None:
        """
        Start the gui.
        """

        self.gui = Gui(self)
        self.gui.start()

    def close(self) -> None:
        """
        Close the gui and stops the connections.
        """

        self.s = State.CLOSING
        self.communication.close()

    def broadcast(self, message: Message) -> None:
        """
        Broadcast a message.

        Parameters:
             message: message to broadcast
        """

        self.communication.broadcast(message)


if __name__ == "__main__":
    client = Client()

    listening_thread = Thread(target=client.run_listener)
    listening_thread.start()

    client.start_gui()

    listening_thread.join()
