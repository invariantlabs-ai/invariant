"""Script is used to run tests using Invariant."""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import webbrowser

import pytest
import termcolor
from invariant_sdk.client import Client as InvariantClient

from invariant.analyzer.extras import Extra
from invariant.testing.config import Config
from invariant.testing.constants import (
    INVARIANT_AGENT_PARAMS_ENV_VAR,
    INVARIANT_AP_KEY_ENV_VAR,
    INVARIANT_RUNNER_TEST_RESULTS_DIR,
    INVARIANT_TEST_RUNNER_CONFIG_ENV_VAR,
    INVARIANT_TEST_RUNNER_TERMINAL_WIDTH_ENV_VAR,
)
from invariant.testing.explorer import launch_explorer
from invariant.testing.utils import utils

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


def create_config(args: argparse.Namespace) -> Config:
    """Create and return a Config instance based on parsed arguments and environment variables.

    Args:
    ----
        args (argparse.Namespace): Parsed command-line arguments.

    Returns:
    -------
        Config: Config instance with dataset name, push status, and API key.

    """
    api_key = os.getenv(INVARIANT_AP_KEY_ENV_VAR)

    try:
        agent_params = None if args.agent_params is None else json.loads(args.agent_params)
    except json.JSONDecodeError as e:
        raise ValueError("--agent-params should be a valid JSON") from e

    prefix = args.dataset_name
    dataset_name = f"{prefix}-{int(time.time())}"

    os.makedirs(INVARIANT_RUNNER_TEST_RESULTS_DIR, exist_ok=True)

    return Config(
        dataset_name=dataset_name,
        push=args.push,
        api_key=api_key,
        result_output_dir=INVARIANT_RUNNER_TEST_RESULTS_DIR,
        agent_params=agent_params,
    )


def finalize_tests_and_print_summary(conf: Config, open_browser: bool) -> None:
    """Finalize the test run.

    * pushes result metadata to the Explorer if --push
    * prints a summary of the test results.
    """
    test_results_directory = utils.get_test_results_directory_path(conf.dataset_name)

    if not os.path.exists(test_results_directory):
        print(
            "[ERROR] No test results found. Make sure your tests were executed correctly using Invariant assertions."
        )
        return

    print(f"{BOLD}Invariant Test summary{END}")
    print(f"Test result saved to: {test_results_directory}")
    print(f"{BOLD}------------{END}")

    passed_count = 0
    tests = 0
    explorer_url = ""
    for filename in os.listdir(test_results_directory):
        file_path = os.path.join(test_results_directory, filename)
        # The directory should only contain test result files - one per test.
        with open(file_path, "r", encoding="utf-8") as file:
            # Only one line in each file.
            test_result = json.loads(file.readline().strip())
            tests += 1
            if test_result.get("passed"):
                passed_count += 1
            print(
                f"{tests}. {test_result.get('name')}: {'PASSED' if test_result.get('passed') else 'FAILED'}"
            )
            explorer_url = explorer_url or test_result.get("explorer_url")
    print("\n")
    print(f"{BOLD}Total tests: {END}{tests}")
    print(f"{BOLD}Passed: {END}: {passed_count}")
    print(f"{BOLD}Failed: {END}: {tests - passed_count}")
    print(f"{BOLD}------------{END}")

    # update dataset metadata if --push
    if conf.push:
        metadata = {
            "invariant_test_results": {
                "num_tests": tests,
                "num_passed": passed_count,
            }
        }
        if conf.agent_params:
            metadata["agent_params"] = conf.agent_params

        client = InvariantClient()
        client.create_request_and_update_dataset_metadata(
            dataset_name=conf.dataset_name,
            metadata=metadata,
            request_kwargs={"verify": utils.ssl_verification_enabled()},
        )

        print(f"Results available at {explorer_url}")

        # open in browser if --open
        if open_browser:
            webbrowser.open(explorer_url)


def test(args: list[str]) -> None:
    """Run Tests."""
    try:
        # Parse command-line arguments and create configuration
        invariant_runner_args, pytest_args = parse_args(args)
        config = create_config(invariant_runner_args)
        os.environ[INVARIANT_TEST_RUNNER_CONFIG_ENV_VAR] = config.model_dump_json()
        # pass along actual terminal width to the test runner (for better formatting)
        os.environ[INVARIANT_TEST_RUNNER_TERMINAL_WIDTH_ENV_VAR] = str(utils.terminal_width())
        if invariant_runner_args.agent_params:
            os.environ[INVARIANT_AGENT_PARAMS_ENV_VAR] = invariant_runner_args.agent_params
    except ValueError as e:
        logger.error("Configuration error: %s", e)
        sys.exit(1)

    test_results_directory_path = utils.get_test_results_directory_path(config.dataset_name)
    if os.path.exists(test_results_directory_path):
        shutil.rmtree(test_results_directory_path)

    # Run pytest with remaining arguments
    exit_code = pytest.main(pytest_args)

    # print Invariant test summary
    finalize_tests_and_print_summary(config, open_browser=invariant_runner_args.open)

    return exit_code


def main():
    """Entry point for the Invariant Runner."""
    actions = {
        "test": "Runs a specified test (folder) with Invariant test (pytest compatible arguments)",
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
    if verb == "test":
        return test(sys.argv[2:])
    elif verb == "explorer":
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
