#!/bin/bash

from utils.msg import MessageComposer
from utils.msg_variables import MsgKey, MsgType
from rsm.env_config import HOST_MAP, PORT_MAP, CRYPTO_KEYS, PROCESS_ID, BUFFER_SIZE, N_FAULTY_PROCESSES, FAULTY, CLIENT_PID
from utils.communication import Communication
from utils.utils import OpQueue, State, signp, check_approve, check_validation_confirm, check_validation_abort, remove_unwanted_messages, reset_op_time
from random import randint
from time import sleep, time


OP_MAX_AGE = 3  # max age of an operation in seconds
NEW_SIEVE_CONFIG_THRESHOLD = 50  # threshold for the new sieve config start


class Process:
    """
    Class representing a process.
    """

    def __init__(self):
        self.communication = Communication(HOST_MAP, PORT_MAP, CRYPTO_KEYS, PROCESS_ID, BUFFER_SIZE)
        self.I = OpQueue()  # queue of all operations invoked
        self.config = 0  # sieve-config number (actual turn)
        self.next_epoch = None  # next config
        self.s = State.S0  # actual state
        self.t = None  # speculative state
        self.B = {}  # leader's buffer
        self.buffer_queue = []  # buffer for FIFO execution of the operations in leader's buffer
        self.leader = 1  # leader"s process id (default 1)
        self.next_leader = None  # next leaders process id
        self.cur = None  # current operation
        self.cur_pid = None  # current operation process id invoker
        self.r = None  # speculative response (in this case is equal to the operation)
        self.receive_buffer = {}  # buffer for approve, validation and new sieve config messages received
        self.dictionary = {}  # shared dictionary
        self.last_order = None  # last order received
        self.faulty = FAULTY  # indicates if the process is faulty for simulation
        self.ex_time = (1, 100, 20)  # debug option for execution time simulation
        self.new_sieve_config_start = None  # time of the start of the new sieve config

    ##########################################
    #   Thread functions
    ##########################################

    def run(self):
        """
        Run the process.
        """
        self.communication.broadcast(MessageComposer.compose_start())

        while self.s != State.CLOSING:
            if self.s == State.S0:
                if self.B:
                    self.request_execution(self.buffer_queue.pop(0))

            if self.s == State.ELABORATION:
                self.t, self.r = self.execute_operation(self.ex_time)
                if self.t is not None:
                    self.s = State.WAITING_APPROVAL if self.leader == PROCESS_ID else State.WAITING_ORDER

            if self.s == State.NEW_CONFIG:
                if self.new_sieve_config_start is not None and time() > self.new_sieve_config_start + NEW_SIEVE_CONFIG_THRESHOLD:
                    self.new_sieve_config_start = None
                    self.receive_buffer = {}
                if self.new_sieve_config_start is None:
                    self.choose_new_leader()
                    self.start_new_sieve_config(self.next_epoch, self.next_leader, True)
                    self.new_sieve_config_start = time()

            sleep(0.01)

        self.close()

    def run_listener(self):
        """
        Run the listener.
        """

        while self.s != State.CLOSING:
            message, sender_id = self.communication.receive()
            # try:
            self.route(message, int(sender_id))
            # except TypeError as e:
            #     pass
            # except Exception as e:
                # print(f"Error in message type: {e}")

            sleep(0.01)

    def run_check_age(self):
        """
        Check the age of the operations.
        """

        while self.s != State.CLOSING:
            if self.leader != PROCESS_ID and self.s != State.ABORT:
                self.check_operations_age()

            sleep(0.1)

    def route(self, message, sender_id):
        """
        Redirect to executor.

        :param message: message received
        :param sender_id: id of the process that sent the message
        """

        msg_type = message[MsgKey.TYPE.value]

        if msg_type == MsgType.CLIENT_INVOKE.value:
            self.rsm_execute(message[MsgKey.OPERATION.value])
        elif msg_type == MsgType.INVOKE.value:
            self.receive_invoke(message, sender_id)
        elif msg_type == MsgType.EXECUTE.value:
            self.receive_execute(message, sender_id)
        elif msg_type == MsgType.APPROVE.value and self.leader == PROCESS_ID:
            if self.s == State.WAITING_APPROVAL:
                self.receive_approve(message, sender_id)
        elif msg_type == MsgType.COMPLAIN.value:
            self.receive_complain(message)
        elif msg_type == MsgType.NEW_SIEVE_CONFIG.value:
            self.receive_new_sieve_config(message, sender_id)
        elif msg_type == MsgType.ORDER.value:
            self.receive_order(message)
        elif msg_type == MsgType.VALIDATION.value:
            if self.s == State.WAITING_VALIDATION:
                self.receive_validation(message, sender_id)
        elif msg_type == MsgType.COMMIT.value:
            self.receive_commit()
        elif msg_type == MsgType.ABORT.value:
            self.receive_abort()
        elif msg_type == MsgType.CLOSE.value:
            self.s = State.CLOSING
        elif msg_type == MsgType.START.value:
            # Permit saving the client udp data
            pass
        elif msg_type == MsgType.DEBUG.value:
            self.receive_debug(message)
        else:
            raise Exception("Unknown message type:", msg_type)

    def check_operations_age(self):
        """
        Check the age of the operations.
        """

        for o, age in self.I.get_ages().items():
            if time() > age + OP_MAX_AGE:
                if self.cur is not None:
                    self.I.remove(o)
                    if o == tuple(self.cur):
                        self.send_complain()
                    else:
                        pass
                    break
                        # TODO manda errore di comunicazione al gui

    ##########################################
    #   Receive functions
    ##########################################

    def receive_debug(self, message):
        """
        Logics for the DEBUG message.

        :param message: message received
        """

        if message[MsgKey.DEBUG_FAULTY.value]:
            self.faulty = message[MsgKey.DEBUG_FAULTY.value]
        elif message[MsgKey.DEBUG_EX_TIME.value]:
            self.ex_time = message[MsgKey.DEBUG_EX_TIME.value]

    def receive_complain(self, message):
        """
        Logics for the COMPLAIN message (leader).

        :param message: complain message received
        """

        if message[MsgKey.CONFIG.value] == self.config and message[MsgKey.OPERATION.value] == self.cur:
            # Notifies the client of the complain
            self.rsm_output(MsgType.COMPLAIN.value, self.config, self.cur)

            self.abort(True)

    def rsm_execute(self, o):
        """
        Logics for the receiving of a gui operation proposal. Add the operation to the queue.

        :param o: operation
        """

        if self.leader != PROCESS_ID:
            self.I.add(o)
            self.communication.send(MessageComposer.compose_invoke(self.config, o), self.leader)
        else:
            self.receive_invoke(MessageComposer.compose_invoke(self.config, o), PROCESS_ID)  # Treats the client invoke as a normal invoke

    def rsm_output(self, res, config, data):
        """
        Output of the operation result to the gui.

        :param res: result status of the process to output
        :param config: epoch number
        :param data: data to output
        """

        self.communication.send(MessageComposer.compose_output(res, config, data), CLIENT_PID)

    def receive_invoke(self, message, sender_id):
        """
        Logics for the INVOKE message (leader).

        :param message: message received
        :param sender_id: id of the process that sent the message
        """

        if self.leader == PROCESS_ID and message[MsgKey.CONFIG.value] == self.config and sender_id not in self.B.keys():
            self.buffer_queue.append(sender_id)
            self.B[sender_id] = message[MsgKey.OPERATION.value]

    def receive_execute(self, message, sender_id):
        """
        Logics for the EXECUTE message.

        :param message: message received
        :param sender_id: id of the process that sent the message
        """

        if message[MsgKey.CONFIG.value] == self.config and self.t is None:
            self.cur = message[MsgKey.OPERATION.value]
            self.t, self.r = self.execute_operation(self.ex_time)
            signature = signp(self.r)
            self.communication.send(MessageComposer.compose_approve(self.config, message[MsgKey.OPERATION.value], signature),
                                    sender_id)

    def receive_approve(self, message, sender_id):
        """
        Logics for the receiving of all APPROVE messages (leader).

        :param message: message received
        :param sender_id: id of the process that sent the message
        """

        self.receive_buffer[sender_id] = message

        if len(self.receive_buffer) >= 2 * N_FAULTY_PROCESSES:
            temp_buffer = self.receive_buffer.copy()  # copy the buffer that contains also the leader's message
            temp_buffer[PROCESS_ID] = MessageComposer.compose_approve(self.config, self.cur, signp(self.r))
            correct_messages = check_approve(temp_buffer, self.config, self.cur)
            # temp_buffer.pop(PROCESS_ID)

            self.receive_buffer = remove_unwanted_messages(temp_buffer, MsgType.APPROVE.value)

            if len(correct_messages) > N_FAULTY_PROCESSES:
                # Propose COMMIT
                message_to_send = MessageComposer.compose_order(
                    MsgType.CONFIRM.value, self.config, self.cur, self.t.value, self.r, correct_messages)
                self.t = State.COMMIT
                self.last_order = message_to_send
                self.communication.broadcast(message_to_send)
            else:
                # Propose ABORT
                self.t = State.ABORT
                self.communication.broadcast(MessageComposer.compose_order(
                    MsgType.ABORT.value, self.config, self.cur, self.t.value, self.r, temp_buffer))

            self.s = State.WAITING_VALIDATION

    def receive_order(self, message):
        """
        Logics for the receiving of the ORDER message (non-leader).

        :param message: message received
        """

        self.last_order = message

        if message[MsgKey.DECISION.value] == MsgType.CONFIRM.value or message[MsgKey.DECISION.value] == MsgType.ABORT.value:
            self.communication.send(MessageComposer.compose_validation(MsgType.CONFIRM.value if self.validation_predicate(message) else MsgType.ABORT.value, self.config, self.cur), self.leader)

    def receive_validation(self, message, sender_id):
        """
        Logics for the receiving of VALIDATION messages to reach consensus.

        :param message: message received
        :param sender_id: id of the process that sent the message
        """

        self.receive_buffer[sender_id] = message

        if len(self.receive_buffer) > 2 * N_FAULTY_PROCESSES:

            res = None
            count_confirm = 0
            for _, msg in self.receive_buffer.items():
                if msg[MsgKey.DECISION.value] == MsgType.CONFIRM.value and msg[MsgKey.CONFIG.value] == self.config and msg[MsgKey.OPERATION.value] == self.cur:
                    count_confirm += 1

            cur_op = self.cur
            faulty_leader = False

            if self.t == State.COMMIT:
                if count_confirm > N_FAULTY_PROCESSES:
                    res = MsgType.COMMIT.value
                    faulty_leader = PROCESS_ID not in self.last_order[MsgKey.MSG_SET.value].keys()
                    self.commit_operation(self.last_order)
                else:
                    res = MsgType.ABORT.value
                    self.abort(True)
            elif self.t == State.ABORT:
                res = MsgType.ABORT.value
                self.abort(count_confirm > N_FAULTY_PROCESSES)

            self.rsm_output(res, self.config, cur_op)
            self.receive_buffer = {}
            if faulty_leader:
                self.s = State.NEW_CONFIG

    def receive_new_sieve_config(self, message, sender_id):
        """
        Logics for the receiving of the NEW_SIEVE_CONFIG message.

        :param message: message received
        :param sender_id: id of the process that sent the message
        """

        new_config, new_leader = message[MsgKey.CONFIG.value], message[MsgKey.PID.value]

        if sender_id == self.leader and new_config > self.config and message[MsgKey.DATA.value] is not None:
            if self.next_leader is not None and new_leader != self.next_leader and new_config == self.next_epoch:
                self.receive_buffer = {}
            self.next_epoch, self.next_leader = new_config, new_leader
            if PROCESS_ID == new_leader:
                self.B, self.buffer_queue = message[MsgKey.LEADER_BUFFER.value]
                sleep(2)
                self.start_new_sieve_config(new_config, PROCESS_ID)
        elif self.validation_predicate(message): #new_leader == self.next_leader and new_config <= self.next_epoch:
                self.receive_buffer = remove_unwanted_messages(self.receive_buffer, MsgType.VALIDATION.value)
                self.receive_buffer[sender_id] = message
                if len(self.receive_buffer) > 2 * N_FAULTY_PROCESSES:
                    self.start_epoch()
                elif sender_id == new_leader:
                    self.start_new_sieve_config(new_config, new_leader)

    def receive_commit(self):
        """
        Logics for the receiving of the COMMIT message.

        :param message: message received
        """

        self.process_commit(self.last_order)
        self.receive_buffer = {}

    def receive_abort(self):
        """
        Logics for the receiving of the ABORT message.

        :param message: message received
        """

        self.abort()
        self.receive_buffer = {}

    ##########################################
    #   Commit operation
    ##########################################

    def commit_operation(self, message):
        """
        Logics of operation commit. It is executed when abv-deliver is received and c == self.config.

        :param message: message to deliver
        """

        if self.leader == PROCESS_ID:
            self.dictionary[self.r[0]] = self.r[1]
            self.B.pop(self.cur_pid)
            self.communication.broadcast(MessageComposer.compose_commit(self.config, self.cur))
            self.cur = None
            self.last_order = None
        if self.I.check_presence(message[MsgKey.OPERATION.value]):
            self.I.remove(message[MsgKey.OPERATION.value])
        self.t = None
        self.s = State.S0

    def process_commit(self, message):
        """
        Logics of operation commit. It is executed when abv-deliver is received and c == self.config (non-leader).

        :param message: message received
        """

        if PROCESS_ID in message[MsgKey.MSG_SET.value].keys():
            self.dictionary[self.r[0]] = self.r[1]
            self.s = self.t
        else:
            # Fix faulty operation value
            self.dictionary[message[MsgKey.S_RES.value][0]] = message[MsgKey.S_RES.value][1]
            self.s = message[MsgKey.S_STATE.value]
        self.cur = None
        self.last_order = None

    ##########################################
    #   Abort - Rollback - New Sieve Config
    ##########################################

    def abort(self, new_config=False):
        """
        Logics for the ABORT status (leader).

        :param new_config: if True, the process starts a new sieve config
        """

        self.rollback()
        self.next_epoch, self.next_leader = None, None
        if self.leader == PROCESS_ID:
            self.B.pop(self.cur_pid)
            self.communication.broadcast(MessageComposer.compose_abort(self.config, self.cur))
            if new_config:
                self.s = State.NEW_CONFIG
            else:
                self.s = State.S0

    def rollback(self):
        """
        Rollback the operation.
        """

        if self.leader == PROCESS_ID:
            self.rsm_output(MsgType.ROLLBACK.value, self.config, self.cur)
        self.cur = None
        self.t = None
        self.s = State.ABORT  # if self.leader == PROCESS_ID else State.S0

    def choose_new_leader(self):
        """
        Choose a new leader.
        """

        self.next_leader = self.leader
        while self.next_leader == PROCESS_ID:
            self.next_leader = randint(1, len(HOST_MAP))
        self.next_epoch = self.config + 1

    def start_new_sieve_config(self, e, p, start=False):
        """
        Start a new sieve config.

        :param e: next epoch number
        :param p: next leader
        """

        if e > self.config:
            message = MessageComposer.compose_new_sieve_config(e, p)
            if self.leader == PROCESS_ID:
                message[MsgKey.LEADER_BUFFER.value] = (self.B, self.buffer_queue)
                if start:
                    message[MsgKey.DATA.value] = True
            self.communication.broadcast(message)

    def start_epoch(self):
        """
        Start the new epoch configuring the process with the new leader and the new epoch.
        """

        self.receive_buffer = {}
        self.config, self.leader = self.next_epoch, self.next_leader
        self.t = None

        if self.leader == PROCESS_ID:
            self.rsm_output(MsgType.NEW_SIEVE_CONFIG.value, self.config, (self.leader, self.B, self.buffer_queue))
        else:
            self.B, self.buffer_queue = {}, []

        reset_op_time(self.I)
        self.s = State.S0

    def send_complain(self):
        """
        Send a complain message to the leader.
        """

        self.communication.send(MessageComposer.compose_complain(self.config, self.cur, PROCESS_ID), self.leader)

    ##########################################
    #   Other operations
    ##########################################

    def request_execution(self, pid):
        """
        Request the execution of the operation (leader).

        :param pid: process id
        """

        if pid in self.B.keys() and self.cur is None and self.leader == PROCESS_ID:
            self.cur = self.B[pid]
            self.cur_pid = pid

            # Broadcast EXECUTE
            self.communication.broadcast(MessageComposer.compose_execute(self.config, self.cur))
            self.s = State.ELABORATION

    def execute_operation(self, random_param=(1, 100, 20)) -> tuple:
        """
        Execute the operation.

        :param random_param: tuple (min, max, threshold) for the random execution time number generation
        :return: tuple (t, r) where t is the speculative state and r is the speculative response
        """

        t = State.WAITING_APPROVAL if self.leader == PROCESS_ID else State.WAITING_ORDER
        r = self.cur if not self.faulty else (
            self.cur[0], str(self.cur[1]) + str("FAULTY") + str(PROCESS_ID))  # Add artificial error if process is faulty

        # Simulate execution time
        if randint(random_param[0], random_param[1]) <= random_param[2]:
            for _ in range(int((OP_MAX_AGE + 1) / 0.01)):
                if self.s == State.S0:
                    return None, None
                sleep(0.01)

        return t, r

    def close(self):
        """
        Close the process and the communication. If the process is the leader,
        it broadcasts the close message.
        """

        # The leader broadcast close message also to the gui
        if self.leader == PROCESS_ID:
            print("Closing the RSM")
            #self.communication.broadcast(MessageComposer.compose_close(), True)

        self.communication.close()

    def validation_predicate(self, message):
        """
        Check if the message is valid.

        :param message: message to check
        :return: True if the message is valid, False otherwise
        """

        if message[MsgKey.TYPE.value] == MsgType.ORDER.value and message[MsgKey.CONFIG.value] == self.config and message[MsgKey.OPERATION.value] == self.cur and check_validation_confirm(message[MsgKey.MSG_SET.value], self.r, N_FAULTY_PROCESSES):
            return True
        elif message[MsgKey.TYPE.value] == MsgType.ORDER.value and message[MsgKey.DECISION.value] == MsgType.ABORT.value and check_validation_abort(message[MsgKey.MSG_SET.value], N_FAULTY_PROCESSES, self.config, self.cur):
            return True
        elif message[MsgKey.TYPE.value] == MsgType.NEW_SIEVE_CONFIG.value and message[MsgKey.CONFIG.value] <= self.next_epoch and message[MsgKey.PID.value] == self.next_leader:
            return True
        return False
