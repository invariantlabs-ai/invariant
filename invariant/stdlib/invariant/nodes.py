from pydantic.dataclasses import dataclass
from typing import Optional

@dataclass
class LLM:
    vendor: str
    model: str

@dataclass
class ToolCall:
    id: str
    type: str
    function: list

@dataclass
class Message:
    content: str
    role: str
    tool_calls: Optional[list[ToolCall]] = None

@dataclass
class Function:
    name: str
    arguments: dict

@dataclass
class ToolOutput:
    role: str
    content: str
    tool_call_id: str

TraceEvent = Message | ToolCall | ToolOutput

@dataclass
class Trace:
    elements: list[TraceEvent]