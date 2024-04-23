# Sieve-protocol (BFT) Simulation

## Overview
This repository contains a Python program that simulates the sieve protocol in byzantine fault-tolerant context.
The sieve protocol is crucial in distributed systems where achieving consensus among nodes is essential for
system reliability and fault tolerance.

## Requirements
- [Docker](https://docs.docker.com/get-docker/)
- [Python 3.10](https://www.python.org/downloads/)

## Setup
- Clone this repository to your local machine.
- Ensure Docker is installed and running on your system.
- Install Python 3.10 if not already installed.
- Install the required Python dependencies using:
    ```
    pip install -r requirements.txt
    ```
- Build the Docker image for the Sieve nodes using:
    ```
    docker build -t sieve-process .
    ```
  or use the latest image from the Docker Hub:
    ```
    docker pull emanueleartegiani/sieve-process:latest
    ```
- Move into the ***src*** directory amd run the Python client program to start the Sieve protocol simulation:
    ```
    python src/client.py <client_id> <number_of_sieve_nodes> <buffer_size>
    ```
    where (following parameters are optional and default values are used if not provided):
- `<client_id>` is the unique identifier of the client.
- `<number_of_sieve_nodes>` is the number of sieve nodes in the system.
- `<buffer_size>` is the size of the buffer used by the Python socket.

## Documentation
The documentation is generated using [MkDocs](https://www.mkdocs.org/). To use it, execute the following commands:
- Install the dependencies using:
    ```
    pip install -r mkdocs/requirements.txt
    ```
- Run the MkDocs server using:
    ```
    mkdocs serve
    ```
- Open your browser and navigate to `http://localhost:8080` to view the documentation.

In case you want to build the documentation, execute the following command:
```
mkdocs build
```
For more information about the structure of the project, please refer to the files inside the _docs_ folder.