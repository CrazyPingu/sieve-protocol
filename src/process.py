#!/bin/bash

from random import randint
from time import sleep, time
from queue import Queue

from rsm.env_config import HOST_MAP, PORT_MAP, CRYPTO_KEYS, PROCESS_ID, BUFFER_SIZE, N_FAULTY_PROCESSES, FAULTY
from utils.communication import Communication
from utils.msg import MessageComposer, Message
from utils.msg_variables import MsgType
from utils.utils import OpQueue, State, signp, check_approve, check_validation_confirm, check_validation_abort, \
    remove_unwanted_messages, dict_to_list, compute_correct_rs

COMPLAIN_THRESHOLD = 7  # threshold for the complain message
OP_MAX_AGE = 4  # max age of an operation in seconds
NEW_SIEVE_CONFIG_THRESHOLD = 3  # threshold for the new sieve config start


class Process:
    """
    Class representing a process.

    Attributes:
        communication (Communication): communication object
        I (OpQueue): queue of all operations invoked
        config (int): sieve-config number (actual turn)
        next_epoch (int): next config
        s (State): actual state
        t (State): speculative state
        B (dict): leader's buffer
        buffer_queue (list): buffer for FIFO execution of the operations in leader's buffer
        clients_ids (dict): ids of the clients that invoked operations
        leader (int): leader's process id
        next_leader (int): next leaders process id
        cur (list): current operation
        cur_pid (int): current operation process id invoker
        r (list): speculative response (in this case is equal to the operation)
        msg_buffer (dict): buffer for approve, validation and new sieve config messages received
        dictionary (dict): shared dictionary between processes
        last_order (Message): last order received
        faulty (int): indicates if the process is faulty for simulation
        ex_time (tuple): debug option for execution time simulation
        new_sieve_config_start (float): time of the start of the new sieve config
    """

    def __init__(self):
        self.communication = Communication(HOST_MAP, PORT_MAP, CRYPTO_KEYS, PROCESS_ID, BUFFER_SIZE)
        self.receive_buffer = Queue()  # buffer for the received messages to be processed
        self.I = OpQueue()  # queue of all operations invoked
        self.config = 0  # sieve-config number (actual turn)
        self.next_epoch = None  # next config
        self.s = State.S0  # actual state
        self.t = None  # speculative state
        self.B = {}  # leader's buffer
        self.buffer_queue = []  # buffer for FIFO execution of the operations in leader's buffer
        self.clients_ids = {}  # ids of the clients that invoked operations
        self.leader = 1  # leader"s process id (default 1)
        self.next_leader = None  # next leaders process id
        self.cur = None  # current operation
        self.cur_pid = None  # current operation process id invoker
        self.r = None  # speculative response (in this case is equal to the operation)
        self.msg_buffer = {}  # buffer for approve, validation and new sieve config messages received
        self.dictionary = {}  # shared dictionary
        self.last_order = None  # last order received
        self.faulty = FAULTY  # indicates if the process is faulty for simulation
        self.ex_time = (1, 100, 20)  # debug option for execution time simulation
        self.new_sieve_config_start = None  # time of the start of the new sieve config

    ##########################################
    #   Thread functions
    ##########################################

    def run(self) -> None:
        """
        Run the process.
        """
        while self.s != State.CLOSING:

            if not self.receive_buffer.empty():
                message, sender_id = self.receive_buffer.get()
                try:
                    self.__route(message, int(sender_id))
                except TypeError as e:
                    pass
                except Exception as e:
                    print(f"Error in message type: {e}")
                self.receive_buffer.task_done()

            if self.s == State.S0:
                if self.B:
                    self.__request_execution(self.buffer_queue.pop(0))

            if self.s == State.ELABORATION:
                self.t, self.r = self.__execute_operation(self.ex_time)
                if self.t is not None:
                    self.s = self.t

            if self.s == State.NEW_CONFIG:
                if self.new_sieve_config_start is not None and time() > self.new_sieve_config_start + NEW_SIEVE_CONFIG_THRESHOLD:
                    self.new_sieve_config_start = None
                    self.msg_buffer = {}
                if self.new_sieve_config_start is None:
                    self.__choose_new_leader()
                    self.new_sieve_config_start = time()
                    self.__start_new_sieve_config(self.next_epoch, self.next_leader, True)

            sleep(0.01)

        self.close()

    def run_listener(self) -> None:
        """
        Run the listener.
        """

        while self.s != State.CLOSING:
            message, sender_id = self.communication.receive()
            if message is not None:
                self.receive_buffer.put((message, sender_id))

            sleep(0.01)

    def run_check_age(self) -> None:
        """
        Check the age of the operations.
        """

        while self.s != State.CLOSING:
            if self.leader != PROCESS_ID and self.s != State.ABORT:
                self.__check_operations_age()

            sleep(0.1)

    def __route(self, message: Message, sender_id: int) -> None:
        """
        Given a message, route it to the right handler.

        Parameters:
            message: the message received
            sender_id: the id of the process that sent the message
        """

        msg_type = message.type

        match msg_type:
            case MsgType.CLIENT_INVOKE.value:
                self.__rsm_execute(message.o, sender_id)
            case MsgType.INVOKE.value:
                self.__receive_invoke(message, sender_id)
            case MsgType.EXECUTE.value:
                self.__receive_execute(message, sender_id)
            case MsgType.APPROVE.value:
                if self.s == State.WAITING_APPROVAL and self.leader == PROCESS_ID:
                    self.__receive_approve(message, sender_id)
            case MsgType.COMPLAIN.value:
                self.__receive_complain(message)
            case MsgType.NEW_SIEVE_CONFIG.value:
                self.__receive_new_sieve_config(message, sender_id)
            case MsgType.ORDER.value:
                self.__receive_order(message)
            case MsgType.VALIDATION.value:
                if self.s == State.WAITING_VALIDATION:
                    self.__receive_validation(message, sender_id)
            case MsgType.COMMIT.value:
                self.__receive_commit()
            case MsgType.ABORT.value:
                self.__receive_abort()
            case MsgType.CLOSE.value:
                self.s = State.CLOSING
            case MsgType.REQUEST_VALUE.value:
                self.__receive_request_value(message, sender_id)
            case MsgType.START.value:
                pass  # Permit saving the client udp data
            case MsgType.DEBUG.value:
                self.__receive_debug(message)
            case _:
                raise Exception("Unknown message type:", msg_type)

    def __check_operations_age(self) -> None:
        """
        Check the age of the operations and act accordingly.
        """

        for o, age in self.I.get_ages().copy().items():
            if time() > age + OP_MAX_AGE:
                if self.cur is not None:
                    self.I.remove(o)
                    if o == tuple(self.cur):
                        self.__send_complain()
                    else:
                        self.__rsm_output(MsgType.OPERATION_NOT_QUEUED.value, self.config, o, self.clients_ids[o])
                    break
            elif self.cur is None:
                client_id = self.I.get_client_id(o)
                self.communication.send(MessageComposer.compose_invoke(self.config, o, client_id), self.leader)

    ##########################################
    #   Receive functions
    ##########################################

    def __receive_debug(self, message: Message) -> None:
        """
        Logics for the DEBUG message.

        Parameters:
            message: debug message received
        """

        if message.debug_faulty:
            self.faulty = message.debug_faulty
        elif message.debug_ex_time:
            self.ex_time = message.debug_ex_time

    def __receive_complain(self, message: Message) -> None:
        """
        Logics for the COMPLAIN message (leader).

        Parameters:
            message: complain message received
        """

        if message.c == self.config and message.o == self.cur:
            # Notifies the client of the complaint
            self.__rsm_output(MsgType.COMPLAIN.value, self.config, self.cur, self.clients_ids[tuple(self.cur)])

            self.__abort(True)

    def __rsm_execute(self, o: object, sender_id: int) -> None:
        """
        Logics for the receiving of a gui operation proposal. Add the operation to the queue.

        Parameters:
            o: operation to execute
            sender_id: id of the client that sent the message
        """

        if self.leader != PROCESS_ID:
            self.I.add(o, sender_id)
            self.clients_ids[tuple(o)] = sender_id
            self.communication.send(MessageComposer.compose_invoke(self.config, o, sender_id), self.leader)
        else:
            self.__receive_invoke(MessageComposer.compose_invoke(self.config, o, sender_id),
                                  PROCESS_ID)  # Treats the client invoke as a normal invoke

    def __rsm_output(self, res: object, config: int, data: object, client_id: int = None) -> None:
        """
        Output of the operation result to the client.

        Parameters:
            res: result status of the process to output
            config: epoch number
            data: data to output
            client_id: id of the client to output the message to
        """

        if client_id is not None:
            self.communication.send(MessageComposer.compose_output(res, config, data), client_id)
        else:
            self.communication.broadcast_to_clients(MessageComposer.compose_output(res, config, data))

    def __receive_request_value(self, message: Message, client_id: int) -> None:
        """
        Logics for the receiving of the REQUEST_VALUE message.

        Parameters:
            message: request value message received
            client_id: id of the client that sent the message
        """

        if message.generic_data in self.dictionary.keys():
            data = (message.generic_data, self.dictionary[message.generic_data])
        else:
            data = (message.generic_data, None)

        self.__rsm_output(MsgType.REQUEST_VALUE.value, self.config, data, client_id)

    def __receive_invoke(self, message: Message, sender_id: int) -> None:
        """
        Logics that handle the reception of an INVOKE message in case the process that called this method is the leader.

        Parameters:
            message: message received
            sender_id: id of the process that sent the message
        """

        if self.leader == PROCESS_ID and message.c == self.config and sender_id not in self.B.keys():
            self.buffer_queue.append(sender_id)
            self.B[sender_id] = message.o
            self.clients_ids[tuple(message.o)] = message.pid

    def __receive_execute(self, message: Message, sender_id: int) -> None:
        """
        Logics for the receiving of the EXECUTE message.

        Parameters:
            message: message received
            sender_id: id of the process that sent the message
        """

        if message.c == self.config and self.t is None:
            self.cur = message.o
            self.t, self.r = self.__execute_operation(self.ex_time)
            self.s = self.t
            signature = signp(self.r)
            self.communication.send(MessageComposer.compose_approve(self.config, message.o, signature),
                                    sender_id)

    def __receive_approve(self, message: Message, sender_id: int) -> None:
        """
        Logics for the receiving of all APPROVE messages (leader).

        Parameters:
            message: message received
            sender_id: id of the process that sent the message
        """

        self.msg_buffer = remove_unwanted_messages(self.msg_buffer, MsgType.NEW_SIEVE_CONFIG.value)
        self.msg_buffer[sender_id] = message

        if len(self.msg_buffer) >= 2 * N_FAULTY_PROCESSES:
            temp_buffer = self.msg_buffer.copy()  # copy the buffer that contains also the leader's message
            temp_buffer[PROCESS_ID] = MessageComposer.compose_approve(self.config, self.cur, signp(self.r))
            correct_messages = check_approve(temp_buffer, self.config, self.cur)

            self.msg_buffer = remove_unwanted_messages(temp_buffer, MsgType.APPROVE.value)

            if len(correct_messages) > N_FAULTY_PROCESSES:
                # Propose COMMIT
                self.t = State.COMMIT
                r = self.r if PROCESS_ID in correct_messages.keys() else compute_correct_rs(self.cur)
                message_to_send = MessageComposer.compose_order(
                    MsgType.CONFIRM.value, self.config, self.cur, self.t.value, r, correct_messages)
                self.last_order = message_to_send
                self.communication.broadcast(message_to_send)
            else:
                # Propose ABORT
                self.t = State.ABORT
                self.communication.broadcast(MessageComposer.compose_order(
                    MsgType.ABORT.value, self.config, self.cur, self.t.value, self.r, temp_buffer))

            self.s = State.WAITING_VALIDATION

    def __receive_order(self, message: Message) -> None:
        """
        Logics for the receiving of the ORDER message (non-leader).

        Parameters:
            message: message received
        """

        self.last_order = message

        if message.decision == MsgType.CONFIRM.value or message.decision == MsgType.ABORT.value:
            self.communication.send(MessageComposer.compose_validation(
                MsgType.CONFIRM.value if self.__validation_predicate(message) else MsgType.ABORT.value, self.config,
                self.cur), self.leader)

    def __receive_validation(self, message: Message, sender_id: int) -> None:
        """
        Logics for the receiving of VALIDATION messages to reach consensus.

        Parameters:
            message: message received
            sender_id: id of the process that sent the message
        """

        self.msg_buffer[sender_id] = message

        if len(self.msg_buffer) > 2 * N_FAULTY_PROCESSES:
            res = None
            count_confirm = 0
            for _, msg in self.msg_buffer.items():
                if msg.decision == MsgType.CONFIRM.value and msg.c == self.config and msg.o == self.cur:
                    count_confirm += 1

            cur_op = self.cur
            faulty_leader = False

            if self.t == State.COMMIT:
                if count_confirm > N_FAULTY_PROCESSES:
                    res = MsgType.COMMIT.value
                    faulty_leader = PROCESS_ID not in self.last_order.msg_set.keys()
                    self.__commit_operation(self.last_order)
                else:
                    res = MsgType.ABORT.value
                    self.__abort(True)
            elif self.t == State.ABORT:
                res = MsgType.ABORT.value
                self.__abort(count_confirm > N_FAULTY_PROCESSES)

            self.__rsm_output(res, self.config, cur_op, self.clients_ids[tuple(cur_op)])
            self.msg_buffer = {}
            if faulty_leader:
                self.s = State.NEW_CONFIG

    def __receive_new_sieve_config(self, message: Message, sender_id: int) -> None:
        """
        Logics for the receiving of the NEW_SIEVE_CONFIG message.

        Parameters:
            message: message received
            sender_id: id of the process that sent the message
        """

        new_config, new_leader = message.c, message.pid

        if sender_id == self.leader and new_config > self.config and message.generic_data:
            if self.next_leader is not None and new_leader != self.next_leader and new_config == self.next_epoch:
                self.msg_buffer = {}
            self.next_epoch, self.next_leader = new_config, new_leader
            if PROCESS_ID == new_leader:
                self.B, self.buffer_queue, self.clients_ids = message.leader_buffer
                self.__start_new_sieve_config(new_config, PROCESS_ID)
        elif self.__validation_predicate(message):
            self.msg_buffer = remove_unwanted_messages(self.msg_buffer, MsgType.VALIDATION.value)
            self.msg_buffer[sender_id] = message
            if len(self.msg_buffer) > 2 * N_FAULTY_PROCESSES:
                self.__start_epoch()
                self.new_sieve_config_start = None
            elif sender_id == new_leader:
                self.__start_new_sieve_config(new_config, new_leader)

    def __receive_commit(self) -> None:
        """
        Logics for the receiving of the COMMIT message.
        """

        self.__commit_operation(self.last_order)
        self.msg_buffer = {}

    def __receive_abort(self) -> None:
        """
        Logics for the receiving of the ABORT message.
        """

        self.__abort()
        self.msg_buffer = {}

    ##########################################
    #   Commit operation
    ##########################################

    def __commit_operation(self, message: Message) -> None:
        """
        Logics of operation commit. It is executed when abv-deliver is received and the config in the message is equal
        to the leader's config.

        Parameters:
            message: message to deliver
        """

        if str(PROCESS_ID) in message.msg_set.keys():
            self.dictionary[self.r[0]] = self.r[1]
            self.s = self.t
        else:
            # Fix faulty operation value
            self.dictionary[message.rc[0]] = message.rc[1]
            self.s = State(message.tc)

        if self.leader == PROCESS_ID:
            self.B.pop(self.cur_pid)
            self.communication.broadcast(MessageComposer.compose_commit(self.config, self.cur))
        if self.I.check_presence(message.o):
            self.I.remove(message.o)

        self.last_order = None
        self.cur = None
        self.cur_pid = None
        self.r = None
        self.t = None
        self.s = State.S0

    ##########################################
    #   Abort - Rollback - New Sieve Config
    ##########################################

    def __abort(self, new_config: bool = False) -> None:
        """
        Logics for the ABORT status (leader).

        Parameters:
            new_config: if True, the process starts a new sieve config
        """

        self.__rollback()
        self.next_epoch, self.next_leader = None, None
        if self.leader == PROCESS_ID:
            self.B.pop(self.cur_pid)
            self.communication.broadcast(MessageComposer.compose_abort(self.config, self.cur))
            if new_config:
                self.s = State.NEW_CONFIG
            else:
                self.s = State.S0

    def __rollback(self) -> None:
        """
        Rollback to the previous state.
        """

        if self.leader == PROCESS_ID:
            self.__rsm_output(MsgType.ROLLBACK.value, self.config, self.cur, self.clients_ids[tuple(self.cur)])
        self.cur = None
        self.t = None
        self.s = State.ABORT

    def __choose_new_leader(self) -> None:
        """
        Choose the new leader and the new epoch.
        """

        self.next_leader = self.leader
        while self.next_leader == PROCESS_ID:
            self.next_leader = randint(1, len(HOST_MAP) - 1)
        self.next_epoch = self.config + 1

    def __start_new_sieve_config(self, epoch: int, next_leader: int, start: bool = False) -> None:
        """
        Start a new sieve config.

        Parameters:
            epoch: next epoch number
            next_leader: next leader process id
            start: if True, the leader process starts the new sieve config
        """

        if epoch > self.config:
            message = MessageComposer.compose_new_sieve_config(epoch, next_leader)
            if self.leader == PROCESS_ID:
                message.leader_buffer = [self.B, self.buffer_queue, dict_to_list(self.clients_ids)]
                if start:
                    message.generic_data = True
            self.communication.broadcast(message)

    def __start_epoch(self) -> None:
        """
        Start the new epoch configuring the process with the new leader and the new epoch.
        """

        self.msg_buffer = {}
        self.config, self.leader = self.next_epoch, self.next_leader
        self.t = None

        if self.leader == PROCESS_ID:
            self.__rsm_output(MsgType.NEW_SIEVE_CONFIG.value, self.config, (self.leader, self.B, self.buffer_queue))
        else:
            self.B, self.buffer_queue, self.clients_ids = {}, [], {}

        self.I.reset_operations_ages()
        self.s = State.S0

    def __send_complain(self) -> None:
        """
        Send a COMPLAIN message to the leader.
        """

        self.communication.send(MessageComposer.compose_complain(self.config, self.cur, PROCESS_ID), self.leader)

    ##########################################
    #   Other operations
    ##########################################

    def __request_execution(self, pid: int) -> None:
        """
        Request the execution of the operation (leader).

        Parameters:
            pid: process id of the process that invoked the operation
        """

        if pid in self.B.keys() and self.cur is None and self.leader == PROCESS_ID:
            self.cur = self.B[pid]
            self.cur_pid = pid

            # Broadcast EXECUTE
            self.communication.broadcast(MessageComposer.compose_execute(self.config, self.cur))
            self.s = State.ELABORATION

    def __execute_operation(self, random_param: tuple = (1, 100, 20)) -> tuple:
        """
        Execute the operation.

        Parameters:
            random_param: tuple (min, max, threshold) for the random execution time number generation

        Returns:
            tuple (t, r) where t is the speculative state and r is the speculative response
        """

        t = State.WAITING_APPROVAL if self.leader == PROCESS_ID else State.WAITING_ORDER
        r = self.cur if self.faulty == 0 else (
            self.cur[0],
            str(self.cur[1]) + str("FAULTY") + str(PROCESS_ID))  # Add artificial error if process is faulty

        # Simulate execution time
        if randint(random_param[0], random_param[1]) <= random_param[2] and self.leader == PROCESS_ID:
            for _ in range(int((COMPLAIN_THRESHOLD + 1) / 0.01)):
                if self.s == State.NEW_CONFIG:
                    return None, None
                sleep(0.01)

        return t, r

    def close(self) -> None:
        """
        Close the process and the communication.
        If the process is the leader, it broadcasts the close message.
        """

        self.communication.close()

    def __validation_predicate(self, message: Message) -> bool:
        """
        Check if the message is valid.

        Parameters:
            message: message to check

        Returns:
            True if the message is valid, False otherwise
        """

        if message.type == MsgType.ORDER.value and message.c == self.config and message.o == self.cur and check_validation_confirm(
                message.msg_set, self.r, N_FAULTY_PROCESSES):
            return True
        elif message.type == MsgType.ORDER.value and message.decision == MsgType.ABORT.value and check_validation_abort(
                message.msg_set, N_FAULTY_PROCESSES, self.config, self.cur):
            return True
        elif message.type == MsgType.NEW_SIEVE_CONFIG.value and message.c <= self.next_epoch and message.pid == self.next_leader:
            return True
        return False
