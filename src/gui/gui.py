#!/bin/bash

import PySimpleGUI as sg

from gui.common import run_docker_compose, stop_docker_compose

# Set the constant values
SUBMIT_KEY = "-SUBMIT-"
START_KEY = "-START-"
STOP_KEY = "-STOP-"
INPUT_KEY = "-KEY-"
INPUT_VALUE = "-VALUE-"
CLEAR_KEY = "-CLEAR-"
HISTORY_KEY = "-HISTORY-"
SIZE_INPUT_TEXT = 7

# Define the layout
LAYOUT = [
    [sg.Column([
        [sg.Text("Admin", pad=(5, (10, 50)))],
        [sg.Button("Start server", key=START_KEY)],
        [sg.Button("Stop server", key=STOP_KEY)]
    ], vertical_alignment="top", key="-COL1-", expand_x=True, expand_y=True, pad=((0, 30), 0)),
        sg.Column([
            [sg.Text("Client", pad=(5, (10, 20)))],
            [sg.Frame("Operation", [
                [sg.Text("Key:", pad=(0, (20, 0)), size=SIZE_INPUT_TEXT),
                 sg.InputText(key=INPUT_KEY, pad=(0, (20, 0))), ],
                [sg.Text("Value:", pad=(0, (10, 0)), size=SIZE_INPUT_TEXT),
                 sg.InputText(key=INPUT_VALUE, pad=(0, (10, 0)))],
                [sg.Column([
                    [sg.Button("Send", key=SUBMIT_KEY, pad=(0, (10, 0)))]
                ], expand_x=True, element_justification='right')],

            ], border_width=0)],

            [sg.Frame("", [
                [sg.Column([
                    [sg.Text("Response history", pad=(5, (10, 20))),
                     sg.Button("Clear", key=CLEAR_KEY, pad=(5, (10, 20)))]
                ], expand_x=True, element_justification='center')],

                [sg.Column([
                    [sg.Multiline(size=(50, 10), key=HISTORY_KEY, disabled=True)]
                ], expand_x=True, expand_y=True)],

            ], expand_x=True, border_width=0)],
            # [sg.Frame("Table", [
            #     [sg.Column([[sg.Table(values=[["" for _ in range(2)] for _ in range(10)], headings=["Key", "Value"],
            #                           display_row_numbers=False, auto_size_columns=False, num_rows=min(25, 10),
            #                           key=TABLE_KEY)]], expand_x=True)]
            # ])],
        ], vertical_alignment="top")]
]


class GuiGenerator:
    def __init__(self, client):
        self.layout = LAYOUT
        self.client = client
        self.window = None

    def start(self):
        # Create the window
        self.window = sg.Window("Sieve Protocol", self.layout, resizable=False, finalize=True)
        # self.window['-COL1-'].Widget.configure(borderwidth=3, relief=sg.DEFAULT_FRAME_RELIEF)

        # Event loop
        while True:
            event, values = self.window.read()
            if event == sg.WINDOW_CLOSED:
                break
            elif event == SUBMIT_KEY:
                # Update the table with the text from the input fields
                self.window[TABLE_KEY].update(values=[[values[INPUT1_KEY], values[INPUT2_KEY]]])
            elif event == START_KEY:
                run_docker_compose("docker-compose.yaml")
                # self.comm.broadcast(MessageComposer.compose_start())  # is it really necessary?
            elif event == STOP_KEY:
                stop_docker_compose()

        self.stop()

    def stop(self):
        self.window.close()
        # mself.comm.broadcast(MessageComposer.compose_close())
