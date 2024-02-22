#!/bin/bash

import unittest
from gui.common import run_docker_compose, stop_docker_compose, check_containers
from utils.msg import MessageComposer
from client import Client
from utils.msg_variables import MsgType, MsgKey
from threading import Thread
from time import sleep


class SieveTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.thread = None

    def setUp(cls):
        # Start Docker Compose for testing
        run_docker_compose("docker-compose.yaml")

        cls.client = Client()

        cls.thread = Thread(target=cls.client.run_listener)
        cls.thread.start()

        cls.client.send_start()

    def tearDown(cls):
        # Stop Docker Compose after testing
        stop_docker_compose()

        cls.client.close()
        cls.thread.join()

    # def test_commit(self):
    #     # Set execution time simulation to 0 seconds
    #     debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (10, 10, 0)))
    #     self.client.broadcast(debug_message)

    #     # Send an invoke message
    #     message = self.client.build_invoke("a", 1)
    #     self.client.send_invoke(message)

    #     while not self.client.history:
    #         sleep(0.01)

    #     self.assertEqual(self.client.history[1][MsgKey.TYPE.value], MsgType.COMMIT.value)

    # def test_abort(self):
    #     # Set execution time simulation to 0 seconds
    #     debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (10, 10, 0)))
    #     self.client.broadcast(debug_message)

    #     # Set faulty processes to ensure abort (f > n/3)
    #     debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_FAULTY.value, 100))
    #     faulty_processes = [3, 4, 5, 6, 7]
    #     for pid in faulty_processes:
    #         self.client.communication.send(debug_message, pid)

    #     # Send an invoke message
    #     message = self.client.build_invoke("a", 1)
    #     self.client.send_invoke(message)

    #     self.client.history = 1, MessageComposer.compose_output(MsgType.ROLLBACK.value, 1, ("b", 2))

    #     while self.client.history[1][MsgKey.TYPE.value] == MsgType.ROLLBACK.value:
    #         sleep(0.01)

    #     self.assertEqual(self.client.history[1][MsgKey.TYPE.value], MsgType.ABORT.value)

    # def test_rollback(self):
    #     # Set execution time simulation to 0 seconds
    #     debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (10, 10, 0)))
    #     self.client.broadcast(debug_message)

    #     # Set faulty processes to ensure abort (f > n/3)
    #     debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_FAULTY.value, 100))
    #     faulty_processes = [3, 4, 5, 6, 7]
    #     for pid in faulty_processes:
    #         self.client.communication.send(debug_message, pid)

    #     # Send an invoke message
    #     message = self.client.build_invoke("a", 1)
    #     self.client.send_invoke(message)

    #     while not self.client.history:
    #         sleep(0.01)

    #     self.assertEqual(self.client.history[1][MsgKey.TYPE.value], MsgType.ROLLBACK.value)

    # def test_complain(self):
    #     # Set execution time simulation to over complain threshold
    #     debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (1, 1, 10)))
    #     self.client.broadcast(debug_message)

    #     # Send an invoke message
    #     message = self.client.build_invoke("a", 1)
    #     self.client.send_invoke(message, 6)

    #     while not self.client.history:
    #         sleep(0.01)

    #     self.assertEqual(self.client.history[1][MsgKey.TYPE.value], MsgType.COMPLAIN.value)

    def test_new_sieve_config(self):
        # Set execution time simulation to 0 seconds
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (10, 10, 0)))
        self.client.broadcast(debug_message)

        # Set faulty processes to ensure abort (f > n/3)
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_FAULTY.value, 100))
        faulty_processes = [3, 4, 5, 6, 7]
        for pid in faulty_processes:
            self.client.communication.send(debug_message, pid)

        # Send an invoke message
        for i in range(3):
            message = self.client.build_invoke("a", i)
            self.client.send_invoke(message)

        self.client.history = 1, MessageComposer.compose_output(MsgType.ROLLBACK.value, 1, ("b", 2))

        while self.client.history[1][MsgKey.TYPE.value] == MsgType.COMPLAIN.value or self.client.history[1][MsgKey.TYPE.value] == MsgType.ROLLBACK.value or self.client.history[1][MsgKey.TYPE.value] == MsgType.ABORT.value:
            sleep(0.01)

        self.assertEqual(self.client.history[1][MsgKey.TYPE.value], MsgType.NEW_SIEVE_CONFIG.value)
        self.assertFalse(self.client.history[0] == 1)
        self.assertFalse(self.client.history[1][MsgKey.DATA.value][0] == 1)
        self.assertEqual(int(self.client.history[0]), self.client.history[1][MsgKey.DATA.value][0])
        self.assertTrue(self.client.history[1][MsgKey.DATA.value][1])

    # def test_close(self):
    #     message = MessageComposer.compose_close()
    #     self.client.broadcast(message)

    #     sleep(3)

    #     self.assertEqual(check_containers("sieve-process:latest"), False)


if __name__ == "__main__":
    unittest.main()
