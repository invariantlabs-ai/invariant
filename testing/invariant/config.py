"""The configuration module for the invariant runner."""

from typing import Optional

from pydantic import BaseModel, field_validator


class Config(BaseModel):
    """Configuration settings for the invariant runner."""

    dataset_name: Optional[str]
    push: bool = False
    api_key: Optional[str]
    result_output_dir: str
    agent_params: Optional[dict]

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, api_key_value, info):
        """Ensure that `api_key` is provided if `push` is set to true."""
        push_value = info.data.get("push")
        if push_value and not api_key_value:
            raise ValueError("`INVARIANT_API_KEY` is required if `push` is set to true.")
        return api_key_value
