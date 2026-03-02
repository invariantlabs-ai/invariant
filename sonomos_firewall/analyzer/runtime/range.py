from typing import Optional

from pydantic import BaseModel


class Range(BaseModel):
    """
    Represents a range in the input object that is relevant for
    the currently evaluated expression.

    A range can be an entire object (start and end are None) or a
    substring (start and end are integers, and object_id refers to
    the object that the range is part of).
    """

    object_id: Optional[str]
    start: Optional[int]
    end: Optional[int]

    # json path to this range in the input object (not always directly available)
    # Use Input.locate to generate the JSON paths
    json_path: Optional[str] = None

    @classmethod
    def from_object(cls, obj, start=None, end=None):
        if type(obj) is dict and "__origin__" in obj:
            obj = obj["__origin__"]
        return cls(object_id=str(id(obj)), start=start, end=end)

    def match(self, obj):
        if self.object_id is None:
            return False
        if isinstance(obj, str):
            return self.value == obj or str(id(obj)) == self.object_id
        return str(id(obj)) == self.object_id

    def to_address(self):
        path = "messages" + (("." + self.json_path) if self.json_path else "")
        if self.start is not None and self.end is not None and ":" not in path:
            path += f":{self.start}-{self.end}"

        return path

    @classmethod
    def from_address(cls, address: str):
        # check for :<start>-<end>
        if ":" in address:
            _, start_end = address.split(":")
            start_str, end_str = start_end.split("-")
            start = int(start_str)
            end = int(end_str)
        else:
            start = None
            end = None

        if address.startswith("messages."):
            return cls(object_id=None, json_path=address[9:], start=start, end=end)
        else:
            return cls(object_id=None, json_path=address, start=start, end=end)
