#!/bin/bash

import json
import socket

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util.Padding import pad, unpad
from gui.client_config import CLIENT_PID

class Communication:
    """
    Class representing a communication.

    :param hosts: ip addresses of the processes
    :param ports: ports of the processes
    :param keys: crypto keys of the processes
    :param pid: process id of the current process
    :param buffer_size: size of the communication buffer
    """

    def __init__(self, hosts, ports, keys, pid, buffer_size=1024):
        self.pid = pid
        self.host = hosts[str(pid)]
        self.port = ports[str(pid)]
        self.buffer_size = buffer_size
        self.hosts_dict = hosts
        self.ports_dict = ports
        self.keys_dict = keys
        self.n_processes = len(hosts)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))

    def __derive_key(self, base_key, salt=b"12345678", iterations=100000, key_length=16):
        """
        Derive the key from the given base key.

        :param base_key: key to derive
        """

        return PBKDF2(base_key, salt, key_length, iterations)

    def __crypt(self, message, key):
        """
        Crypt the message with the key.

        :param message: message to crypt
        :param key: key to use for the encryption
        :return: crypted message
        """

        key = self.__derive_key(key)

        try:
            cipher = AES.new(key, AES.MODE_CBC)
            ciphertext = cipher.encrypt(pad(message.encode(), AES.block_size))
            return cipher.iv + ciphertext
        except Exception as e:
            print(f"Encryption error: {e}")

    def __decrypt(self, message, key):
        """
        Decrypt the message with the key.

        :param message: message to decrypt
        :param key: key to use for the decryption
        :return: decrypted message
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

    def broadcast(self, message, include_client=False) -> None:
        """
        Broadcast the message to all the sockets.

        :param message: message to broadcast
        :param include_client: whether to include the gui in the broadcast
        """

        # for i in range(1, self.n_processes + 1):
        for pid in self.keys_dict.keys():
            pid = int(pid)
            if pid != self.pid and pid != CLIENT_PID:
                self.send(message, pid)

        if include_client:
            self.send(message, CLIENT_PID)

    def send_debug(self, message, receiver_id=None):
        """
        Send the message to the socket. It is used for debugging purposes.

        :param message: message to send
        :param receiver_id: id of the process to send the message to. If it is None send a broadcast
        """

        if receiver_id is None:
            self.broadcast(message)
            return

        self.send(message, receiver_id)


    def send(self, message, receiver_id):
        """
        Send the message to the socket.

        :param message: message to send
        :param receiver_id: id of the process to send the message to
        """

        try:
            message = json.dumps(message)
        except json.JSONDecodeError as e:
            print(f"Json decode error: {e}")

        try:
            # print(f"Sending message to {receiver_id}")
            # print(f"Host: {self.hosts_dict[str(receiver_id)]}")
            # print(f"Port: {self.ports_dict[str(receiver_id)]}")
            # print(f"Message: {message}")

            self.socket.sendto(
                self.__crypt(message, self.keys_dict[str(receiver_id)]),
                (self.hosts_dict[str(receiver_id)], self.ports_dict[str(receiver_id)])
            )

            # self.socket.sendto(
            #     message.encode(),
            #     (self.hosts_dict[str(receiver_id)], self.ports_dict[str(receiver_id)])
            # )

            print(f"({self.pid}) SEND: Message {message} sent to "
                  f"{(self.hosts_dict[str(receiver_id)], self.ports_dict[str(receiver_id)])} "
                  f"with key {self.keys_dict[str(receiver_id)]} "
                  f"from ({self.host}, {self.port})\n")

        # Send to gui
        except socket.error as e:
            print(f"Send socket error: {e}")

    def receive(self):
        """
        Receive the message from the socket.

        :return: the message received from the socket
        """

        print("Waiting for message")
        json_data = None
        sender_id = None
        try:
            data, addr = self.socket.recvfrom(self.buffer_size)
            sender_id = str(CLIENT_PID if addr[1] > 10000 else addr[1] - 8000)

            # Save unknown host and port
            if sender_id not in self.ports_dict.keys():
                self.hosts_dict[sender_id] = addr[0]
                self.ports_dict[sender_id] = addr[1]

            json_data = self.__decrypt(data, self.keys_dict[sender_id])
            json_data = json.loads(json_data)

            print(f"({self.pid}) RECEIVED: message {json_data} received from {addr}\n")

        except socket.error as e:
            if e.errno == 9 or e.errno == 10038:  # Irrelevant errors when closing the socket, only related to the socket implementation in python
                pass
            else:
                print(f"Receive socket error: {e}")
        except json.JSONDecodeError as e:
            print(f"Json decode error: {e}")
        except Exception as e:
            print(f"Receive error: {e}")
        finally:
            return json_data, sender_id

    def close(self):
        """
        Close the socket.
        """

        self.socket.close()
