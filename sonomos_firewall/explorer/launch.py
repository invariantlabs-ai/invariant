#!/usr/bin/env python3
"""CLI to launch the Invariant Explorer as a Docker compose application."""

import argparse
import io
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pexpect
import requests

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

# all other non-flag arguments
parser.add_argument("args", nargs=argparse.REMAINDER)
# all other flags
parser.add_argument("flags", nargs=argparse.REMAINDER)

args = None

# list active tags of repo
def released_versions(repository):
    """List the tags of a GitHub repository."""
    try:
        url = f"https://api.github.com/repos/{repository}/tags"
        r = requests.get(
            url,
            headers={
                # make sure to not get cached versions
                "Cache-Control": "no-cache",
            },
        )
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
    except requests.exceptions.HTTPError as e:
        # check for rate limits
        if e.response.status_code == 403:
            print("GitHub API rate limit reached, please try again later.")
            exit(1)
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
        r = requests.get(
            url,
            headers={
                # make sure to not get cached versions
                "Cache-Control": "no-cache",
            },
        )
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
            "invariantlabs-ai/explorer", version, "docker-compose.stable.yml"
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
            "invariantlabs-ai/explorer",
            version,
            "configs/explorer.local.yml",
        )
        f.write(contents)

    return tf.name


class ExplorerLauncher:
    """Class to launch the Invariant Explorer as a Docker compose application."""

    def __init__(self, args):
        self.args = args

        # gets the config and docker compose files for the specified version or branch
        version = args.version
        if version == "stable":
            versions = released_versions("invariantlabs-ai/explorer")
            if len(versions) == 0:
                print(
                    "No published versions of Explorer found. Please specify a specific version using --version=vX.Y.Z."
                )
                exit(1)
            version = versions[0]["name"]

        self.version = version

        # download the files for the specified version
        self.compose_file = docker_compose_setup(version)
        self.config = config_file(version)

    def ensure_has_docker_compose(self):
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

    def ensure_has_docker_network(self):
        """Ensure that the user has the Docker network that the Invariant Explorer uses `invariant-explorer-web`."""
        
        # check if the network exists
        p = subprocess.Popen(
            ["docker", "network", "ls", "--format", "{{.Name}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, _ = p.communicate()
        if p.returncode != 0:
            raise Exception(
                "Failed to check for Docker networks. Please make sure Docker is installed and running."
            )
        out = out.decode("utf-8")
        network_names = out.split("\n")
        if "invariant-explorer-web" not in network_names:
            print("[Creating network] invariant-explorer-web")
            # create the network
            p = subprocess.Popen(
                ["docker", "network", "create", "invariant-explorer-web"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            p.communicate()
            if p.returncode != 0:
                raise Exception(
                    "Failed to create the Docker network `invariant-explorer-web`. Please make sure Docker is installed and running."
                )
        else:
            print("[Network exists] invariant-explorer-web")

    def ensure_has_db_folder(self):
        """Ensure that the user has the database folder that the Invariant Explorer uses."""
        Path("./data/database").mkdir(parents=True, exist_ok=True)

    def ensure_dot_env_exists(self):
        """Ensure that the user has a `.env` file for the Invariant Explorer."""
        if not os.path.exists(".env"):
            with open(".env", "w") as f:
                f.write("""POSTGRES_USER=postgres
    POSTGRES_PASSWORD=postgres
    POSTGRES_DB=invariantmonitor
    POSTGRES_HOST=database""")

    def env(self):
        """Get the environment variables for the Invariant Explorer."""
        return {
            **dict(os.environ),
            "APP_NAME": "invariant-explorer",
            "DEV_MODE": "true",
            "CONFIG_FILE_NAME": self.config,
            "PREVIEW": "0",
            "PORT_HTTP": str(self.args.port),
            "PORT_API": "8000",
            "KEYCLOAK_CLIENT_ID_SECRET": "local-does-not-use-keycloak",  # for local development
            "VERSION": self.version if self.version != "main" else "latest",
        }

    def ensure_db_ready(self):
        """Launches and waits for the database to be ready. Then terminates the database container."""
        # log the output
        log = io.BytesIO()

        print("[Preparing database]")

        # use pexpect and wait for 'database system is ready to accept connections'
        p = pexpect.spawn(
            "docker compose -f "
            + self.compose_file
            # disable fancy docker output
            + " -p invariant-explorer --project-directory . --no-ansi up database",
            env={**self.env(), "DOCKER_SCAN_SUGGEST": "false"},
            logfile=log,
        )

        try:
            p.expect("database system is ready to accept connections", timeout=5)

            p.sendcontrol("c")
            p.expect(pexpect.EOF)
            assert p.exitstatus is None
            print("[Database ready]")
        except pexpect.exceptions.ExceptionPexpect:
            print("Database is not ready. Please check the logs for more information.")
            print(log.getvalue().decode("utf-8"))
            exit(1)

    def launch(self, args: list[str]):
        """Launches the Invariant Explorer."""
        cmd = [
            "docker",
            "compose",
            "-f",
            self.compose_file,
            "-p",
            "invariant-explorer",
            "--project-directory",
            ".",
            *args,
        ]
        print("[Launching]", " ".join(cmd))
        p = subprocess.Popen(
            # make sure paths are relative to the current directory
            cmd,
            env=self.env(),
        )

        p.communicate()

        if p.returncode != 0:
            raise Exception(
                "Failed to launch the Invariant Explorer. Please check the logs for more information."
            )

    def ensure_ready(self):
        self.ensure_has_docker_compose()
        self.ensure_has_docker_network()
        self.ensure_has_db_folder()
        self.ensure_dot_env_exists()


def launch_explorer(args=None):
    """Launch the Invariant Explorer as a Docker compose application."""
    if args is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(args)

    launcher = ExplorerLauncher(args)
    print("[version]", launcher.version)

    # sets up environment and checks for dependencies
    launcher.ensure_ready()
    # ensures DB is initialized
    if len(args.args) == 0:
        launcher.ensure_db_ready()
    # launches the explorer
    launcher.launch(args.args or ["up", "--build"])


if __name__ == "__main__":
    launch_explorer()
