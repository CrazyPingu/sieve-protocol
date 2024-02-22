#!/bin/bash

from process import Process
from threading import Thread
from time import sleep
from utils.utils import State


def main():
    p = Process()

    threads = []

    execution_thread = Thread(target=p.run, daemon=False)
    threads.append(execution_thread)

    listening_thread = Thread(target=p.run_listener, daemon=False)
    threads.append(listening_thread)

    age_thread = Thread(target=p.run_check_age, daemon=False)
    threads.append(age_thread)

    for t in threads:
        t.start()

    for t in threads:
        t.join()



if __name__ == "__main__":
    main()
