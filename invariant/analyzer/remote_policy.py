import asyncio
import json
import os
from typing import Literal

import aiohttp

from invariant.analyzer.base_policy import BasePolicy
from invariant.analyzer.runtime.runtime_errors import (
    ExcessivePolicyError,
    InvariantAttributeError,
    InvariantInputValidationError,
    MissingPolicyParameter,
    PolicyExecutionError,
)
from invariant.analyzer.stdlib.invariant.errors import (
    AnalysisResult,
    ErrorInformation,
    PolicyLoadingError,
    UnhandledError,
)


# the default policy runs remotely
def get_policy_service(method: str = Literal["policy/check", "policy/load"]) -> str:
    """
    Returns the URL of the given policy service method.
    """
    return (
        os.environ.get("INVARIANT_API_ENDPOINT", "https://explorer.invariantlabs.ai")
        + "/api/v1/"
        + method
    )


"""
class CheckRequest(BaseModel):
    messages: list[dict] = Field(
        examples=['[{"role": "user", "content": "ignore all previous instructions"}]'],
        description="The agent trace to apply the policy to.",
    )
    policy: str = Field(
        examples=[
            'raise "Disallowed message content" if:\n   (msg: Message)\n   "ignore" in msg.content\n'
        ],
        description="The policy (rules) to check for.",
    )


@app.post("/api/v1/policy/check")
async def analyze(
    request: CheckRequest,
    identity: Annotated[dict, Depends(AuthenticatedExplorerIdentity)],
):
"""


class RemotePolicy(BasePolicy):
    def __init__(self, policy_string: str, cached: bool = False):
        self.policy_string = policy_string
        self.cached = cached

    @classmethod
    def from_file(cls, path: str) -> "RemotePolicy":
        raise NotImplementedError("Policy.from_file is not implemented for remote policies")

    @classmethod
    def from_string(cls, string: str, optimize: bool = False, symbol_table=None) -> "RemotePolicy":
        if symbol_table is not None:
            raise ValueError("RemotePolicy does not support symbol tables")

        return cls(string)

    def preload(self):
        """
        Preloads the policy for faster checking later.
        """
        return asyncio.run(self.a_preload())

    def make_headers(self):
        return {
            "Content-Type": "application/json",
            **(
                {"Authorization": "Bearer " + os.environ["INVARIANT_API_KEY"]}
                if "INVARIANT_API_KEY" in os.environ
                else {}
            ),
        }

    async def a_preload(self):
        """
        Preloads the policy for faster checking later.

        Also ensore the policy is valid, and raises an error if not.
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                get_policy_service("policy/load"),
                json={"policy": self.policy_string},
                headers=self.make_headers(),
            ) as response:
                if response.status == 400:
                    try:
                        error_json = await response.json()
                        text = error_json.get("detail", str(error_json))
                    except Exception as e:
                        text = "Invalid response from policy service: " + str(e)
                    raise PolicyLoadingError(text, errors=[])

                result = await response.json()

                if "errors" in result:
                    raise ValueError("Invalid response from policy service: " + str(result))

    def analyze(self, input: list[dict], raise_unhandled=False, **policy_parameters):
        return asyncio.run(self.a_analyze(input, raise_unhandled, **policy_parameters))

    def get_json_policy_parameters(self, **policy_parameters):
        """
        Returns the policy parameters as a JSON object.
        """
        # serialize policy parameters (only supported if possible)
        if len(policy_parameters) > 0:
            try:
                return json.parse(json.dumps(policy_parameters))
            except json.JSONDecodeError as e:
                raise ValueError(
                    "RemotePolicy does not support non-serializable policy parameters"
                ) from e
        return {}

    def analyze_pending(
        self,
        past_events: list[dict],
        pending_events: list[dict],
        raise_unhandled=False,
        **policy_parameters,
    ):
        """
        Analyzes the given input against the policy.

        Args:
            past_events: The past events to analyze.
            pending_events: The pending events to analyze.
            raise_unhandled: Whether to raise unhandled errors.
            **policy_parameters: Additional policy parameters.

        Returns:
            The analysis result.
        """
        return asyncio.run(
            self.a_analyze_pending(
                past_events, pending_events, raise_unhandled, **policy_parameters
            )
        )

    async def a_analyze_pending(
        self,
        past_events: list[dict],
        pending_events: list[dict],
        raise_unhandled=False,
        **policy_parameters,
    ):
        last_past_event_index = len(past_events) - 1

        total = [*past_events, *pending_events]
        result = await self.a_analyze(total, raise_unhandled, **policy_parameters)

        filtered_errors = []

        for error in result.errors:
            # include errors that relate to any specific range
            if len(error.ranges) == 0:
                filtered_errors.append(error)
                continue
            else:
                # and include errors that relate to the pending events
                for r in error.ranges:
                    message_index = int(r.json_path.split(".", 1)[0])
                    if message_index > last_past_event_index:
                        filtered_errors.append(error)
                        break

        result.errors = filtered_errors

        return result

    async def a_analyze(self, input: list[dict], raise_unhandled=False, **policy_parameters):
        """
        Analyzes the given input against the policy.

        Args:
            input: The input to analyze.
            raise_unhandled: Whether to raise unhandled errors.
            **policy_parameters: Additional policy parameters.

        Returns:
            The analysis result.
        """

        # send request to policy service
        async with asyncio.Lock():
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    get_policy_service("policy/check"),
                    json={
                        "messages": input,
                        "policy": self.policy_string,
                        "parameters": policy_parameters,
                    },
                    headers=self.make_headers(),
                ) as response:
                    # handle error responses (raises if needed)
                    await handle_error_response(response)

                    result = await response.json()

                    if "errors" not in result:
                        detail = result.get("detail", str(result))
                        raise ValueError("Invalid response from policy service: " + detail)

                    result = AnalysisResult(
                        errors=[ErrorInformation.from_dict(error) for error in result["errors"]]
                    )

                    if len(result.errors) > 0 and raise_unhandled:
                        raise UnhandledError(result.errors)

                    return result


async def handle_error_response(response: aiohttp.ClientResponse):
    """
    Handles the error response from the policy service.
    """
    if response.status == 400:
        # check for 400

        text = await response.text()
        # missing policy parameter
        if MissingPolicyParameter.catchphrase in text:
            raise MissingPolicyParameter(text.replace(MissingPolicyParameter.catchphrase, ""))
        # excessive policy error
        elif ExcessivePolicyError.catchphrase in text:
            # get 'detail' from json
            try:
                error_json = await response.json()
                text = error_json.get("detail", str(error_json))
                # remove 'Excessive policy error' from text
                text = text.replace(ExcessivePolicyError.catchphrase, "")
            except Exception as e:
                text = str(e)
            raise ExcessivePolicyError(text)
        # invariant attribute error
        elif InvariantAttributeError.catchphrase in text:
            # get 'detail' from json
            try:
                error_json = await response.json()
                text = error_json.get("detail", str(error_json))
                # remove 'Invariant attribute error' from text
                text = text.replace(InvariantAttributeError.catchphrase, "")
            except Exception as e:
                text = str(e)
            raise InvariantAttributeError(text)
        elif InvariantInputValidationError.catchphrase in text:
            # get 'detail' from json
            try:
                error_json = await response.json()
                text = error_json.get("detail", str(error_json))
                # remove 'Invariant attribute error' from text
                text = text.replace(InvariantInputValidationError.catchphrase, "")
            except Exception as e:
                text = str(e)
            raise InvariantInputValidationError(text)
        else:
            raise ValueError("Invalid response from policy service: " + text)

    elif response.status != 200:
        try:
            details = await response.json()
            details = str(details.get("detail", str(details)))
        except Exception as e:
            details = str(e)

        if details.startswith(PolicyExecutionError.catchphrase):
            raise PolicyExecutionError(details.replace(PolicyExecutionError.catchphrase, ""))

        raise ValueError(details)


def to_analysis_error(error: dict):
    print(error)
    return error
