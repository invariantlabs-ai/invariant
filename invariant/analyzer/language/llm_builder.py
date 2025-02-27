"""
LLM-based builder for converting natural language DSL descriptions into valid Invariant Policy Language.
"""

import re
import json
import textwrap
from typing import Dict, List, Optional, Tuple, Union, Any
import anthropic

from invariant.analyzer.language.parser import parse
from invariant.analyzer.policy import Policy

class DSLBuilder:
    """
    A class that uses LLM capabilities to convert natural language DSL descriptions
    into valid Invariant Policy Language syntax.
    """
    policy_examples = textwrap.dedent("""
        1. Policy example to check if an email is sent to someone other than the sender
        raise PolicyViolation("Must not send an email to someone other than the sender", sender=sender, outgoing_mail=outgoing_mail) if:
            # check all get_email -> send_email flows
            (output: ToolOutput) -> (call2: ToolCall) # we need to get output from get_email and then compare it to input of send_email
            output is tool:get_email # check if the tool name is get_email
            call2 is tool:send_email # check if the tool name is send_email
            # get the sender of the retrieved email
            sender := output.content.sender # assume that there is a sender field in tool output
            (outgoing_mail: dict) in call2.function.arguments.emails # assume that the arguments of a function call are in the 'emails' field, each of which has a 'to' field with email address
            outgoing_mail.to != sender # check if the 'to' field of the outgoing mail is not the sender


        2. Policy example to check if unsafe code is executed after visiting an untrusted URL
        from invariant.detectors.code import python_code

        raise "tried to execute unsafe code, after visiting an untrusted URL" if:
            # check all flows of 'get_url' to 'run_python'
            (call_repo: ToolCall) -> (execute_call: ToolCall) # we need to get call_repo from get_url and then compare it to input of run_python
            call_repo is tool:get_url # check if the tool name is get_url
            execute_call is tool:run_python # check if the tool name is run_python
            program_repr := python_code(execute_call.function.arguments.code) # assume that the code to be executed is in the 'code' field of the function call
            "os" in program_repr.imports # check if the 'os' module is imported, which is unsafe

        3. Also you may be interested in the validators from invariant stdlib:
        a. Though the DSL syntax is different, you can import any function from any python standard library (re, json, etc).
        b. You can also create your own predicates using the DSL. Try to use it as much as possible to make policy code more readable. For example:
        is_affirmative(m: Message) :=
            "yes" in m.content or "true" in m.content

        raise PolicyViolation("The assistant should not reply affirmatively", message=msg) if:
            (msg: Message)
            m.role == "assistant"
            is_affirmative(msg)
        b. from invariant.detectors import pii
        raise "PII found" if:
            (msg: Message)
            any(pii(msg.content)) -> will check for PII in the message content. Input is a string or list of strings, output is a list of PII found.
        c. from invariant.detectors.code import python_code
        python_code -> it will parse the code and extract all imports and builtins used.
        d. from invariant.access_control import should_allow_rbac, AccessControlViolation
        user_roles := {"alice": ["user"], "bob": ["admin", "user"]}
        role_grants := {
            "admin": {"public": True, "internal": True},
            "user": {"public": True}
        }
        not should_allow_rbac(message.content, message.type, "alice", user_roles, role_grants) -> will check if the chunk is allowed to be accessed by the user with the given role.
        e. from invariant.detectors import secrets
        raise "Secret found" if:
            (msg: Message)
            any(secrets(msg.content)) -> will check for secrets in the message content. Input is a string or list of strings, output is a list of secrets found.
        f. from invariant.detectors import semgrep
        raise "Vulnerability in python code [risk=medium]" if:
            (call: ToolCall)
            call is tool:python_code
            semgrep_res := semgrep(call.function.arguments.code, lang="python")
            any(semgrep_res)
        """)

    def __init__(self, model_name: str = "claude-3-7-sonnet-20250219", api_key: str = None):
        """
        Initialize the DSL Builder.

        Args:
            model_name: The name of the LLM model to use for parsing.
        """
        self.model_name = model_name
        self.llm_client = anthropic.Anthropic(api_key=api_key)

    def _clean_trace(self, trace: str) -> str:
        """
        Clean a trace by removing long strings (like base64 encoded images).

        Args:
            trace: The raw trace string.

        Returns:
            Cleaned trace with long strings removed.
        """
        # Pattern to match long strings (e.g., base64 encoded data)
        # This looks for strings longer than 100 characters
        pattern = r'("|\')(?:[^"\'\\]|\\.){100,}("|\')'

        # Replace long strings with a placeholder
        cleaned_trace = re.sub(pattern, r'\1<LONG_STRING_REMOVED>\2', trace)
        return cleaned_trace

    def _parse_response(self, response_text: str) -> Tuple[str, str]:
        response_text = response_text.strip("```json\n").strip("\n```")
        response_json = json.loads(response_text)

        # Convert escaped newlines (\n) to actual newlines in the DSL code
        dsl_with_real_newlines = response_json["dsl"].replace('\\n', '\n')

        return dsl_with_real_newlines, response_json["reasoning"]

    def _build_prompt(self, user_dsl: str, trace_example: Optional[Union[str, List, Dict]] = None) -> str:
        """
        Build a prompt for the LLM to convert natural language DSL to valid syntax.

        Args:
            user_dsl: The user's natural language DSL description.
            trace_example: Optional example trace to provide context. Can be a string or parsed JSON.

        Returns:
            A formatted prompt for the LLM.
        """
        prompt = textwrap.dedent(f"""
        # Invariant Policy Language Conversion Task

        Your task is to convert a natural language description of a policy into valid Invariant Policy Language (IPL) syntax.

        ## Invariant Policy Language Examples:
        ```
        {self.policy_examples}
        ```
        """)

        if trace_example:
            if isinstance(trace_example, str):
                cleaned_trace = self._clean_trace(trace_example)
            else:
                # Handle JSON trace
                import json
                cleaned_trace = self._clean_trace(json.dumps(trace_example, indent=2))
            prompt += f"\n## Example Trace (for context):\n```json\n{cleaned_trace}\n```\n"
        else:
            prompt += "\n## Trace format:\nAssume that a trace follows standard OPENAI trace format."

        prompt += f"\n## Natural Language DSL Description:\n```\n{user_dsl}\n```\n"

        prompt += textwrap.dedent("""
        ## Your Task:
        Convert the above natural language description into valid Invariant Policy Language syntax.
        Focus on:
        1. Correct syntax for raise statements
        2. Proper variable declarations
        3. Correct function call syntax
        4. Proper indentation

        ## Output Format:
        Your response should always be structured in JSON with the following keys with no additional text:
        - `reasoning`: <string>    # Explanation for the decision (allowed or not allowed).
        - `dsl`: <string>    # The converted DSL code.
        """)

        return prompt

    def _build_debug_prompt(self, original_dsl: str, previous_attempt: str, error_info: str,
                           trace_example: Optional[Union[str, List, Dict]] = None) -> str:
        """
        Build a prompt for debugging an invalid DSL conversion with error information.

        Args:
            original_dsl: The original natural language DSL.
            previous_attempt: The previous conversion attempt that was invalid.
            error_info: Information about the errors in the previous attempt.
            trace_example: Optional example trace to provide context.

        Returns:
            A debugging prompt for the LLM.
        """
        debug_prompt = textwrap.dedent(f"""
        # DSL Conversion Debugging

        The previous conversion attempt was not valid according to the Invariant Policy Language syntax.

        ## Original Natural Language Description:
        ```
        {original_dsl}
        ```

        ## Previous Conversion Attempt:
        ```
        {previous_attempt}
        ```

        ## Error Information:
        ```
        {error_info}
        ```
        """)

        if trace_example:
            if isinstance(trace_example, str):
                cleaned_trace = self._clean_trace(trace_example)
            else:
                cleaned_trace = self._clean_trace(json.dumps(trace_example, indent=2))
            debug_prompt += f"\n## Example Trace (for context):\n```json\n{cleaned_trace}\n```\n"

        debug_prompt += textwrap.dedent("""
        ## Your Task:
        1. Analyze the error information carefully
        2. Identify the specific issues in the previous conversion attempt
        3. Fix the syntax errors to create valid Invariant Policy Language

        Common issues to check:
        1. Proper indentation
        2. Correct raise statement syntax
        3. Valid function call syntax
        4. Proper variable declarations
        5. Correct parameter extraction

        ## Output Format:
        Your response should always be structured in JSON with the following keys with no additional text:
        - `reasoning`: <string>    # Explanation for the decision (allowed or not allowed).
        - `dsl`: <string>    # The converted DSL code.
        """)

        return debug_prompt

    def build_policy(self,
                    user_dsl: str,
                    trace_example: Optional[Union[str, List, Dict]] = None,
                    max_attempts: int = 3) -> Tuple[bool, str, Optional[Any]]:
        """
        Build a policy from natural language DSL with up to one refinement attempt.

        Args:
            user_dsl: The user's natural language DSL description.
            trace_example: Optional example trace to provide context. Can be a string or parsed JSON.
            max_attempts: Maximum number of attempts (1 or 2).

        Returns:
            Tuple of (is_valid, best_dsl, policy) where:
            - is_valid indicates if the conversion is valid according to the parser
            - best_dsl is the best DSL conversion found
            - policy is the parsed policy object if valid, None otherwise
        """
        # First attempt - direct conversion
        print("Attempt 1: Initial conversion...")
        messages = [
            {"role": "user", "content": self._build_prompt(user_dsl, trace_example)}
        ]
        print(messages[-1])
        response = self.llm_client.messages.create(
            model=self.model_name,
            max_tokens=4000,
            messages=messages
        )
        messages.append({"role": "assistant", "content": response.content[0].text})
        print(messages[-1])
        response_text = response.content[0].text

        try:
            converted_dsl, reasoning = self._parse_response(response_text)
        except (json.JSONDecodeError, AttributeError):
            print("JSON parsing failed: ", response_text)
            raise

        policy_rules = parse(converted_dsl, verbose=False)
        is_valid = len(policy_rules.errors) == 0

        print("Attempt 2: Refinement with error feedback...")
        for attempt in range(max_attempts - 1):
            if is_valid:
                break

            error_info = "\n".join([str(error) for error in policy_rules.errors])

            debug_prompt = self._build_debug_prompt(user_dsl, converted_dsl, error_info, trace_example)
            messages.append({"role": "user", "content": debug_prompt})
            print(messages[-1])
            response = self.llm_client.messages.create(
                model=self.model_name,
                max_tokens=4000,
                messages=messages
            )
            messages.append({"role": "assistant", "content": response.content[0].text})
            print(messages[-1])
            response_text = response.content[0].text
            try:
                converted_dsl, reasoning = self._parse_response(response_text)
            except (json.JSONDecodeError, AttributeError):
                print("JSON parsing failed: ", response_text)
                raise

            policy_rules = parse(converted_dsl, verbose=False)
            is_valid = len(policy_rules.errors) == 0

            if is_valid:
                policy = Policy(policy_rules)
                try:
                    policy.analyze(trace_example)
                except Exception as e:
                    messages.append({"role": "user", "content": f"Policy analysis failed. Try to understand the source of the error and fix the policy. Look at the tract once more: {trace_example}\n\n Error: {e}"})
                    print(messages[-1])
                    is_valid = False


        policy = Policy(policy_rules)
        return is_valid, converted_dsl, policy
