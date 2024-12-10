"""Define a context manager class to run tests with Invariant."""

# pylint: disable=attribute-defined-outside-init

import inspect
import json
import logging
import os
import time
import traceback as tb
from contextvars import ContextVar
from json import JSONEncoder
from typing import Literal

import pytest
from invariant_sdk.client import Client as InvariantClient
from invariant_sdk.types.push_traces import PushTracesResponse
from pydantic import ValidationError

from invariant.config import Config
from invariant.constants import INVARIANT_TEST_RUNNER_CONFIG_ENV_VAR
from invariant.custom_types.invariant_dict import InvariantDict
from invariant.custom_types.invariant_string import InvariantString
from invariant.custom_types.test_result import AssertionResult, TestResult
from invariant.formatter import format_trace
from invariant.utils import utils

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INVARIANT_CONTEXT = ContextVar("invariant_context", default=[])


class RaisingManager:
    """Similar to 'Manager' but immediately raises hard exceptions and does not track them over time.

    This manager will be used e.g. when the `trace.as_context()` context manager was not used.

    Example scenarios include users using library assertion functions like `assert_that` but outside of
    the context of a trace context manager.
    """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def add_assertion(self, assertion: AssertionResult):
        # raise hard assertions directly
        if assertion.type == "HARD" and not assertion.passed:
            column_width = utils.terminal_width()
            failure_message = "ASSERTION FAILED"
            message = assertion.message
            # locate in snippet like below
            error_message = (
                " "
                + assertion.test
                + ("_" * column_width + "\n")
                + f"\n{failure_message}: {message or ''}\n"
                + ("_" * column_width + "\n\n")
            )
            pytest.fail(error_message, pytrace=False)

        # ignore soft and passed assertions


class Manager:
    """Context manager class to run tests with Invariant."""

    def __init__(self, trace):
        self.trace = trace
        self.assertions: list[AssertionResult] = []
        self.explorer_url = ""

    @staticmethod
    def current():
        """Return the current context."""
        if len(INVARIANT_CONTEXT.get()) == 0:
            return RaisingManager()
        return INVARIANT_CONTEXT.get()[-1]

    def add_assertion(self, assertion: AssertionResult):
        """Add an assertion to the list of assertions."""
        self.assertions.append(assertion)

    def _get_test_name(self):
        """Retrieve the name of the current test function."""
        frame = inspect.currentframe().f_back.f_back
        # If the request fixture is accessible, use that to get the test name with the paramaters.
        # This gives the test name in the format: test_name[param1-param2-...] from pytest.
        request = frame.f_locals.get("request")
        if request:
            return request.node.name
        # pytest sets the test name in the environment variable.
        # when the test is running, PYTEST_CURRENT_TEST has the format:
        # sample_tests/test_agent.py::test_get_test_name_and_parameters[Bob-True] (call)
        # This too contains the parameter names with the test name.
        if "PYTEST_CURRENT_TEST" in os.environ:
            return (
                os.environ.get("PYTEST_CURRENT_TEST")
                .split("::", 1)[1]
                .rsplit("(call)", 1)[0]
                .strip()
            )
        # Fallback to just the test function name without parameters.
        return inspect.stack()[2].function

    def _load_config(self):
        """Load the configuration from the environment variable."""
        if os.getenv(INVARIANT_TEST_RUNNER_CONFIG_ENV_VAR) is not None:
            try:
                return Config.model_validate_json(
                    os.getenv(INVARIANT_TEST_RUNNER_CONFIG_ENV_VAR)
                )
            except ValidationError as e:
                raise ValueError(
                    f"""The {INVARIANT_TEST_RUNNER_CONFIG_ENV_VAR} environment variable is
                    not a valid configuration."""
                ) from e
        # If no config is provided, the tests have not been invoked with the Invariant test runner.
        return None

    def _get_test_result(self):
        """Generate the test result."""
        passed = all(
            assertion.passed if assertion.type == "HARD" else True
            for assertion in self.assertions
        )
        return TestResult(
            name=self.test_name,
            passed=passed,
            trace=self.trace,
            assertions=self.assertions,
            explorer_url=self.explorer_url,
        )

    def _get_explorer_url(self, push_traces_response: PushTracesResponse) -> str:
        """Get the Explorer URL for the test results."""
        prefix = (
            "https://localhost"
            if self.client.api_url == "http://localhost:8000"
            else self.client.api_url
        )
        return (
            f"{prefix}/u/{push_traces_response.username}/{self.config.dataset_name}/t/1"
        )

    def __enter__(self) -> "Manager":
        """Enter the context manager and setup configuration."""
        INVARIANT_CONTEXT.get().append(self)
        self.config = self._load_config()
        self.test_name = self._get_test_name()
        self.client = (
            InvariantClient() if self.config is not None and self.config.push else None
        )

        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        """Exit the context manager, handling any exceptions that occurred."""
        if exc_type is AssertionError:
            # add regular assertion failure as hard assertion result
            assertion = AssertionResult(
                test=str(tb.format_exc()),
                message=str(exc_value).encode("unicode_escape").decode()
                + " (AssertionError)",
                passed=False,
                type="HARD",
                addresses=[],
            )
            self.add_assertion(assertion)
        elif exc_type is not None:
            assertion = AssertionResult(
                test=str(tb.format_exc()),
                message="Error during test execution: " + str(exc_value),
                passed=False,
                type="HARD",
                addresses=[],
            )
            self.add_assertion(assertion)

        # print("exit manager with", exc_type, exc_value)

        # Save test result to the output directory.
        dataset_name_for_test_results = (
            self.config.dataset_name if self.config else int(time.time())
        )
        test_results_directory = utils.get_test_results_directory_path(
            dataset_name_for_test_results
        )
        test_result_file_path = f"{test_results_directory}/{self.test_name}.json"

        # if there is a config, and push is enabled, push the test results to Explorer
        if self.config is not None and self.config.push:
            push_traces_response = self.push()
            self.explorer_url = self._get_explorer_url(push_traces_response)

        # make sure path exists
        os.makedirs(os.path.dirname(test_result_file_path), exist_ok=True)

        with open(test_result_file_path, "w", encoding="utf-8") as file:
            json.dump(self._get_test_result().model_dump(), file, cls=TestResultEncoder)

        # Handle exceptions via exc_value, if needed
        # Returning False allows exceptions to propagate; returning True suppresses them
        INVARIANT_CONTEXT.get().pop()

        # unset 'manager' field of parent Trace
        if self.trace.manager is self:
            self.trace.manager = None

        # if there was only normal assertions and we already recorded it, we are n
        if exc_type is not None:
            return False

        # handle outcome (e.g. throw an exception if a hard assertion failed)
        self.handle_outcome()

        return False

    def handle_outcome(self):
        """Handle the outcome of the test (check whether we need to raise an exception)."""
        # collect set of failed hard assertions
        failed_hard_assertions = [
            a for a in self.assertions if a.type == "HARD" and not a.passed
        ]

        # raise a pytest failure if there are any failed hard assertions
        if len(failed_hard_assertions) > 0:
            # the error message is all failed hard assertions with respective
            # code and trace snippets
            error_message = (
                f"ERROR: {len(failed_hard_assertions)} hard assertions failed:\n\n"
            )

            for i, failed_assertion in enumerate(failed_hard_assertions):
                test_snippet = failed_assertion.test
                message = failed_assertion.message
                # flatten addresses
                addresses = failed_assertion.addresses
                # remove character ranges after : in addresses
                addresses = [a.split(":")[0] if ":" in a else a for a in addresses]

                column_width = utils.terminal_width()
                failure_message = (
                    "ASSERTION FAILED"
                    if failed_assertion.type == "HARD"
                    else "EXPECTATION VIOLATED"
                )

                formatted_trace = format_trace(self.trace.trace, highlights=addresses)
                if formatted_trace is not None:
                    error_message += (
                        " "
                        + test_snippet
                        + ("_" * column_width + "\n")
                        + f"\n{failure_message}: {message or ''}\n"
                        + ("_" * column_width + "\n\n")
                        + formatted_trace
                        + "\n"
                    )

                # add separator between failed assertions
                if i < len(failed_hard_assertions) - 1:
                    error_message += "_" * column_width + "\n\n"

            pytest.fail(error_message, pytrace=False)

    def _create_annotations(
        self, assertion: AssertionResult, address: str, source: str, assertion_id: int
    ) -> list[dict]:
        """Create annotations for a single assertion.

        This converts assertion to a standard which is easy to parse by the explorer.
        In particular:
        * addresses pointing at a part of a message content, are rendered by highlighting that part.
        * addresses pointing at full messages are rendered by highlighting,
          the whole message content if available, otherwise all the tool calls.
        * addresses pointing at tool calls are rendered by highlighting the tool call name.
        """
        content = assertion.message

        # if there is no message, we extract the assertion call
        if content is None:
            # take everything after the marked line (remove marker)
            remainder = assertion.test.split("\n")[assertion.test_line :]
            # truncate it smartly
            content = "\n".join(remainder)
            content = utils.ast_truncate(content.lstrip(">"))

        if address == "<root>":
            address_to_push = ["<root>"]

        elif address.isdigit():
            # Case where the address points to a message, but not a portion of the content
            msg = self.trace.trace[int(address)]
            if msg.get("content", False):
                if isinstance(msg["content"], str | InvariantString):
                    address_to_push_inner = [f".content:0-{len(msg['content'])}"]
                elif isinstance(msg["content"], dict | InvariantDict):
                    address_to_push_inner = [
                        f".content.{k}:0-{len(msg['content'][k])}"
                        for k in msg["content"]
                    ]
                else:
                    address_to_push_inner = [""]
            elif msg.get("tool_calls", False):
                address_to_push_inner = [
                    f".tool_calls.{i}.function.name:0-{len(tool_call['function']['name'])}"
                    for i, tool_call in enumerate(msg["tool_calls"])
                ]

            address_to_push = [
                "messages." + address + atpi for atpi in address_to_push_inner
            ]

        elif len(address.split(".")) > 1 and address.split(".")[1] == "tool_calls":
            msg = self.trace.trace[int(address.split(".")[0])]
            if len(address.split(".")) > 2:
                if not address.split(".")[2].isdigit():
                    raise ValueError(
                        f"Tool call index must be an integer, got {address.split('.')[2]}"
                    )
                tool_calls = [msg["tool_calls"][int(address.split(".")[2])]]
            else:
                tool_calls = msg["tool_calls"]
            address_to_push = [
                "messages."
                + address
                + f".function.name:0-{len(tool_call['function']['name'])}"
                for tool_call in tool_calls
            ]
        else:
            address_to_push = ["messages." + address]

        return [
            {
                # non-localized assertions are top-level
                "address": atp,
                # the assertion message
                "content": content,
                # metadata as expected by Explorer
                "extra_metadata": {
                    "source": source,
                    "test": assertion.test,
                    "passed": assertion.passed,
                    "line": assertion.test_line,
                    # ID of the assertion (if an assertion results in multiple annotations)
                    "assertion_id": assertion_id,
                },
            }
            for atp in address_to_push
        ]

    def push(self) -> PushTracesResponse:
        """Push the test results to Explorer."""
        assert self.config is not None, "cannot push(...) without a config"

        # annotations have the following structure:
        # {content: str, address: str, extra_metadata: {source: str, test: str, line: int}}
        annotations = []
        for assertion in self.assertions:
            assertion_id = id(assertion)
            for address in assertion.addresses:
                source = (
                    "test-assertion" if assertion.type == "HARD" else "test-expectation"
                )
                if assertion.passed:
                    source += "-passed"

                annotations += self._create_annotations(
                    assertion, address, source, assertion_id
                )

            if len(assertion.addresses) == 0:
                annotations += self._create_annotations(
                    assertion,
                    "<root>",
                    "test-assertion" + ("-passed" if assertion.passed else ""),
                    assertion_id,
                )
        test_result = self._get_test_result()
        metadata = {
            "name": test_result.name,
            "invariant.num-failures": len(
                [a for a in self.assertions if a.type == "HARD" and not a.passed]
            ),
            "invariant.num-warnings": len(
                [a for a in self.assertions if a.type == "SOFT" and not a.passed]
            ),
        }

        try:
            return self.client.create_request_and_push_trace(
                messages=[self.trace.trace],
                annotations=[annotations],
                metadata=[metadata],
                dataset=self.config.dataset_name,
                request_kwargs={"verify": utils.ssl_verification_enabled()},
            )
        except Exception:
            # fail test suite hard if this happens
            pytest.fail(
                "Failed to push test results to Explorer. Please make sure your Invariant API key and endpoint are setup correctly or run without --push.",
                pytrace=False,
            )


class TestResultEncoder(JSONEncoder):
    """Simple encoder that omits the Manager object from the JSON output."""

    def default(self, o):
        if isinstance(o, Manager):
            return None
        return JSONEncoder.default(self, o)
