"""Test the weather agent."""

import invariant.testing.functional as F
import pytest
from invariant.testing import TraceFactory, assert_true
from langchain_core.messages import HumanMessage

from .weather_agent import WeatherAgent


@pytest.fixture(name="weather_agent")
def fixture_weather_agent():
    """Create a weather agent."""
    return WeatherAgent().get_graph()


def test_weather_agent_with_only_sf(weather_agent):
    """Test the weather agent with San Francisco."""
    invocation_response = weather_agent.invoke(
        {"messages": [HumanMessage(content="what is the weather in sf")]},
        config={"configurable": {"thread_id": 42}},
    )

    trace = TraceFactory.from_langgraph(invocation_response)

    with trace.as_context():
        find_weather_tool_calls = trace.tool_calls(name="_find_weather")
        assert_true(F.len(find_weather_tool_calls) == 1)
        assert_true(
            find_weather_tool_calls[0]["function"]["arguments"].contains(
                "San francisco"
            )
        )

        find_weather_tool_outputs = trace.messages(role="tool")
        assert_true(F.len(find_weather_tool_outputs) == 1)
        assert_true(
            find_weather_tool_outputs[0]["content"].contains("60 degrees and foggy")
        )

        assert_true(trace.messages(-1)["content"].contains("60 degrees and foggy"))


def test_weather_agent_with_sf_and_nyc(weather_agent):
    """Test the weather agent with San Francisco and New York City."""
    _ = weather_agent.invoke(
        {"messages": [HumanMessage(content="what is the weather in sf")]},
        config={"configurable": {"thread_id": 41}},
    )
    invocation_response = weather_agent.invoke(
        {"messages": [HumanMessage(content="what is the weather in nyc")]},
        config={"configurable": {"thread_id": 41}},
    )

    trace = TraceFactory.from_langgraph(invocation_response)

    with trace.as_context():
        find_weather_tool_calls = trace.tool_calls(name="_find_weather")
        assert_true(len(find_weather_tool_calls) == 2)
        find_weather_tool_call_args = str(
            F.map(lambda x: x.argument(), find_weather_tool_calls)
        )
        assert_true(
            "San Francisco" in find_weather_tool_call_args
            and "New York City" in find_weather_tool_call_args
        )

        find_weather_tool_outputs = trace.messages(role="tool")
        assert_true(F.len(find_weather_tool_outputs) == 2)
        assert_true(
            find_weather_tool_outputs[0]["content"].contains("60 degrees and foggy")
        )
        assert_true(
            find_weather_tool_outputs[1]["content"].contains("90 degrees and sunny")
        )

        assistant_response_messages = F.filter(
            lambda m: m.get("tool_calls") is None, trace.messages(role="assistant")
        )
        assert_true(len(assistant_response_messages) == 2)
        assert_true(
            assistant_response_messages[0]["content"].contains(
                "weather in San Francisco is"
            )
        )
        assert_true(
            assistant_response_messages[1]["content"].contains(
                "weather in New York City is"
            )
        )
