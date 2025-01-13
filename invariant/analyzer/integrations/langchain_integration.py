"""
Langchain integration for the Invariant Agent Analyzer.
"""

import contextvars
import uuid
from typing import Any, List, Optional

import termcolor

from invariant.analyzer import Monitor
from invariant.analyzer.extras import langchain_extra
from invariant.analyzer.monitor import stack, wrappers

langchain = langchain_extra.package("langchain").import_module()

from langchain.agents import AgentExecutor
from langchain_core.agents import AgentAction, AgentActionMessageLog, AgentFinish, AgentStep
from langchain_core.tools import BaseTool


def format_invariant_chat_messages(
    run_id: str,
    agent_input,
    intermediate_steps: list[AgentAction],
    next_step: AgentAction | AgentFinish,
):
    messages = []

    for msg in agent_input.get("chat_history", []):
        messages.append(
            {
                "role": msg["role"],
                "content": str(msg["content"]),
            }
        )

    if "input" in agent_input:
        messages.append(
            {
                "role": "user",
                "content": str(agent_input["input"]),
            }
        )

    msg_id = 0

    def next_id():
        nonlocal msg_id
        msg_id += 1
        return run_id + "_" + str(msg_id)

    for step in intermediate_steps:
        msg = step
        if isinstance(step, tuple) or isinstance(step, MutableAgentActionTuple):
            action, observation = step
            if isinstance(action, AgentActionMessageLog):
                messages.append(
                    {
                        "role": "assistant",
                        "content": str(action.message_log[0].content)
                        if len(action.message_log) > 0
                        else None,
                        "tool_calls": [
                            {
                                "id": "1",
                                "type": "function",
                                "function": {
                                    "name": action.tool,
                                    "arguments": action.tool_input.copy(),
                                },
                                "action": action,
                                "key": "tool_call_" + str(next_id()),
                            }
                        ],
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "content": str(observation),
                        "tool_call_id": "1",
                        "agent_output": step,
                        "key": "observation_" + str(next_id()),
                    }
                )
            else:
                raise ValueError(f"Unknown step tuple: ({action}, {observation})")
        else:
            raise ValueError(f"Unknown message type: {msg}")

    if type(next_step) is not list:
        next_step = [next_step]

    for ns in next_step:
        if isinstance(ns, AgentAction):
            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "1",
                            "type": "function",
                            "function": {"name": ns.tool, "arguments": ns.tool_input.copy()},
                            "action": ns,
                            "key": "tool_call_" + str(next_id()),
                        }
                    ],
                }
            )
        elif isinstance(ns, AgentFinish):
            messages.append(
                {
                    "role": "assistant",
                    "content": ns.return_values.get("output", str(ns.return_values)),
                }
            )
        elif isinstance(ns, tuple) or isinstance(ns, MutableAgentActionTuple):
            tool_call, tool_output = ns
            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "1",
                            "type": "function",
                            "function": {
                                "name": tool_call.tool,
                                "arguments": tool_call.tool_input.copy(),
                            },
                            "action": tool_call,
                            "key": "tool_call_" + str(next_id()),
                        }
                    ],
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "content": str(tool_output),
                    **(
                        {"tool_call_id": tool_call.tool_call_id}
                        if hasattr(tool_call, "tool_call_id")
                        else {}
                    ),
                    "agent_output": ns,
                    "key": "observation_" + str(next_id()),
                }
            )
        elif ns is not None:
            raise ValueError(f"Unknown next step type: {type(ns)}: {ns}")

    return messages


ACTIVE_AGENT_STATE = contextvars.ContextVar("active_agent_state", default=[])


class AgentState:
    inputs: dict
    intermediate_steps: List[AgentStep] = []

    def __init__(self, inputs=None, intermediate_steps=None):
        self.inputs = inputs
        self.intermediate_steps = intermediate_steps

    def __enter__(self):
        ACTIVE_AGENT_STATE.set(ACTIVE_AGENT_STATE.get() + [self])
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        ACTIVE_AGENT_STATE.set(ACTIVE_AGENT_STATE.get()[:-1])


def get_active_agent_state():
    return ACTIVE_AGENT_STATE.get()[-1]


class MutableAgentActionTuple:
    """
    Mutable proxy for a tuple of (AgentAction, Any) that allows a
    policy to update the observation of a tool call later on.

    Handles like a tuple, but allows for updating the observation.
    """

    action: AgentAction
    observation: Any

    def __init__(self, action, observation):
        self.action = action
        self.observation = observation

    @staticmethod
    def from_result(result):
        if isinstance(result, list):
            return [MutableAgentActionTuple.from_result(r) for r in result]
        elif not isinstance(result, tuple):
            return result
        action, observation = result
        return MutableAgentActionTuple(action, observation)

    def __getitem__(self, key):
        return self.observation[key]

    def __iter__(self):
        return iter([self.action, self.observation])

    def __repr__(self):
        return f"MutableAgentActionTuple({self.action}, {self.observation})"

    def __str__(self):
        return f"MutableAgentActionTuple({self.action}, {self.observation})"


class MonitoringAgentExecutor(AgentExecutor):
    monitor: Monitor
    verbose_policy: bool = False
    raise_on_violation: bool = True
    run_id: str = None

    async def ainvoke(self, inputs: dict, **kwargs):
        # choose UUID for this run
        self.run_id = str(uuid.uuid4().hex)
        return await super().ainvoke(inputs, **kwargs)

    def invoke(self, inputs: dict, **kwargs):
        raise NotImplementedError(
            "MonitoringAgentExecutor does not support synchronous execution yet. Use 'ainvoke' instead."
        )

    async def _atake_next_step(
        self, name_to_tool_map, color_mapping, inputs, intermediate_steps, run_manager=None
    ):
        with AgentState(inputs, intermediate_steps) as state:
            # analysis current state
            analysis_result = self.monitor.analyze(
                format_invariant_chat_messages(
                    self.run_id, state.inputs, state.intermediate_steps, None
                ),
                raise_unhandled=True,
            )
            # apply the handlers (make sure side-effects apply to tool_call_msg)
            analysis_result.execute_handlers()

            if len(analysis_result.handled_errors) > 0:
                self.print_chat(
                    format_invariant_chat_messages(
                        self.run_id, state.inputs, state.intermediate_steps, None
                    ),
                    heading="== POLICY APPLIED == ",
                )

            result = await super()._atake_next_step(
                name_to_tool_map, color_mapping, inputs, intermediate_steps, run_manager
            )
            result = MutableAgentActionTuple.from_result(result)

            self.print_chat(
                format_invariant_chat_messages(
                    self.run_id, state.inputs, state.intermediate_steps, result
                )
            )

            return result

    def print_chat(self, chat, heading=None):
        if not self.verbose_policy:
            return

        if heading:
            print("\n" + heading)

        print("\nCURRENT CHAT")

        for s in chat:
            s_print = s.copy()
            if "tool_calls" in s_print:
                s_print["tool_calls"] = []
                for tc in s["tool_calls"]:
                    s_print["tool_calls"].append(
                        {
                            **tc,
                        }
                    )
                    s_print["tool_calls"][-1]["action"] = "action:" + str(id(tc["action"]))
            if "agent_output" in s_print:
                s_print["agent_output"] = "agent_output:" + str(id(s["agent_output"]))
            print("", s_print)

    async def _aperform_agent_action(
        self,
        name_to_tool_map,
        color_mapping,
        agent_action,
        run_manager,
    ):
        agent_state = get_active_agent_state()

        def update_tool_input(tool_input):
            agent_action.tool_input = tool_input
            # agent_action.message_log[0].additional_kwargs['function_call']['arguments'] = json.dumps(tool_input)

        # compute current chat state
        chat = format_invariant_chat_messages(
            self.run_id, agent_state.inputs, agent_state.intermediate_steps, agent_action
        )
        tool_call_msg = chat.pop(-1)
        self.print_chat(chat + [tool_call_msg])

        # analysis current state + this tool call
        analysis_result = self.monitor.analyze(chat + [tool_call_msg], raise_unhandled=True)

        # apply the handlers (make sure side-effects apply to tool_call_msg)
        analysis_result.execute_handlers()

        chat = format_invariant_chat_messages(
            self.run_id, agent_state.inputs, agent_state.intermediate_steps, agent_action
        )
        tool_call_msg = chat.pop(-1)

        # actual tool call is last fct in stack
        async def actual_tool(tool_input: dict, **kwargs):
            if kwargs.get("verbose", False) and str(tool_input) not in agent_action.log:
                termcolor.cprint(
                    "policy handlers: input changed to `" + str(tool_input) + "`", "yellow"
                )

            # update the tool call arguments, based on actual arguments
            tool_call_msg["tool_calls"][0]["function"]["arguments"] = tool_input
            update_tool_input(tool_input)

            if kwargs.get("verbose", False) and str(tool_input) not in agent_action.log:
                self.print_chat(chat + [tool_call_msg], heading="== POLICY APPLIED == ")

            tool = name_to_tool_map[agent_action.tool]
            return await tool.arun(tool_input, **kwargs)

        # chain the wrappers
        wrapped_fct = stack(wrappers(analysis_result) + [actual_tool])
        wrapped_tool = WrappedOneTimeTool.wrap(wrapped_fct, name_to_tool_map[agent_action.tool])

        patched_map = name_to_tool_map.copy()
        patched_map[agent_action.tool] = wrapped_tool
        agent_action.log = agent_action.log.rstrip() + "\n"

        # show another snapshot, if any error handler was called
        if len(analysis_result.handled_errors) - len(wrappers(analysis_result)) > 0:
            self.print_chat(chat + [tool_call_msg], heading="== POLICY APPLIED == ")

        return await super(MonitoringAgentExecutor, self)._aperform_agent_action(
            patched_map, color_mapping, agent_action, run_manager
        )


class WrappedOneTimeTool(BaseTool):
    """
    Checks the policy before invoking a tool.

    If verification fails, the tool call is blocked and an error message is returned instead.
    """

    tool_fct: Any
    result: Optional[Any] = None

    def _run(self, tool_args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("This method should not be called directly. Use 'arun' instead.")

    async def arun(self, tool_input: dict, **kwargs: Any) -> Any:
        return await self.tool_fct(tool_input, **kwargs)

    @classmethod
    def wrap(cls, fct, tool):
        return cls(
            tool_fct=fct, name=tool.name, description=tool.description, args_schema=tool.args_schema
        )
