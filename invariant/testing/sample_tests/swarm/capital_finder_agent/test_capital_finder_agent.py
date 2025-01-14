"""Tests for the capital_finder_agent"""

import invariant.testing.functional as F
import pytest
from invariant.testing import assert_equals, assert_false, assert_true
from invariant.testing.wrappers.swarm_wrapper import SwarmWrapper
from swarm import Swarm

from .capital_finder_agent import create_agent


@pytest.fixture(name="swarm_wrapper", scope="module")
def fixture_swarm_wrapper():
    """Create a wrapper swarm client."""
    return SwarmWrapper(Swarm())


def test_capital_finder_agent_when_capital_found(swarm_wrapper):
    """Test the capital finder agent when the capital is found."""
    agent = create_agent()
    messages = [{"role": "user", "content": "What is the capital of France?"}]
    response = swarm_wrapper.run(
        agent=agent,
        messages=messages,
    )
    trace = SwarmWrapper.to_invariant_trace(response)

    with trace.as_context():
        get_capital_tool_calls = trace.tool_calls(name="get_capital")
        assert_true(F.len(get_capital_tool_calls) == 1)
        assert_equals("France", get_capital_tool_calls[0].argument("country_name"))

        assert_true(trace.messages(-1)["content"].contains("paris"))


def test_capital_finder_agent_when_capital_not_found(swarm_wrapper):
    """Test the capital finder agent when the capital is not found."""
    agent = create_agent()
    messages = [{"role": "user", "content": "What is the capital of Spain?"}]
    response = swarm_wrapper.run(
        agent=agent,
        messages=messages,
    )
    trace = SwarmWrapper.to_invariant_trace(response)

    with trace.as_context():
        get_capital_tool_calls = trace.tool_calls(name="get_capital")
        assert_true(F.len(get_capital_tool_calls) == 1)
        assert_equals("Spain", get_capital_tool_calls[0].argument("country_name"))

        tool_outputs = trace.tool_outputs(tool_name="get_capital")
        assert_true(F.len(tool_outputs) == 1)
        assert_true(tool_outputs[0]["content"].contains("not_found"))

        assert_false(trace.messages(-1)["content"].contains("Madrid"))
