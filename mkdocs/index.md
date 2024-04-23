Welcome to the documentation for the Sieve Protocol simulation project. This project implements a Byzantine Fault Tolerant (BFT) 
consensus algorithm using the Sieve Protocol. The simulation is orchestrated through Docker containers, and a graphical user interface (GUI) 
is provided to simulate the behavior of the Sieve Protocol in a controlled environment.

## Table of Contents

- [Introduction](#introduction)
- [Pre-requisites](#pre-requisites)
- [Deployment](#deployment)

## Introduction

The Sieve Protocol is a Byzantine Fault Tolerant consensus algorithm that ensures the integrity and consistency of distributed systems, even in the presence of malicious nodes. This simulation project allows you to explore and understand the Sieve Protocol in a controlled environment.

## Pre-requisites

- **Python 3:** Install Python 3 on the system. You can download the latest version from the [official Python website](https://www.python.org/downloads/).

- **pip:** Ensure that the Python package installer, pip, is available. It is typically installed automatically with Python. If not, install it using the appropriate package manager for your system.

- **Docker:** Install Docker to enable containerization. Follow the instructions for your operating system on the [official Docker website](https://docs.docker.com/get-docker/).


## Deployment

- Clone the Sieve Protocol simulation repository to your local machine.
- Move to the root directory of the cloned repository.
- Install the required Python dependencies listed in the `requirements.txt` file:

```
pip install -r requirements.txt
```

- Run the following command to build the Docker image for the Sieve Protocol simulation process:

```
docker build -t sieve-process .
```

- Once the Docker image is built, you can start the simulation by running the `client.py` file.




