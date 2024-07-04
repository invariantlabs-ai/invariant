from pydantic.dataclasses import dataclass
from pydantic import BaseModel
from typing import Optional

@dataclass
class LLM:
    vendor: str
    model: str

class Function(BaseModel):
    name: str
    arguments: dict

class ToolCall(BaseModel):
    id: str
    type: str
    function: Function
    data: Optional[dict] = None

class Message(BaseModel):
    content: Optional[str]
    role: str
    tool_calls: Optional[list[ToolCall]] = None
    data: Optional[dict] = None

class ToolOutput(BaseModel):
    role: str
    content: str
    tool_call_id: Optional[str]
    data: Optional[dict] = None

    _tool_call: Optional[ToolCall]

Event = Message | ToolCall | ToolOutput


