"""This script is used to run tests using Invariant."""

import argparse
import json
import logging
import os
import shutil
import sys
import time
import webbrowser

import pytest
from invariant_sdk.client import Client as InvariantClient

from invariant.config import Config
from invariant.constants import (
    INVARIANT_AGENT_PARAMS_ENV_VAR,
    INVARIANT_AP_KEY_ENV_VAR,
    INVARIANT_RUNNER_TEST_RESULTS_DIR,
    INVARIANT_TEST_RUNNER_CONFIG_ENV_VAR,
    INVARIANT_TEST_RUNNER_TERMINAL_WIDTH_ENV_VAR,
)
from invariant.utils import utils

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ANSI escape code for bold text
BOLD = "\033[1m"
END = "\033[0m"


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
        "--agent-params", help="JSON containing the parameters of the agent", type=str, default=None
    )
    return parser.parse_known_args(args)


def create_config(args: argparse.Namespace) -> Config:
    """Create and return a Config instance based on parsed arguments and environment variables.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.

    Returns:
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
    """Finalizes the test run:
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
    actions = {
        "test": "Runs a specified test (folder) with Invariant test (pytest compatible arguments)",
        "help": "Shows this help message",
    }

    if len(sys.argv) < 2 or sys.argv[1] not in actions or sys.argv[1] == "help":
        print("Usage: invariant <command> [<args>]")
        print("\nSupported Commands:\n")
        for verb, description in actions.items():
            print(f"  {verb}: {description}")
        print()
        sys.exit(1)

    verb = sys.argv[1]
    if verb == "test":
        return test(sys.argv[2:])
    else:
        print(f"Unknown action: {verb}")
        return 1
