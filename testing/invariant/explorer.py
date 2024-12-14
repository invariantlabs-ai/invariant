#!/usr/bin/env python3
"""CLI to launch the Invariant Explorer as a Docker compose application."""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path
import requests
import time

parser = argparse.ArgumentParser(
    prog="invariant explorer",
    description="Launch the Invariant Explorer as a Docker compose application.",
)
parser.add_argument(
    "--port",
    type=int,
    default=80,
    help="The port to expose the Invariant Explorer on.",
)
parser.add_argument(
    "--version",
    type=str,
    default="stable",
    help="Branch or version of the Invariant Explorer to use.",
)

args = None


def ensure_has_docker_compose():
    """Ensure that the user has Docker Compose installed."""
    try:
        p = subprocess.Popen(
            ["docker", "compose", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        p.communicate()

        if p.returncode != 0:
            raise Exception(
                "Docker Compose is not installed. Please go to https://docs.docker.com/compose/install/ to install it and then re-run this command."
            )
    except FileNotFoundError:
        raise Exception(
            "Docker Compose is not installed. Please go to https://docs.docker.com/compose/install/ to install it and then re-run this command."
        )


def ensure_has_docker_network():
    """Ensure that the user has the Docker network that the Invariant Explorer uses `invariant-explorer-web`."""
    p = subprocess.Popen(
        ["docker", "network", "ls", "--filter", "name=invariant-explorer-web"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    p.communicate()

    if p.returncode != 0:
        p = subprocess.Popen(
            ["docker", "network", "create", "invariant-explorer-web"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        p.communicate()

        if p.returncode != 0:
            raise Exception(
                "Failed to create the Docker network that the Invariant Explorer uses. Please check the logs for more information."
            )


def ensure_has_db_folder():
    """Ensure that the user has the database folder that the Invariant Explorer uses."""
    Path("./data/database").mkdir(parents=True, exist_ok=True)
    
def is_db_initialized():
    db_folders = list(Path("./data/database").iterdir())
    return len(db_folders) > 0


# list active tags of repo
def released_versions(repository):
    """List the tags of a GitHub repository."""
    try:
        url = f"https://api.github.com/repos/{repository}/tags"
        r = requests.get(url)
        r.raise_for_status()

        releases = []

        for tag in r.json():
            # if it starts with 'v'
            if tag["name"].startswith("v"):
                releases.append(tag)
        # sort by version number
        releases.sort(key=lambda x: x["name"], reverse=True)
        return releases

    # not connected to the internet
    except requests.exceptions.ConnectionError:
        print(
            "Failed to connect to the internet. Please check your connection and try again. `invariant explorer` requires an internet connection to download and update the necessary Docker images."
        )
        exit(1)


def github_file(repository, tag, path):
    """Download a file from a public GitHub repository."""
    try:
        url = (
            f"https://raw.githubusercontent.com/{repository}/refs/heads/{tag}/{path}"
            if tag == "main"
            else f"https://raw.githubusercontent.com/{repository}/refs/tags/{tag}/{path}"
        )
        print("[Updating]", url)
        r = requests.get(url)
        r.raise_for_status()
        return r.text
    # not connected to the internet
    except requests.exceptions.ConnectionError:
        print(
            "Failed to connect to the internet. Please check your connection and try again. `invariant explorer` requires an internet connection to download and update the necessary Docker images."
        )
        exit(1)


def docker_compose_setup(version):
    """Download the latest Docker Compose setup for the Invariant Explorer."""
    tf = tempfile.NamedTemporaryFile(
        delete=False, prefix="docker-compose-", suffix=".yml"
    )

    with open(tf.name, "w") as f:
        contents = github_file(
            "invariantlabs-ai/explorer-public", version, "docker-compose.stable.yml"
        )
        f.write(contents)

    return tf.name


def config_file(version):
    """Download the latest configuration file for the Invariant Explorer."""
    tf = tempfile.NamedTemporaryFile(
        delete=False, prefix="explorer.config-", suffix=".yml"
    )

    with open(tf.name, "w") as f:
        contents = github_file(
            "invariantlabs-ai/explorer-public",
            version,
            "configs/explorer.local.yml",
        )
        f.write(contents)

    return tf.name


def ensure_dot_env_exists():
    """Ensure that the user has a `.env` file for the Invariant Explorer."""
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("""POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=invariantmonitor
POSTGRES_HOST=database""")


def launch_explorer(args=None):
    """Launch the Invariant Explorer as a Docker compose application."""
    # download l

    if args is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(args)

    # gets the config and docker compose files for the specified version or branch
    version = args.version
    if version == "stable":
        versions = released_versions("invariantlabs-ai/explorer-public")
        if len(versions) == 0:
            print(
                "No published versions of Explorer found. Please specify a specific version using --version=vX.Y.Z."
            )
            exit(1)
        version = versions[0]["name"]

    # download the files for the specified version
    compose_file = docker_compose_setup(version)
    cf = config_file(version)

    # sets up environment
    ensure_has_docker_compose()
    ensure_has_docker_network()
    ensure_has_db_folder()
    ensure_dot_env_exists()
    
    first_run = not is_db_initialized()

    env = {
        **dict(os.environ),
        "APP_NAME": "explorer-local",
        "DEV_MODE": "true",
        "CONFIG_FILE_NAME": cf,
        "PREVIEW": "0",
        "PORT_HTTP": str(args.port),
        "PORT_API": "8000",
        "KEYCLOAK_CLIENT_ID_SECRET": "local-does-not-use-keycloak",
        # for 'main' we pull the latest image
        "VERSION": version if version != "main" else "latest",
    }

    print("[version]", env["VERSION"])
   
    if first_run: 
        print("First run: initializing database")
        p = subprocess.Popen(
            # make sure paths are relative to the current directory
            [
                "docker",
                "compose",
                "-f",
                compose_file,
                "--project-directory",
                ".",
                "up",
                "-d",
                "database",
                "--build",
            ],
            env=env,
        )
        p.communicate()
        if p.returncode != 0:
            raise Exception(
                "Failed to launch the Invariant Explorer. Please check the logs for more information."
            )

        # wait for the database to be ready and then close the process
        time.sleep(3)
        p = subprocess.Popen(
            # make sure paths are relative to the current directory
            [
                "docker",
                "compose",
                "-f",
                compose_file,
                "--project-directory",
                ".",
                "down",
                "database",
            ],
            env=env,
        )
        p.communicate()
        if p.returncode != 0:
            raise Exception(
                "Failed to launch the Invariant Explorer. Please check the logs for more information."
            )


    p = subprocess.Popen(
        # make sure paths are relative to the current directory
        [
            "docker",
            "compose",
            "-f",
            compose_file,
            "--project-directory",
            ".",
            "up",
            "--build",
        ],
        env=env,
    )
    p.communicate()

    if p.returncode != 0:
        raise Exception(
            "Failed to launch the Invariant Explorer. Please check the logs for more information."
        )


if __name__ == "__main__":
    launch_explorer()
