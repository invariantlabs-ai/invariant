#!/usr/bin/env python3
"""CLI to launch the Invariant Explorer as a Docker compose application."""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser(
    prog="invariant explorer",
    description="Launch the Invariant Explorer as a Docker compose application.",
)
parser.add_argument(
    "--port", type=int, default=80, help="The port to expose the Invariant Explorer on."
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


def latest_docker_compose_setup():
    s = """
services:
  traefik:
    image: traefik:v2.0
    container_name: "${APP_NAME}-local-traefik"
    command:
      - --providers.docker=true
      # Enable the API handler in insecure mode,
      # which means that the Traefik API will be available directly
      # on the entry point named traefik.
      - --api.insecure=true
      # Define Traefik entry points to port [80] for http and port [443] for https.
      - --entrypoints.web.address=0.0.0.0:80
      - --log.level=INFO
    networks:
      - web
    ports:
      - '${PORT_HTTP}:80'
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.traefik-http.entrypoints=web"

  app-api:
    image: ghcr.io/invariantlabs-ai/explorer-oss/app-api:latest
    platform: linux/amd64
    depends_on:
      - database
    working_dir: /srv/app
    env_file:
      - .env
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MODAL_TOKEN_ID=${MODAL_TOKEN_ID}
      - MODAL_TOKEN_SECRET=${MODAL_TOKEN_SECRET}
      - PROJECTS_DIR=/srv/projects
      - KEYCLOAK_CLIENT_ID_SECRET=${KEYCLOAK_CLIENT_ID_SECRET}
      - TZ=Europe/Berlin
      - DEV_MODE=${DEV_MODE}
      - APP_NAME=${APP_NAME}
      - CONFIG_FILE=/config/explorer.config.yml
    networks:
      - web
      - internal
    volumes:
      - $CONFIG_FILE_NAME:/config/explorer.config.yml
      - ./data/images:/srv/images
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.$APP_NAME-api.rule=(Host(`localhost`) && PathPrefix(`/api/`)) || (Host(`127.0.0.1`) && PathPrefix(`/api/`))"
      - "traefik.http.routers.$APP_NAME-api.entrypoints=web"
      - "traefik.http.services.$APP_NAME-api.loadbalancer.server.port=8000"
      - "traefik.docker.network=invariant_web"

  app-ui:
    image: ghcr.io/invariantlabs-ai/explorer-oss/app-ui:latest
    platform: linux/amd64
    networks:
      - web
    volumes:
      - $CONFIG_FILE_NAME:/config/explorer.config.yml
    environment:
      - APP_NAME=${APP_NAME}
      - VITE_CONFIG_FILE=/config/explorer.config.yml
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.$APP_NAME-ui.rule=Host(`localhost`)||Host(`127.0.0.1`)"
      - "traefik.http.routers.$APP_NAME-ui.entrypoints=web"
      - "traefik.http.services.$APP_NAME-ui.loadbalancer.server.port=8000"
      - "traefik.docker.network=invariant_web"

  database:
    image: postgres:16
    env_file:
      - .env
    networks:
      - internal
    volumes:
      - type: bind
        source: ./data/database
        target: /var/lib/postgresql/data

networks:
  web:
  internal:"""

    tf = tempfile.NamedTemporaryFile(
        delete=False, prefix="docker-compose-", suffix=".yml"
    )

    with open(tf.name, "w") as f:
        f.write(s)

    return tf.name


def config_file():
    s = """# this configuration file is available both in the frontend and the backend
# WARNING: never put any sensitive information in this file, as it is exposed to the client

# limit at which the content of a message will be truncated (UI and on the API)
truncation_limit: 10000
server_truncation_limit: 100000

# the name of this deployment instance (e.g. prod, local, preview, <custom name>)
instance_name: local

## authentication setup (Keycloak)

# realm name for authentication
authentication_realm: invariant-dev
# prefix of the client ID used to identify the authentication client (e.g. invariant- will be expanded to invariant-$APP_NAME)
authentication_client_id_prefix: invariant-dev

# whether this is a private instance or not (private instances do not offer a public homepage or any form of anonymous access)
private: false

# whether telemetry is enabled for this instance
telemetry: true"""

    tf = tempfile.NamedTemporaryFile(
        delete=False, prefix="explorer.config-", suffix=".yml"
    )

    with open(tf.name, "w") as f:
        f.write(s)

    return tf.name


def ensure_dot_env_exists():
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("""POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=invariantmonitor
POSTGRES_HOST=database

PGADMIN_DEFAULT_EMAIL=admin@mail.com
PGADMIN_DEFAULT_PASSWORD=admin""")


def launch_explorer(args=None):
    """Launch the Invariant Explorer as a Docker compose application."""
    # download l

    if args is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(args)

    compose_file = latest_docker_compose_setup()
    cf = config_file()

    print(compose_file)

    ensure_has_docker_compose()
    ensure_has_docker_network()
    ensure_has_db_folder()
    ensure_dot_env_exists()

    env = {
        **dict(os.environ),
        "APP_NAME": "explorer-local",
        "DEV_MODE": "true",
        "CONFIG_FILE_NAME": cf,
        "PREVIEW": "0",
        "PORT_HTTP": str(args.port),
        "PORT_API": "8000",
        "KEYCLOAK_CLIENT_ID_SECRET": "local-does-not-use-keycloak",
    }

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
