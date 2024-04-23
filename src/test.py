#!/bin/bash

import unittest
from gui.common import run_docker_compose, stop_docker_compose, check_containers
from utils.msg import MessageComposer
from client import Client
from utils.msg_variables import MsgType, MsgKey
from threading import Thread
from time import sleep


class SieveTest(unittest.TestCase):
    """
    Class for testing the Sieve protocol.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.thread = None

    def setUp(self):
        # Start Docker Compose for testing
        run_docker_compose("../docker-compose.yaml")

        self.client = Client()

        self.thread = Thread(target=self.client.run_listener)
        self.thread.start()

        # Send the start message
        for i in range(2):
            self.client.send_start()

    def tearDown(self):
        # Stop Docker Compose after testing
        stop_docker_compose()

        self.client.close()
        self.thread.join()

    def test_commit(self):
        """
        Test the functionality of the commit.
        """
        # Set execution time simulation to 0 seconds
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (10, 10, 0)))
        self.client.broadcast(debug_message)

        # Send an invoke message
        message = self.client.build_invoke("a", 1)
        self.client.send_to_server(message)

        while not self.client.history:
            sleep(0.01)

        self.assertEqual(MsgType.COMMIT.value, self.client.history[1].type)

    def test_abort(self):
        """
        Test the functionality of the abort.
        """
        # Set execution time simulation to 0 seconds
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (10, 10, 0)))
        self.client.broadcast(debug_message)

        # Set faulty processes to ensure abort (f > n/3)
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_FAULTY.value, 100))
        faulty_processes = [3, 4, 5, 6, 7]
        for pid in faulty_processes:
            self.client.communication.send(debug_message, pid)

        # Send an invoke message
        message = self.client.build_invoke("a", 1)
        self.client.send_to_server(message)

        self.client.history = 1, MessageComposer.compose_output(MsgType.ROLLBACK.value, 1, ("b", 2))

        while self.client.history[1].type == MsgType.ROLLBACK.value:
            sleep(0.01)

        self.assertEqual(MsgType.ABORT.value, self.client.history[1].type)

    def test_rollback(self):
        """
        Test the functionality of the rollback.
        """
        # Set execution time simulation to 0 seconds
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (10, 10, 0)))
        self.client.broadcast(debug_message)

        # Set faulty processes to ensure abort (f > n/3)
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_FAULTY.value, 100))
        faulty_processes = [3, 4, 5, 6, 7]
        for pid in faulty_processes:
            self.client.communication.send(debug_message, pid)

        # Send an invoke message
        message = self.client.build_invoke("a", 1)
        self.client.send_to_server(message)

        while not self.client.history:
            sleep(0.01)

        self.assertEqual(MsgType.ROLLBACK.value, self.client.history[1].type)

    def test_complain(self):
        """
        Test the functionality of the complaint.
        """
        # Set execution time simulation to over complain threshold
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (1, 1, 10)))
        self.client.broadcast(debug_message)

        # Send an invoke message
        message = self.client.build_invoke("a", 1)
        self.client.send_to_server(message, 6)

        while not self.client.history:
            sleep(0.01)

        self.assertEqual(MsgType.COMPLAIN.value, self.client.history[1].type)

    def test_new_sieve_config_after_abort(self):
        """
        Test what happens when the leader is changed after an abort (new sieve config).
        """
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
            self.client.send_to_server(message, i + 1)

        self.client.history = 1, MessageComposer.compose_output(MsgType.ROLLBACK.value, 1, ("b", 2))

        while (self.client.history[1].type == MsgType.COMPLAIN.value
               or self.client.history[1].type == MsgType.ROLLBACK.value
               or self.client.history[1].type == MsgType.ABORT.value
               or self.client.history[1].type == MsgType.OPERATION_NOT_QUEUED.value):
            sleep(0.01)

        self.assertEqual(MsgType.NEW_SIEVE_CONFIG.value, self.client.history[1].type)
        self.assertFalse(self.client.history[0] == 1)
        self.assertFalse(self.client.history[1].generic_data[0] == 1)
        self.assertEqual(int(self.client.history[0]), self.client.history[1].generic_data[0])
        self.assertTrue(self.client.history[1].generic_data[1])

    def test_new_sieve_config_after_complain(self):
        """
        Test what happens when the leader is changed after a complaint (new sieve config).
        """
        # Set execution time simulation to over complain threshold
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (1, 1, 10)))
        self.client.broadcast(debug_message)

        # Send an invoke message
        for i in range(3):
            message = self.client.build_invoke("a", i)
            self.client.send_to_server(message, i + 2)

        self.client.history = 1, MessageComposer.compose_output(MsgType.ROLLBACK.value, 1, ("b", 2))

        while (self.client.history[1].type == MsgType.COMPLAIN.value
               or self.client.history[1].type == MsgType.ROLLBACK.value
               or self.client.history[1].type == MsgType.ABORT.value
               or self.client.history[1].type == MsgType.OPERATION_NOT_QUEUED.value):
            sleep(0.01)

        self.assertEqual(MsgType.NEW_SIEVE_CONFIG.value, self.client.history[1].type)
        self.assertFalse(self.client.history[0] == 1)
        self.assertFalse(self.client.history[1].generic_data[0] == 1)
        self.assertEqual(int(self.client.history[0]), self.client.history[1].generic_data[0])
        self.assertTrue(self.client.history[1].generic_data[1])

    def test_close(self):
        """
        Test the correct closing of the docker containers.
        """
        message = MessageComposer.compose_close()
        self.client.broadcast(message)

        sleep(3)

        self.assertFalse(check_containers("sieve-process:latest"))

    def test_multiple_commit(self):
        """
        Test the functionality of multiple commits.
        """
        # Set execution time simulation to 0 seconds
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (10, 10, 0)))
        self.client.broadcast(debug_message)

        # Send n invoke messages
        n = 5
        message = self.client.build_invoke("a", 1)
        for i in range(n):
            message.o = ("a", i)
            self.client.send_to_server(message, i + 1)
            sleep(0.1)

        for i in range(n):
            while not self.client.history:
                sleep(0.01)

            self.assertEqual(MsgType.COMMIT.value, self.client.history[1].type)
            self.client.history = None

    def test_commit_after_new_sieve_config(self):
        """
        Test the functionality of commit after a new sieve config.
        """
        # COMPLAIN - NEW SIEVE CONFIG SECTION
        # Set execution time simulation to over complain threshold
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (1, 1, 10)))
        self.client.broadcast(debug_message)

        # Send some invoke message
        for i in range(3):
            self.client.send_to_server(self.client.build_invoke("a", i), i + 4)
            sleep(0.2)

        self.client.history = 1, MessageComposer.compose_output(MsgType.ROLLBACK.value, 1, ("b", 2))

        # Set execution time simulation to 0 seconds
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (10, 10, 0)))
        self.client.broadcast(debug_message)

        while (self.client.history[1].type == MsgType.COMPLAIN.value
               or self.client.history[1].type == MsgType.ROLLBACK.value
               or self.client.history[1].type == MsgType.ABORT.value
               or self.client.history[1].type == MsgType.OPERATION_NOT_QUEUED.value):
            sleep(0.01)

        self.assertEqual(MsgType.NEW_SIEVE_CONFIG.value, self.client.history[1].type)

        # COMMIT SECTION
        # Send another invoke message
        message = self.client.build_invoke("b", 2)
        self.client.send_to_server(message, 1)

        for i in range(2):
            while self.client.history[1].type != MsgType.COMMIT.value:
                sleep(0.01)

            self.assertEqual(MsgType.COMMIT.value, self.client.history[1].type)
            self.client.history = 1, MessageComposer.compose_output(MsgType.ROLLBACK.value, 1, ("b", 2))

    def test_request_non_existing_value(self):
        """
        Test the functionality of requesting a non-existing value.
        """
        self.client.request_value("a")

        while not self.client.history:
            sleep(0.01)

        self.assertIsNone(self.client.history[1].generic_data[1])

    def test_request_existing_value(self):
        """
        Test the functionality of requesting an existing value.
        """
        # Set execution time simulation to 0 seconds
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (10, 10, 0)))
        self.client.broadcast(debug_message)

        key = "a"

        # Send an invoke message
        message = self.client.build_invoke(key, 1)
        self.client.send_to_server(message)

        while not self.client.history:
            sleep(0.01)

        self.assertEqual(MsgType.COMMIT.value, self.client.history[1].type)

        # REQUEST VALUE SECTION
        self.client.request_value(key)

        self.client.history = None

        while not self.client.history:
            sleep(0.01)

        self.assertIsNotNone(self.client.history[1].generic_data[1])

    def test_request_non_existing_value_after_abort(self):
        """
        Test the functionality of requesting a non-existing value because the operation aborted.
        """
        # Set execution time simulation to 0 seconds
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (10, 10, 0)))
        self.client.broadcast(debug_message)

        # Set faulty processes to ensure abort (f > n/3)
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_FAULTY.value, 100))
        faulty_processes = [3, 4, 5, 6, 7]
        for pid in faulty_processes:
            self.client.communication.send(debug_message, pid)

        # Send an invoke message
        key = "a"
        message = self.client.build_invoke(key, 1)
        self.client.send_to_server(message)

        self.client.history = 1, MessageComposer.compose_output(MsgType.ROLLBACK.value, 1, ("b", 2))

        while self.client.history[1].type == MsgType.ROLLBACK.value:
            sleep(0.01)

        self.assertEqual(MsgType.ABORT.value, self.client.history[1].type)

        # REQUEST VALUE SECTION
        self.client.request_value(key)

        self.client.history = None

        while not self.client.history:
            sleep(0.01)

        self.assertIsNone(self.client.history[1].generic_data[1])

    def test_request_existing_value_after_abort(self):
        """
        Test the functionality of requesting an existing value after the abort of a second operation.
        """
        # Set execution time simulation to 0 seconds
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (10, 10, 0)))
        self.client.broadcast(debug_message)

        # Send an invoke message that commits
        key_committed = "a"
        message = self.client.build_invoke(key_committed, 1)
        self.client.send_to_server(message)

        while not self.client.history:
            sleep(0.01)

        self.assertEqual(MsgType.COMMIT.value, self.client.history[1].type)

        # Set faulty processes to ensure abort (f > n/3)
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_FAULTY.value, 100))
        faulty_processes = [3, 4, 5, 6, 7]
        for pid in faulty_processes:
            self.client.communication.send(debug_message, pid)

        # Send an invoke message that aborts
        key_aborted = "b"
        message = self.client.build_invoke(key_aborted, 1)
        self.client.send_to_server(message)

        self.client.history = 1, MessageComposer.compose_output(MsgType.ROLLBACK.value, 1, ("b", 2))

        while self.client.history[1].type == MsgType.ROLLBACK.value:
            sleep(0.01)

        self.assertEqual(MsgType.ABORT.value, self.client.history[1].type)

        # REQUEST COMMITTED VALUE SECTION
        self.client.request_value(key_committed)

        self.client.history = None

        while not self.client.history:
            sleep(0.01)

        self.assertIsNotNone(self.client.history[1].generic_data[1])

    def test_request_existing_value_all(self):
        """
        Test the functionality of requesting the same existing value to all nodes (check correct consensus).
        """
        # Set execution time simulation to 0 seconds
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (10, 10, 0)))
        self.client.broadcast(debug_message)

        key = "a"
        value = 1

        # Send an invoke message
        message = self.client.build_invoke(key, value)
        self.client.send_to_server(message)

        while not self.client.history:
            sleep(0.01)

        self.assertEqual(MsgType.COMMIT.value, self.client.history[1].type)

        # REQUEST VALUE SECTION
        requested_value = None

        for i in range(1, 8):
            self.client.request_value(key)

            self.client.history = None

            while not self.client.history:
                sleep(0.01)

            if requested_value is not None:
                self.assertEqual(requested_value, self.client.history[1].generic_data[1])

            requested_value = self.client.history[1].generic_data[1]

            self.assertIsNotNone(requested_value)
            self.assertEqual(value, requested_value)

    def test_not_queued_operation(self):
        """
        Test when a node send to the leader more than one invoke. Only the first one should be queued and after a
        certain threshold the rest should be aborted.
        """
        # Set execution time simulation to over complain threshold
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (1, 1, 10)))
        self.client.broadcast(debug_message)

        # Send an invoke message
        message1 = self.client.build_invoke("a", 1)
        message2 = self.client.build_invoke("b", 2)
        self.client.send_to_server(message1, 6)
        self.client.send_to_server(message2, 6)

        while not self.client.history:
            sleep(0.01)

        while self.client.history[1].type != MsgType.OPERATION_NOT_QUEUED.value:
            sleep(0.001)

        response = self.client.history[1]

        self.assertEqual(MsgType.OPERATION_NOT_QUEUED.value, response.type)

    def test_commit_node_queued_operation(self):
        """
        Test the functionality of the commit of an operation queued in a non-leader node.
        """
        # Set execution time simulation to 0 seconds
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (10, 10, 0)))
        self.client.broadcast(debug_message)

        # Send an invoke message
        message1 = self.client.build_invoke("a", 1)
        message2 = self.client.build_invoke("b", 2)
        self.client.send_to_server(message1, 6)
        self.client.send_to_server(message2, 6)

        for i in range(2):
            self.client.history = None

            while not self.client.history:
                sleep(0.01)

            self.assertEqual(MsgType.COMMIT.value, self.client.history[1].type)

    def test_two_clients_commit(self):
        """
        Test the functionality of the commit for operations send by two different clients.
        """
        sleep(2)

        client2 = Client(1001, 9001)
        # Send the start message
        for i in range(2):
            client2.send_start()

        thread2 = Thread(target=client2.run_listener)
        thread2.start()

        # Set execution time simulation to 0 seconds
        debug_message = MessageComposer.compose_debug((MsgKey.DEBUG_EX_TIME.value, (10, 10, 0)))
        self.client.broadcast(debug_message)

        # Send an invoke message
        self.client.send_to_server(self.client.build_invoke("a", 1))
        client2.send_to_server(client2.build_invoke("b", 2))

        while not self.client.history:
            sleep(0.01)

        self.assertEqual(MsgType.COMMIT.value, self.client.history[1].type)

        while not client2.history:
            sleep(0.01)

        self.assertEqual(MsgType.COMMIT.value, self.client.history[1].type)

        client2.close()
        thread2.join()


if __name__ == "__main__":
    unittest.main()
