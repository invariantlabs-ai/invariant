"""Script is used to run tests using Invariant."""

import argparse
import logging
import os
import re
import subprocess
import sys

import termcolor

from invariant.analyzer.extras import Extra
from invariant.explorer.launch import launch_explorer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ANSI escape code for bold text
BOLD = "\033[1m"
END = "\033[0m"


def shortname(name):
    name = name.lower()
    # replace " " with "-" and all non-alphanumeric characters with ""
    name = re.sub(r"[^a-z0-9-]", "", name.replace(" ", "-"))
    return name


def list_extras(*args):
    print("\nThe following extra features can be enabled by installing additional dependencies:")
    extras = Extra.find_all()
    print("\r", end="")

    for extra in extras:
        print("\r" + " " * 80, end="")
        short = shortname(extra.name)
        termcolor.cprint("\n- " + extra.name + " [" + short + "]", "green")
        print("  Required Packages: ")
        for imp in extra.packages.values():
            print("   - " + imp.package_name + imp.version_constraint)
        print("\n  " + extra.description)
    print()


def prompt(question):
    response = input(question + " [y/N] ").strip()
    return response.lower() == "y" or len(response) == 0


def cmd():
    return os.path.basename(sys.argv[0])


def add_extra(*extras):
    if len(extras) == 0:
        print("USAGE:", cmd(), "add [extra1] [extra2] ... [-y] [-r]")
        print("""
[extra1] [extra2] ...: The extras to install, use 'all' to install all extras.
-y: Do not ask for confirmation.
-r: Print the list of packages to install.
              
Examples:
    <cli> add all
    <cli> add extra1 extra2
    <cli> add extra1 extra2 -y
        """)
        sys.exit(1)

    to_install = set()
    extras = set(extras)

    noask = "-y" in extras
    install_all = "all" in extras
    print_r_file = "-r" in extras
    extras = extras - {"-y", "all", "-r"}

    all_extras = Extra.find_all()
    print("\r", end="")

    for extra in all_extras:
        name = shortname(extra.name)
        if name in extras or install_all:
            for pd in extra.packages.values():
                to_install.add(pd.package_name + pd.version_constraint)
                extras = extras - {name}

    if len(extras) > 0:
        print("Unknown extras:", ", ".join(extras))
        sys.exit(1)

    if print_r_file:
        print("\n".join([pd for pd in to_install]))
        sys.exit(0)

    print("Installing the following packages:")
    print("\n".join(["- " + pd for pd in to_install]))

    if any(pd.startswith("torch") for pd in to_install):
        subprocess.call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "torch",
                "--index-url",
                "https://download.pytorch.org/whl/cpu",
            ]
        )
        pd = [pd for pd in to_install if not pd.startswith("torch")]

    if noask or prompt("Do you want to continue?"):
        # make sure 'pip' is installed
        result = subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True)
        if result.returncode != 0:
            print(
                "Error: pip is not installed. If you are not using 'pip', please be sure to install the packages listed above manually."
            )
            sys.exit(1)

        subprocess.run([sys.executable, "-m", "pip", "install"] + [pd for pd in to_install])


def parse_args(args: list[str]) -> tuple[argparse.Namespace, list[str]]:
    """Parse command-line arguments for the Invariant Runner."""
    parser = argparse.ArgumentParser(
        prog="invariant test",
        description="Runs a specified test (folder) with Invariant test (pytest compatible arguments)",
    )
    parser.add_argument(
        "--dataset_name",
        help="The name of the dataset to be used to associate the test trace data and results. This name will be used to derive a fresh dataset name on each run (e.g. myproject-1732007573)",
        default="tests",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the Invariant Explorer with the results of the test run",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="""Flag to indicate whether to push data to the invariant server. If set to true,
        {INVARIANT_AP_KEY_ENV_VAR} environment variable must be set. Visit
        {BOLD}https://explorer.invariantlabs.ai/docs/{END} to see steps to generate
        an API key.""",
    )
    parser.add_argument(
        "--agent-params",
        help="JSON containing the parameters of the agent",
        type=str,
        default=None,
    )
    return parser.parse_known_args(args)


def main():
    """Entry point for the Invariant Runner."""
    actions = {
        "explorer": "Launch the Invariant Explorer as a local Docker compose application (requires Docker)",
        "help": "Shows this help message",
        "analyzer": {
            "add": "Install extra features",
            "list-extras": "List available extra features",
        },
    }

    def help():
        print("Usage: invariant <command> [<args>]")
        print("\nSupported Commands:\n")
        for verb, description in actions.items():
            if isinstance(description, dict):
                print(f"  {verb}:")
                for sub_verb, sub_description in description.items():
                    print(f"    {sub_verb}: {sub_description}")
                continue

            print(f"  {verb}: {description}")
        print()

    if len(sys.argv) < 2:
        help()
        sys.exit(1)

    verb = sys.argv[1]
    if verb == "explorer":
        return launch_explorer(sys.argv[2:])
    elif verb == "analyzer":
        args = sys.argv[2:]
        if args[0] not in actions["analyzer"].keys():
            print("Unknown action:", verb, args[0])
            return 1
        if args[0] == "add":
            print(args)
            return add_extra(*args[1:])
        elif args[0] == "list-extras":
            return list_extras()
    elif verb == "help":
        help()
        return 0

    else:
        print(f"Unknown action: {verb}")
        return 1
