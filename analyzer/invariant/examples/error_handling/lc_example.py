"""
Simple example of a ISA-monitored agent that uses the Langchain OpenAI agent to call a tool and monitor the output.

Showcases the, currently experimental, ability to handle policy violations using custom error handling functions that resolve the issue and continue the agent execution.
"""

import asyncio
import unittest
from dataclasses import dataclass
from langchain import hub
from langchain_core.agents import AgentAction, AgentFinish, AgentStep, AgentActionMessageLog

from invariant import Policy, Monitor
from langchain_openai import ChatOpenAI
from langchain.agents import tool, create_openai_functions_agent
from invariant.integrations.langchain_integration import MutableAgentActionTuple, MonitoringAgentExecutor
from invariant.stdlib.invariant.errors import PolicyViolation
from invariant.stdlib.invariant import ToolCall

@dataclass
class CallToMyTool(Exception):
    call: ToolCall

async def agent(*args, **kwargs):
    monitor = Monitor.from_string(
    """
    from invariant import Message, match, PolicyViolation, ToolCall, ToolOutput
    from invariant.examples.lc_example import CallToMyTool

    # find all calls to 'something' 
    raise CallToMyTool(call) if:
        (call: ToolCall)
        call.function.arguments.x > 2
        call.function.name == 'something'

    # check result after the operation
    raise PolicyViolation("result was too high", call) if:
        (call: ToolOutput)
        call.content > 1000
    """)

    @monitor.on(CallToMyTool)
    def update_inputs_to_10(error: CallToMyTool):
        import json
        call = error.call
        
        # operating on LC objects directly (AgentAction)
        action: AgentAction = call["action"]
        action.tool_input["x"] = 1000

    @monitor.on(CallToMyTool)
    async def wrap_tool(tool_input: dict, error: CallToMyTool = None, call_next: callable = None, **kwargs):
        tool_input["x"] += 1
        result = await call_next(tool_input, **kwargs)
        return result * 2

    @monitor.on(PolicyViolation)
    def handle_too_high_output(error: PolicyViolation):
        call = error.args[1]
        # operating on LC objects directly
        agent_output: MutableAgentActionTuple = call["agent_output"]
        agent_output.observation = 1

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

    # construct the tool calling agent
    agent = create_openai_functions_agent(llm, [something], prompt)
    # create an agent executor by passing in the agent and tools
    agent_executor = MonitoringAgentExecutor(agent=agent, tools=[something], verbose=True, monitor=monitor, verbose_policy=False)

    return agent_executor

# run 'agent' as a test
class TestLangchainIntegration(unittest.TestCase):
    def test_langchain_openai_agent(self):
        async def main():
            agent_executor = await agent()
            result = await agent_executor.ainvoke({
                "input": "What is something(2)? Compute it first, then compute something(something(3))). In your final response, write ## result = <result of second computation>."
            })
            assert "## result = 2" in result["output"], "Expected '## result = 2' in output, but got: " + result["output"]
        asyncio.run(main())

if __name__ == "__main__":
    unittest.main()