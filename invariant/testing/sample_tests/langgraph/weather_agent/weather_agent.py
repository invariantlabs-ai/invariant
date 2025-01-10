"""This is a simple example of a weather agent that uses a tool to get the weather."""

from typing import Literal

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode


class WeatherAgent:
    """Simple weather agent that uses a tool to get the weather."""

    def __init__(self):
        # Private initialization of tools, tool node, and model
        self._tools = [self._find_weather]
        self._tool_node = ToolNode(self._tools)
        self._model = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(self._tools)

    @tool
    @staticmethod
    def _find_weather(query: str):
        """Call to surf the web."""
        if "sf" in query.lower() or "san francisco" in query.lower():
            return "It's 60 degrees and foggy."
        return "It's 90 degrees and sunny."

    @staticmethod
    def _should_continue(state: MessagesState) -> Literal["tools", END]:
        """Determines if the agent should continue or stop."""
        messages = state["messages"]
        last_message = messages[-1]
        # If the LLM makes a tool call, then we route to the "tools" node
        if last_message.tool_calls:
            return "tools"
        # Otherwise, we stop (reply to the user)
        return END

    def _call_model(self, state: MessagesState):
        """Call the model."""
        messages = state["messages"]
        response = self._model.invoke(messages)
        return {"messages": [response]}

    def get_graph(self) -> CompiledStateGraph:
        """Create and return the weather agent."""
        workflow = StateGraph(MessagesState)

        # Define the two nodes we will cycle between
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", self._tool_node)

        # Set the entrypoint as `agent`
        workflow.add_edge(START, "agent")

        # Add a conditional edge from agent node
        workflow.add_conditional_edges("agent", self._should_continue)

        # Add a normal edge from `tools` to `agent`
        workflow.add_edge("tools", "agent")

        # Initialize memory to persist state between graph runs
        checkpointer = MemorySaver()

        return workflow.compile(checkpointer=checkpointer)
