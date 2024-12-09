from unittest.mock import patch

import pytest
from invariant_sdk.client import Client as InvariantClient
from invariant_sdk.types.push_traces import PushTracesRequest

from invariant.testing import Trace


@pytest.fixture(name="sample_trace")
def sample_trace_fixture() -> Trace:
    """Sample trace fixture."""
    return Trace(
        trace=[
            {"role": "user", "content": "Hello there"},
            {
                "role": "assistant",
                "content": "Hello there",
                "tool_calls": [
                    {
                        "type": "function",
                        "function": {"name": "greet", "arguments": {"name": "there"}},
                    }
                ],
            },
            {"role": "user", "content": "I need help with something."},
            {
                "role": "assistant",
                "content": "I need help with something",
                "tool_calls": [
                    {
                        "type": "function",
                        "function": {
                            "name": "help",
                            "arguments": {"thing": "something"},
                        },
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "ask",
                            "arguments": {"question": "what do you need help with?"},
                        },
                    },
                ],
            },
        ],
        metadata={"interisting": "very much"},
    )


class MockException(Exception):
    pass


def mocked_request(self, method, pathname, request_kwargs):
    """Check that the request kwargs match a PushTracesRequest.

    Raise MockException if successful. This way we prevent code executing after the request call from breaking.
    """
    PushTracesRequest(**request_kwargs["json"])
    raise MockException("This is Mocked")


def test_push_to_explorer(sample_trace: Trace):
    """Testing push to explorer method. Test only if the requests is well formed."""
    client = InvariantClient(api_key="fake_url", api_url="http://fake_key")
    with patch("invariant_sdk.client.Client.request", mocked_request):
        try:
            sample_trace.push_to_explorer(client=client)
        except MockException:
            # The mocked request returned MockException if everything went fine, else the test fails
            pass
