"""
Simple example of detecting illegal tool call sequences during execution of a
Langchain-based agent.
"""

import asyncio
import unittest
from dataclasses import dataclass

from langchain import hub
from langchain.agents import create_openai_functions_agent, tool
from langchain_openai import ChatOpenAI

from invariant.analyzer import Monitor, UnhandledError
from invariant.analyzer.integrations.langchain_integration import MonitoringAgentExecutor
from invariant.analyzer.stdlib.invariant import ToolCall


@dataclass
class InvalidFlow(Exception):
    a: ToolCall
    b: ToolCall


async def agent(*args, **kwargs):
    """An agent that cannot call 'something_else' after 'something' with x > 2."""

    monitor = Monitor.from_string(
        """
    from invariant import Message, match, PolicyViolation, ToolCall, ToolOutput
    from invariant.analyzer.examples.lc_flow_example import InvalidFlow
        

    # check result after the operation
    raise InvalidFlow(a=call1, b=call2) if:
        (call1: ToolCall) -> (call2: ToolCall)
        call1 is tool:something
        call1.function.arguments["x"] > 2
        call2 is tool:something_else
    """
    )

    # instantiate the LLM
    llm = ChatOpenAI(model="gpt-4o")

    # simple system prompt based on hwchase17/openai-functions-agent
    prompt = hub.pull("hwchase17/openai-functions-agent")

    # define the tools
    @tool
    def something(x: int) -> int:
        """
        Computes something() of the input x.

        :param x: The input value (int)
        """
        return x + 1

    # define the tools
    @tool
    def something_else(x: int) -> int:
        """
        Computes something_else() of the input x.

        :param x: The input value (int)
        """
        return x * 2

    # construct the tool calling agent
    agent = create_openai_functions_agent(llm, [something, something_else], prompt)
    # create an agent executor by passing in the agent and tools
    agent_executor = MonitoringAgentExecutor(
        agent=agent,
        tools=[something, something_else],
        verbose=True,
        monitor=monitor,
        verbose_policy=False,
    )

    return agent_executor


# run 'agent' as a test
class TestLangchainIntegration(unittest.TestCase):
    def test_langchain_openai_agent(self):
        async def main():
            agent_executor = await agent()
            try:
                result = await agent_executor.ainvoke(
                    {
                        "input": "What is something_else(something(4))? In your final response, write ## result = <result of second computation>."
                    }
                )
                assert False, "expected agent to be aborted due to InvalidFlow, but got: " + str(
                    result
                )
            except UnhandledError as e:
                assert len(e.errors) == 1, "expected exactly one error, but got: " + str(e.errors)
                assert "InvalidFlow" in str([e.errors[0]]), (
                    "expected InvalidFlow error, but got: " + str([e.errors[0]])
                )

        asyncio.run(main())


if __name__ == "__main__":
    unittest.main()
