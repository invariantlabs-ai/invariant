from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, RootModel
from pydantic.dataclasses import dataclass

from invariant.analyzer.runtime.runtime_errors import InvariantAttributeError


@dataclass
class LLM:
    vendor: str
    model: str


class Event(BaseModel):
    metadata: Optional[dict] = Field(
        default_factory=dict, description="Metadata associated with the event"
    )


class Function(BaseModel):
    name: str
    arguments: dict

    def __hash__(self):
        return hash((self.name, tuple(self.arguments.items())))

    def __str__(self):
        return (
            f"<Function {self.name}({', '.join([f'{k}={v}' for k, v in self.arguments.items()])})>"
        )

    def __repr__(self):
        return str(self)

    def __invariant_attribute__(self, name: str):
        if name in ["name", "arguments"]:
            return getattr(self, name)
        raise InvariantAttributeError(
            f"Attribute {name} not found in Function. Available attributes are: name, arguments"
        )


class ToolCall(Event):
    id: Optional[str] = Field(
        default=None,
        description="Unique identifier for the tool call",
    )
    type: str
    function: Function

    def __hash__(self):
        return hash((self.id, self.type, self.function.name))

    def __str__(self):
        return f"<ToolCall {super().__str__()}>"

    def __repr__(self):
        return str(self)

    def __invariant_attribute__(self, name: str):
        if name in ["function", "type", "id", "metadata"]:
            return getattr(self, name)
        raise InvariantAttributeError(
            f"Attribute {name} not found in ToolCall. Available attributes are: function, type"
        )


class TextChunk(Event):
    """
    A simple text chunk piece of content.
    """

    type: str
    text: str

    def __invariant_attribute__(self, name: str):
        if name in ["type", "text"]:
            return getattr(self, name)
        raise InvariantAttributeError(
            f"Attribute {name} not found in TextChunk. Available attributes are: type, text"
        )

    def __str__(self) -> str:
        return f"TextChunk(type={self.type}, text={self.text})>"

    def __repr__(self) -> str:
        return str(self)


class Image(Event):
    """
    A chunk of content that is an image.
    """

    type: str
    image_url: Dict[str, str]

    def __invariant_attribute__(self, name: str):
        if name in ["type", "image_url"]:
            return getattr(self, name)
        raise InvariantAttributeError(
            f"Attribute {name} not found in ImageChunk. Available attributes are: type, image_url"
        )

    def __str__(self):
        return f"Image(type={self.type}, image_url={self.image_url})>"

    def __repr__(self):
        return str(self)


Chunk = Union[TextChunk, Image]


class Contents(RootModel[list[Chunk]]):
    """
    Represents a list of different content chunks.

    Example:

    ```
    {
        "content": [
            {"type": "text", "text": "Hello"},
            {"type": "text", "text": "World"}
        ]
    }
    ```
    """

    root: list[Chunk]

    # override contains
    def __contains__(self, item: object) -> bool:
        for chunk in self.root:
            if isinstance(chunk, TextChunk):
                if item in chunk.text:
                    return True
            elif isinstance(chunk, Image):
                if item in chunk.image_url["url"]:
                    return True
        return False

    def __invariant_attribute__(self, name: str):
        # root is explicitly inaccessible
        if name in ["text", "image"]:
            return getattr(self, name)
        raise InvariantAttributeError(
            f"Attribute {name} not found in Contents list. Use .text() to iterate over all contained text chunks."
        )

    def text(self) -> list[str]:
        """Returns the text representation of the contents."""
        return [chunk.text for chunk in self.root if isinstance(chunk, TextChunk)]

    def image(self) -> list[str]:
        """Returns the image URL of the contents."""
        return [chunk.image_url["url"] for chunk in self.root if isinstance(chunk, Image)]

    def __iter__(self):
        for chunk in self.root:
            yield chunk

    def __getitem__(self, index: int) -> Chunk:
        return self.root[index]

    def __len__(self):
        return len(self.root)

    def __str__(self) -> str:
        return f"<Contents({', '.join([str(chunk) for chunk in self.root])})>"

    def __repr__(self) -> str:
        return str(self)


class Message(Event):
    role: str = Field(description="The role of the message sender (e.g., 'user', 'assistant')")
    content: Optional[str] | Contents = Field(
        default=None, description="The content of the message"
    )

    tool_calls: Optional[list[ToolCall]] = Field(
        default_factory=list,
        description="List of tool calls associated with the message",
    )

    def __rich_repr__(self):
        # Print on separate line
        yield "role", self.role
        yield "content", self.content
        yield "tool_calls", self.tool_calls

    def __hash__(self):
        return hash((self.role, self.content))

    def __str__(self):
        return f"<Message {super().__str__()}>"

    def __repr__(self):
        return str(self)

    def __invariant_attribute__(self, name: str):
        if name in ["role", "content", "tool_calls", "metadata"]:
            return getattr(self, name)
        raise InvariantAttributeError(
            f"Attribute {name} not found in Message. Available attributes are: role, content, tool_calls"
        )


class ToolOutput(Event):
    role: str
    content: Optional[str] | Contents | dict = Field(
        default=None, description="The content of the tool output"
    )
    tool_call_id: Optional[str]

    _tool_call: Optional[ToolCall]

    def __hash__(self):
        return hash((self.role, self.content, self.tool_call_id))

    def __str__(self):
        return f"<ToolOutput {super().__str__()}>"

    def __repr__(self):
        return str(self)

    def __invariant_attribute__(self, name: str):
        if name in ["role", "content", "tool_call_id", "metadata"]:
            return getattr(self, name)
        raise InvariantAttributeError(
            f"Attribute {name} not found in ToolOutput. Available attributes are: role, content, tool_call_id"
        )


def text(*args):
    """
    Returns all text-typed string chunks in a given list of content.

    Supports [Contents(...), "abc"] and ["abc", "def"] and raw strings like "abc".

    Also supports nested lists of that structure.
    """
    from invariant.analyzer.stdlib.invariant.nodes import Contents, Message

    result = []
    for arg in args:
        # for None, there are no text chunks
        if arg is None:
            continue
        # for .content lists, we extra all text chunks via Contents.text()
        elif isinstance(arg, Contents):
            result.extend(arg.text())
        # for Message, we extract the content
        elif isinstance(arg, Message):
            result.extend(text(arg.content))
        elif isinstance(arg, ToolOutput):
            result.extend(text(arg.content))
        # for lists, we recurse
        elif isinstance(arg, list):
            result.extend(text(*arg))
        # for strings, we add them to the result
        elif isinstance(arg, str):
            result.append(arg)
    return result


def image(*args) -> list[str]:
    """
    Returns all image URL chunks in a given list of content.

    Args:
        *args: A list of content chunks.

    Returns:
        A list of base64 encoded image strings.
    """
    from invariant.analyzer.stdlib.invariant.nodes import Contents, Message

    result = []
    for arg in args:
        # for None, there are no image chunks
        if arg is None:
            continue
        # for Contents, we extract the image URLs
        elif isinstance(arg, Contents):
            result.extend(arg.image())
        # for Message, we extract the content
        elif isinstance(arg, Message):
            result.extend(image(arg.content))
        # for ToolOutput, we extract the content
        elif isinstance(arg, ToolOutput):
            result.extend(image(arg.content))
        # for Image, we add the image URL
        elif isinstance(arg, Image):
            result.append(arg.image_url["url"])
        # for lists, we recurse
        elif isinstance(arg, list):
            result.extend(image(*arg))
        # for strings, we add them to the result if they are a base64 encoded image
        elif isinstance(arg, str):
            if arg.startswith("data:image/png;base64,") or arg.startswith(
                "data:image/jpeg;base64,"
            ):
                result.append(arg)

    return result


class ToolParameter(BaseModel):
    type: Literal["object", "array", "string", "number", "boolean"]  # extend as needed
    name: str
    description: str
    required: bool = False

    # for object
    properties: Optional[Dict[str, "ToolParameter"]] = None
    additionalProperties: Optional[bool] = None

    # for array
    items: Optional["ToolParameter"] = None

    # for enums (only if needed)
    enum: Optional[List[str]] = None

    def __invariant_attribute__(self, name: str):
        if name in [
            "type",
            "name",
            "description",
            "required",
            "properties",
            "additionalProperties",
            "items",
            "enum",
        ]:
            return getattr(self, name)
        raise InvariantAttributeError(
            f"Attribute {name} not found in ToolParameter. Available attributes are: type, name, description, required, properties, additionalProperties, items, enum"
        )


ToolParameter.model_rebuild()


class Tool(Event):
    name: str
    description: str
    inputSchema: list[ToolParameter]

    def __invariant_attribute__(self, name: str):
        if name in ["name", "description", "inputSchema"]:
            return getattr(self, name)
        raise InvariantAttributeError(
            f"Attribute {name} not found in Tool. Available attributes are: name, description, inputSchema"
        )

    def __str__(self):
        return f"<Tool {self.name} ({self.description})>"

    def __repr__(self):
        return str(self)
