#!/bin/bash

from random import uniform
from threading import Thread
from time import sleep
from datetime import datetime

import PySimpleGUI as sg

from gui.common import run_docker_compose, stop_docker_compose, check_containers
from utils.msg import Message

# Set the number of start messages
NUM_START_MESSAGES = 2

# Set the constant values
SUBMIT_KEY = "-SUBMIT-"
START_KEY = "-START-"
STOP_KEY = "-STOP-"
INPUT_KEY = "-KEY-"
INPUT_VALUE = "-VALUE-"
CLEAR_KEY = "-CLEAR-"
HISTORY_KEY = "-HISTORY-"
REQUEST_KEY = "-REQUEST-"
LOG_KEY = "-LOG-"
CLEAR_LOG_KEY = "-CLEAR_LOG-"
SERVER_STATUS_TEXT = "-STATUS_TEXT-"
SIZE_INPUT_TEXT = 7

# Define the layout
LAYOUT = [

    # Admin column
    [sg.Column([
        [sg.Frame("Admin", [
            [sg.Frame("Server status:", [
                [sg.Text("█ Server is not running █", background_color="red", key=SERVER_STATUS_TEXT,
                         pad=((5, 5), (5, 5)))],
                [sg.Button("Start server", key=START_KEY)],
                [sg.Button("Stop server", key=STOP_KEY)]
            ], expand_x=True, pad=((5, 5), (5, 5)))],
            [sg.Frame("Log", [
                [sg.Column([
                    [sg.Column([
                        [sg.Button("Clear", key=CLEAR_LOG_KEY, pad=(0, (5, 0)))]
                    ], expand_x=True, element_justification='center')],
                    [sg.Multiline(size=(40, 10), key=LOG_KEY, disabled=True, autoscroll=True)]
                ], expand_x=True, expand_y=True)],
            ], vertical_alignment="top", pad=((5, 5), (5, 5)))]], expand_x=True)]
    ], vertical_alignment="top", expand_x=True, expand_y=True),

        # Client column
        sg.Column([
            [sg.Frame("Client", [
                [sg.Frame("Operation", [
                    [sg.Text("Key:", pad=(0, (20, 0)), size=SIZE_INPUT_TEXT),
                     sg.InputText(key=INPUT_KEY, pad=(0, (20, 0)))],
                    [sg.Text("Value:", pad=(0, (10, 0)), size=SIZE_INPUT_TEXT),
                     sg.InputText(key=INPUT_VALUE, pad=(0, (10, 0)))],
                    [sg.Column([
                        [sg.Button("Request", key=REQUEST_KEY, pad=((10, 10), (5, 5))),
                         sg.Button("Send", key=SUBMIT_KEY, pad=((10, 10), (5, 5)))]
                    ], expand_x=True, element_justification='right')],
                ], expand_x=True, pad=((5, 5), (5, 5)))],

                # Response history table
                [sg.Frame("Response history", [
                    [sg.Column([
                        [sg.Button("Clear", key=CLEAR_KEY, pad=(0, (5, 0)))]
                    ], expand_x=True, element_justification='center')],

                    [sg.Column([
                        [sg.Multiline(size=(50, 10), key=HISTORY_KEY, disabled=True, autoscroll=True)]
                    ], expand_x=True, expand_y=True)],

                ], expand_x=True, pad=((5, 5), (5, 5)))]], expand_x=True)]

        ], vertical_alignment="top", expand_x=True, expand_y=True)]
]


class Gui:
    """
    Class representing the GUI.
    """

    def __init__(self, client):
        self.layout = LAYOUT
        self.client = client
        self.window = None

        # Thread variables
        self.is_running = check_containers("sieve-process:latest")
        self.thread_busy = False
        self.previous_server_status = self.is_running

        check_server = Thread(target=self.check_server, daemon=True)
        check_server.start()

    def check_server(self):
        while True:
            self.is_running = check_containers("sieve-process:latest")
            if self.is_running != self.previous_server_status:
                self.__update_server_status(False)
                self.previous_server_status = self.is_running
            sleep(1)

    def __update_server_status(self, print_status: bool = True) -> None:
        """
        Update the server status.

        Parameters:
            print_status: whether to print the status
        """

        timestamp = datetime.now().strftime('%H:%M:%S')

        if self.is_running:
            if print_status:
                self.window[LOG_KEY].update(f"{timestamp} > SV: server started.\n", append=True)
            self.window[SERVER_STATUS_TEXT].update("█ Server is running █", background_color="green")
            sleep(uniform(1, 4))
            for i in range(3):
                self.client.send_start()
        else:
            if print_status:
                self.window[LOG_KEY].update(f"{timestamp} > SV: server stopped.\n", append=True)
            self.window[SERVER_STATUS_TEXT].update("█ Server is not running █", background_color="red")

    def start(self) -> None:
        """
        Start the GUI.
        """

        self.window = sg.Window("Sieve Protocol", self.layout, resizable=False, finalize=True)

        if self.is_running:
            self.start_container(False)

        # Event loop
        while True:
            try:
                event, values = self.window.read()

                # Close the window
                if event == sg.WINDOW_CLOSED:
                    break

                # Submit the input fields to the docker containers
                elif event == SUBMIT_KEY:
                    if self.is_running:
                        if not values[INPUT_KEY] or not values[INPUT_VALUE]:
                            sg.popup_error("Please fill in the key and value fields.")
                            continue

                        message = self.client.build_invoke(values[INPUT_KEY], values[INPUT_VALUE])
                        Thread(target=self.client.send_to_server, args=(message,)).start()
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        self.window[LOG_KEY].update(
                            f"{timestamp} > Client: submitted '{values[INPUT_KEY]}: {values[INPUT_VALUE]}'\n",
                            append=True)

                        # Clean the input fields
                        self.window[INPUT_KEY].update("")
                        self.window[INPUT_VALUE].update("")
                    else:
                        sg.popup_error("The server is not running.")

                # Start the docker containers
                elif event == START_KEY:
                    if self.thread_busy:
                        sg.popup_ok("The server is starting, please wait.")

                    elif not self.is_running:
                        self.thread_busy = True
                        Thread(target=self.start_container).start()

                        # Send the start messages
                        def startup_setup(client):
                            sleep(1)
                            for i in range(NUM_START_MESSAGES):
                                client.send_start()

                        Thread(target=startup_setup, args=(self.client,)).start()

                    else:
                        sg.popup_ok("The server is already running.")

                elif event == REQUEST_KEY:
                    if self.is_running:
                        if not values[INPUT_KEY]:
                            sg.popup_error("Please fill in the key field.")
                            continue
                        Thread(target=self.client.request_value, args=(values[INPUT_KEY],)).start()
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        self.window[LOG_KEY].update(f"{timestamp} > Client: requested '{values[INPUT_KEY]}'\n",
                                                    append=True)

                        # Clean the input fields
                        self.window[INPUT_KEY].update("")
                        self.window[INPUT_VALUE].update("")
                    else:
                        sg.popup_error("The server is not running.")

                # Stop the docker containers
                elif event == STOP_KEY:
                    if self.thread_busy:
                        sg.popup_ok("The server is stopping, please wait.")

                    elif self.is_running:
                        self.thread_busy = True
                        Thread(target=self.stop_container).start()

                    else:
                        sg.popup_ok("The server is not running.")

                # Clear the history
                elif event == CLEAR_KEY:
                    self.window[HISTORY_KEY].update("")

                elif event == CLEAR_LOG_KEY:
                    self.window[LOG_KEY].update("")

            except Exception as e:
                sg.popup_error(f"An error occurred: {e}", title=e.__class__.__name__)

        self.stop()

    def stop(self) -> None:
        """
        Stop the window and exit the program.
        """

        self.window.close()
        self.client.close()

    # Check if thread for starting the container is done
    def start_container(self, run_compose: bool = True) -> None:
        """
        Start the docker containers.

        Parameters:
            run_compose: whether to run the docker-compose file
        """

        try:
            if run_compose:
                run_docker_compose("../docker-compose.yaml")
                self.is_running = True
                self.previous_server_status = self.is_running
            self.__update_server_status()
            self.thread_busy = False
        except Exception as e:
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.window[LOG_KEY].update(f"{timestamp} > SV: error occurred: {e}\n", append=True)

    # Check if thread for stopping the container is done
    def stop_container(self) -> None:
        """
        Stop the docker containers.
        """

        try:
            stop_docker_compose()
            self.is_running = False
            self.__update_server_status()
            self.thread_busy = False
        except Exception as e:
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.window[LOG_KEY].update(f"{timestamp} > SV: error occurred: {e}\n", append=True)

    def update_table(self, message: Message) -> None:
        """
        Show the message in the history table.
        Parameters:
            message: the message to show
        """

        if self.window is not None:
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.window[HISTORY_KEY].update(f"{timestamp} >>> {message}\n", append=True)

    def show_commit(self) -> None:
        """
        Show the commit message in the log.
        """

        if self.window is not None:
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.window[LOG_KEY].update(f"{timestamp} > SV: commit done.\n", append=True)

    def show_abort(self) -> None:
        """
        Show the abort message in the log.
        """

        if self.window is not None:
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.window[LOG_KEY].update(f"{timestamp} > SV: abort done.\n", append=True)

    def show_complain(self) -> None:
        """
        Show the complain message in the log.
        """

        if self.window is not None:
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.window[LOG_KEY].update(f"{timestamp} > SV: complain called, expecting abort.\n", append=True)

    def show_rollback(self) -> None:
        """
        Show the rollback message in the log.
        """

        if self.window is not None:
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.window[LOG_KEY].update(f"{timestamp} > SV: rollback done.\n", append=True)

    def show_new_sieve_config(self) -> None:
        """
        Show the new sieve config message in the log.
        """

        if self.window is not None:
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.window[LOG_KEY].update(f"{timestamp} > SV: new sieve config received.\n", append=True)

    def show_close(self) -> None:
        """
        Show the close message in the log.
        """

        if self.window is not None:
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.window[LOG_KEY].update(f"{timestamp} > SV: close received.\n", append=True)

    def show_operation_not_queued(self) -> None:
        """
        Show the operation not queued message in the log.
        """

        if self.window is not None:
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.window[LOG_KEY].update(f"{timestamp} > SV: operation not queued.\n", append=True)
