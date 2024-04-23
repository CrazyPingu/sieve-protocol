#!/bin/bash

import subprocess


def run_docker_compose(path_docker_compose_file: str) -> None:
    """
    Run the docker-compose file.

    Parameters:
        path_docker_compose_file: path to the docker-compose file
    """

    execute_command(["docker-compose", "-f", path_docker_compose_file, "up", "-d"])


def stop_docker_compose() -> None:
    """
    Stop the docker-compose file.
    """

    execute_command(["docker-compose", "down"])


def execute_command(command: list) -> None:
    """
    Execute the command in terminal.

    Parameters:
        command: the command to execute
    """

    try:
        # Run the command
        subprocess.run(command, check=True)
        # subprocess.Popen(command)
        print(f"Command executed successfully: {' '.join(command)}")
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")


def check_containers(image_name: str) -> bool:
    """
    Check if any containers are running with the specified image name.

    Parameters:
        image_name: name of the image to check

    Returns:
        True if a container is running with the specified image, False otherwise
    """

    # Run the Docker ps command to list all running containers
    cmd = ["docker", "ps", "--format", "{{.ID}} {{.Image}}"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    output, error = process.communicate()

    if process.returncode != 0:
        print(f"Error occurred: {error}")
        return False

    lines = output.strip().split("\n")

    for line in lines:
        if line == "":
            continue
        container_id, container_image = line.split(" ", 1)
        if container_image == image_name:
            # print(f"Container {container_id} is running with image {image_name}")
            return True

    print(f"No containers found running with image {image_name}")
    return False
