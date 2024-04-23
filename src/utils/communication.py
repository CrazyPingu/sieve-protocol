#!/bin/bash

import json
import socket

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util.Padding import pad, unpad

from gui.client_config import CLIENT_PID
from utils.msg import Message, marshall_message, unmarshall_message


class Communication:
    """
    Class wrapping the communication between the processes.


    Attributes:
        pid (int): process id of the current process
        host (str): ip address of the current process
        port (int): port of the current process
        buffer_size (int): size of the communication buffer
        hosts_dict : dictionary that contains the process id as key and the ip address as value
        ports_dict: dictionary that contains the process id as key and the port as value
        keys_dict: dictionary that contains the process id as key and the crypto key as value
        n_processes: number of processes
        socket: socket used for the communication
    """

    def __init__(self, hosts: dict, ports: dict, keys: dict, pid: int, buffer_size: int = 1024, port: int = None):
        """
        Initialize the communication class.

        Parameters:
            hosts: dictionary that contains the process id as key and the ip address as value
            ports: dictionary that contains the process id as key and the port as value
            keys: dictionary that contains the process id as key and the crypto key as value
            pid: process id of the current process
            buffer_size: size of the communication buffer
        """
        self.pid = pid
        self.host = hosts[str(pid)]
        self.port = ports[str(pid)] if port is None else port
        self.buffer_size = buffer_size
        self.hosts_dict = hosts
        self.ports_dict = ports
        self.keys_dict = keys
        self.n_processes = len(hosts)
        self.n_clients = 0

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))

    def __derive_key(self, base_key: str, salt: bytes = b"12345678", iterations: int = 100000,
                     key_length: int = 16) -> bytes:
        """
        Derive the key from the given base key.

        Parameters:
            base_key: base key to derive the key from
            salt: salt to use for the derivation
            iterations: number of iterations to use for the derivation
            key_length: length of the key to derive

        Returns:
            new key derived from the base key
        """

        return PBKDF2(base_key, salt, key_length, iterations)

    def __encrypt(self, message: str, key: str) -> bytes:
        """
        Encrypt the message with the key.

        Parameters:
            message: message to encrypt
            key: key to use for the encryption

        Returns:
            new encrypted message

        """

        key = self.__derive_key(key)

        try:
            cipher = AES.new(key, AES.MODE_CBC)
            ciphertext = cipher.encrypt(pad(message.encode(), AES.block_size))
            return cipher.iv + ciphertext
        except Exception as e:
            print(f"Encryption error: {e}")

    def __decrypt(self, message: bytes, key: str) -> str:
        """
        Decrypt the message with the key.

        Parameters:
            message: message to decrypt
            key: key to use for the decryption

        Returns:
            decrypted message
        """

        key = self.__derive_key(key)

        try:
            iv = message[:AES.block_size]
            cipher = AES.new(key, AES.MODE_CBC, iv)
            plaintext = unpad(cipher.decrypt(message[AES.block_size:]), AES.block_size)
            return plaintext.decode()
        except ValueError as e:
            print(f"Unpadding error: {e}")
        except Exception as e:
            print(f"Decryption error: {e}")

    def broadcast(self, message: Message, include_client: bool = False) -> None:
        """
        Broadcast the message to all the sockets.

        Parameters:
            message: message to broadcast
            include_client: whether to include the client in the broadcast
        """

        for pid in self.keys_dict.keys():
            pid = int(pid)
            if pid != self.pid and (pid < CLIENT_PID or include_client):
                self.send(message, pid)

    def broadcast_to_clients(self, message: Message) -> None:
        """
        Broadcast the message only to client sockets.

        Parameters:
            message: message to broadcast
        """

        for pid in self.keys_dict.keys():
            pid = int(pid)
            if pid != self.pid and pid >= CLIENT_PID:
                self.send(message, pid)

    def send_debug(self, message: Message, receiver_id: int = None) -> None:
        """
        Send the message to the socket. It is used for debugging purposes.

        Parameters:
            message: message to send
            receiver_id: id of the process to send the message to. If it is None send a broadcast
        """

        if receiver_id is None:
            self.broadcast(message)
            return

        self.send(message, receiver_id)

    def send(self, message: Message, receiver_id: int) -> None:
        """
        Send the message to the socket.

        Parameters:
            message: message to send
            receiver_id: id of the process to send the message to
        """

        try:
            message = json.dumps(marshall_message(message))
        except json.JSONDecodeError as e:
            print(f"Json decode error: {e}")

        try:
            self.socket.sendto(
                self.__encrypt(message, self.keys_dict[str(receiver_id)]),
                (self.hosts_dict[str(receiver_id)], self.ports_dict[str(receiver_id)])
            )

            print(f"({self.pid}) SEND: Message {message} sent to "
                  f"{(self.hosts_dict[str(receiver_id)], self.ports_dict[str(receiver_id)])} "
                  f"with key {self.keys_dict[str(receiver_id)]} "
                  f"from ({self.host}, {self.port})\n")
        except socket.error as e:
            print(f"Send socket error: {e}")

    def receive(self) -> (Message, str):
        """
        Receive the message from the socket.

        Returns:
            the message received from the socket and the id of the process that sent the message
        """

        print("Waiting for message")
        message = None
        sender_id = None
        try:
            data, addr = self.socket.recvfrom(self.buffer_size)

            if addr[1] > 10000 and addr[1] in self.ports_dict.values():
                sender_id = list(self.ports_dict.keys())[list(self.ports_dict.values()).index(addr[1])]
            else:
                sender_id = str(CLIENT_PID + self.n_clients if addr[1] > 10000 else addr[1] - 8000)
                self.n_clients = int(sender_id) - CLIENT_PID + 1

            # Save unknown host and port
            if sender_id not in self.ports_dict.keys():
                self.hosts_dict[sender_id] = addr[0]
                self.ports_dict[sender_id] = addr[1]
                self.keys_dict[sender_id] = str(self.pid)

            json_data = self.__decrypt(data, self.keys_dict[sender_id])
            json_data = json.loads(json_data)
            message = unmarshall_message(json_data)

            print(f"({self.pid}) RECEIVED: message {message} received from {addr}\n")

        except socket.error as e:
            # Irrelevant errors when closing the socket, only related to the socket implementation in python
            if e.errno == 9 or e.errno == 10038:
                pass
            else:
                print(f"Receive socket error: {e}")
        except json.JSONDecodeError as e:
            print(f"Json decode error: {e}")
        except Exception as e:
            print(f"Receive error: {e}")
        finally:
            return message, sender_id

    def close(self) -> None:
        """
        Close the socket.
        """

        self.socket.close()
