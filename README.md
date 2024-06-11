<div align="center">
  <h1 align="center">🕵️‍♂️</h1>
  <h1 align="center">Invariant Analyzer for AI Agent Security</h1>

  <p align="center">
    A security scanner for LLM-based AI agents.
  </p>
</div>
<br/>

The Invariant Security Analyzer is an open source security scanner that enables developers to reduce risk when building AI agents by quickly detecting vulnerabilities, bugs, and security threats. The analyzer scans and analyzes an agent's execution traces to identify threats like data leaks, prompt injections, and unsafe code execution.

![Invariant Security Analyzer](https://github.com/invariantlabs-ai/invariant/assets/17903049/709fa811-566b-4623-8601-4cab15bc688c)


## Use Cases

* **Scanning of agent traces** for security violations and data leaks, including tool use and data flow.

* **Real-Time Monitoring of AI agents** to prevent security issues and data breaches during runtime.

To understand better what the analyzer can do, read about one of the example use cases: [Secure Your RAG-based Chat Agent](#enforce-access-control-in-your-rag-based-chat-agent) or  [Prevent Data Leaks In Your Productivity Agent](#prevent-data-leaks-in-your-productivity-agent) 
or [Detect Vulnerabilities in Your Code Generation Systems](#detect-vulnerabilities-in-your-code-generation-agent).

## Why An Agent Security Analyzer?

AI agents are a powerful new paradigm in computing, finding applications in customer support, software engineering, and data analysis. However, these systems are also vulnerable to novel types of security issues like model failure, non-deterministic behavior, prompt injections and data breaches. Due to the versatility and complexity of these systems, traditional security tools and simple safeguards are often insufficient to protect them from sophisticated attacks and failures. The Invariant Security Analyzer is designed to address these challenges by providing an advanced security scanning tool that can track agent behavior and detects security patterns and vulnerabilities, using classifiers, rule-matching and dataflow analysis techniques.

## Features

* Many *built-in checkers* for detecting **sensitive data, prompt injections, moderation violations, and more.**

* Expressive rule language for defining security policies and constraints with support for incremental checking.

* Dataflow analysis for tracking flows of private and untrusted data inbetween agents, APIs and services.

* Real-time monitoring and analysis of AI agents and other tool-calling LLM applications.

* Extensible architecture for adding custom checkers, predicates and data types.

### Getting Started

To get started, you can install the Invariant Security Analyzer using the following command:

```bash
pip install git+https://github.com/invariantlabs-ai/invariant.git
```

You can then import and use the analyzer in your Python code:

```python
from invariant import Policy

# given some message trace
messages = [
    {"role": "user", "content": "What's in my inbox?"},
    # get_inbox
    {"role": "assistant", "content": None, "tool_calls": [{"id": "1","type": "function","function": {"name": "get_inbox","arguments": {}}}]},
    {"role": "tool","tool_call_id": "1","content": [
        {"id": "1","subject": "Hello","from": "Alice","date": "2024-01-01"},
        {"id": "2","subject": "Meeting","from": "Bob","date": "2024-01-02"}
    ]},
    {"role": "user", "content": "Say hello to Alice."},
    # send_email
    {"role": "assistant", "content": None, "tool_calls": [{"id": "2","type": "function","function": {"name": "send_email","arguments": {"to": "Alice","subject": "Hello","body": "Hi Alice!"}}}]}
]

# define a policy
policy = Policy.from_string(
"""
# only allow sending emails to Bob, after retrieving the inbox
raise "must not call send_email after get_inbox" if:
    (call: ToolCall) -> (call2: ToolCall)
    call is tool:get_inbox
    call2 is tool:send_email({
      to: "^(?!Bob$).*$"
    })
""")

# check our message trace for policy violations
policy.analyze(messages)
# => AnalysisResult(errors=[
#   PolicyViolation('must not call send_email after get_inbox')
# ])
```

Here, we define and check a policy that detects scenarios in which an email is sent to someone other than Bob after retrieving the user's inbox. This can be useful for preventing data leaks or unauthorized access to sensitive data

To learn more, for instance how to implement more advanced policies, read the [documentation](#documentation) or continue reading about different [example use cases](#use-cases).

## Use Cases

### Enforce Access Control In Your RAG-based Chat Agent

> **Vulnerability**: An unauthorized user gains access to sensitive data through an agent's retrieval capabilities.

Retrieval-Augmented Generation (RAG) is a popular method to enhance AI agents with private knowledge and data. However, during information retrieval, it is important to ensure that the agent does not violate access control policies, e.g. enabling unauthorized access to sensitive data, especially when strict access control policies are to be enforced.

To detect and prevent this, the analyzer supports the definition of, for instance, role-based access control policies over retrieval results and data sources:

```python
from invariant.access_control import should_allow_rbac, AccessControlViolation

user_roles := {"alice": ["admin", "user"], "bob": ["user"]}}

role_grants := {
  "admin": {"db1": ["read", "write"], "db2": ["read"]}, 
  "user": {"db1": ["read"]}
}

raise AccessControlViolation("unauthorized access", user=input.user, tool=call_result) if:
    # for any retriever call
    (call_result: ToolOutput)
    call_result is tool:retriever
    # check each retrieved chunk
    (chunk: dict) in call_result.results
    # does the current user have access to the chunk?
    not should_allow(chunk, "db1", input.user, user_roles, role_grants)
```

This RBAC policy ensures that only users with the correct roles can access the data retrieved by the agent. If they cannot, the analyzer will raise an `AccessControlViolation` error, which can then be handled by the agent (e.g. by filtering out the unauthorized chunks) or raise an alert to the system administrator.

### Prevent Data Leaks In Your Productivity Agent

> **Vulnerability**: An email agent inadvertently sends sensitive data to unauthorized recipients.

In productivity agents (e.g. personal email assistants), sensitive data is forwarded between components such as email, calendar, and other productivity tools. This opens up the possibility of data leaks, where sensitive information is inadvertently shared with unauthorized parties. To prevent this, the analyzer can be used to check and enforce data flow policies.

For instance, the following policy states, that after retrieving a specific email, the agent must not send an email to anyone other than the sender of the retrieved email:

```python
raise PolicyViolation("Must not send an email to someone other than the sender", sender=sender, outgoing_mail=outgoing_mail) if:
    # check all get_email -> send_email flows
    (call: ToolOutput) -> (call2: ToolCall)
    call is tool:get_email
    call2 is tool:send_email
    # get the sender of the retrieved email
    sender := call.content.sender
    # make sure, all outgoing emails are just replies and not sent to someone else
    (outgoing_mail: dict) in call2.function.arguments.emails
    outgoing_mail.to != sender
```

As shown here, the analyzer can be used to detect the flows of interest, select specific attributes of the data, and check them against each other. This can be used to prevent data leaks and unauthorized data sharing in productivity agents.

### Detect Vulnerabilities in Your Code Generation Agent

> **Vulnerability**: An AI code agent executes unsafe code generated based on untrusted input.

When using AI agents that generate and execute code, a whole new set of security challenges arises. For instance, unsafe code may be generated or the agent may be actively tricked into executing malicious code, which in turn extracts secrets or private data, such as proprietary code, passwords, or other access credentials.

For example, this policy rule detects if an agent made a request to an untrusted URL (for instance, to read the project documentation) and then executes code that relies on the `os` module:

```python
from invariant.detectors.code import python_code

raise "tried to execute unsafe code, after visiting an untrusted URL" if:
    # check all flows of 'get_url' to 'run_python'
    (call_repo: ToolCall) -> (execute_call: ToolCall)
    call_repo is tool:get_url
    execute_call is tool:run_python
    # analyze generated python code
    program_repr := python_code(execute_call.function.arguments.code)
    # check if 'os' module is imported (unsafe)
    "os" in program_repr.imports
```

This policy prevents an agent from following malicious instructions that may be hidden on an untrusted website. This snippet also demonstrates how the analysis extends into the generated code, such as checking for unsafe imports or other security-sensitive code patterns.

## Documentation

Table of Contents

- [Getting Started](#getting-started)
- [Policy Language](#policy-language)
    * [Example Rule](#example-rule)
    * [Trace Format](#trace-format)
    * [Predicates](#predicates)
- [Integration](#integration)
    * [Analyzing Agent Traces](#analyzing-agent-traces)
    * [Real-Time Monitoring of an OpenAI Agent](#real-time-monitoring-of-an-openai-agent)
    * [Real-Time Monitoring of a `langchain` Agent](#real-time-monitoring-of-a-langchain-agent)
    * [Automatic Issue Resolution (Handlers)](#automatic-issue-resolution-handlers)

### Policy Language

The Invariant Policy language is a domain-specific language (DSL) for defining security policies and constraints of AI agents other LLM-based systems. It is designed to be expressive, flexible, and easy to use, allowing users to define complex security properties and constraints in a concise and readable way.

**Origins**: The Invariant policy language is inspired by [Open Policy's Rego](https://www.openpolicyagent.org/docs/latest/policy-language/), [Datalog](https://en.wikipedia.org/wiki/Datalog) and Python. It is designed to be easy to learn and use with a syntax that is familiar to ML engineers and security professionals.

#### Example Rule

A policy consists of a set of rules, each of which defines a security property and the corresponding conditions under which it is considered violated.

A rule is defined using the `raise` keyword, followed by a condition and an optional message:

```python
raise "can only send an email within the organization after retrieving the inbox" if:
    (call: ToolCall) -> (call2: ToolCall)
    call is tool:get_inbox
    call2 is tool:send_email({
      # only emails that do *not* end in acme.com
      to: r"^[^@]*@(?!acme\\.com)"
    })
```

This rule states that an email can only be sent to a receiver with an `acme.com` email address after retrieving the inbox. For this, the specified conditions, or _rule body_, define several constraints that must be satisfied, for the rule to trigger. The rule body consists of two main conditions:

```python
(call: ToolCall) -> (call2: ToolCall)
```

This condition specifies that there must be two consecutive tool calls in the trace, where the data retrieved by the first call can flow into the second call. The `->` operator denotes the data flow relationship between the two calls.

```python
call is tool:get_inbox
call2 is tool:send_email({
    # only emails that do *not* end in acme.com
    to: r"^[^@]*@(?!acme\\.com)"
})
```

Secondly, the first call must be a `get_inbox` call, and the second call must be a `send_email` call with a recipient that does not have an `acme.com` email address, as expressed by the regular expression `^[^@]*@(?!acme\\.com)`. 

If the specified conditions are met, we consider the rule as triggered, and an application of the policy to an agent trace will return the specified error message.

<!-- TODO: talk about `raise PolicyViolation(<msg>, **kwargs)` -->

#### Trace Format

The Invariant Policy Language operates on agent traces, which are sequences of messages and tool calls. For this, a simple JSON-based format is expected as an input to the analyzer. The format consists of a list of messages, based on the [OpenAI chat format](https://platform.openai.com/docs/guides/text-generation/chat-completions-api).

For this we define the following structural types. To be addressable in the policy language, all messages passed to the analyzer must be in the following format:

##### `Message`

```python
class Message:
    role: str
    content: str
    tool_calls: Optional[List[ToolCall]]

# Example input representation
{ "role": "user", "content": "Hello, how are you?" }
```

* **role** (str): The role of the message, e.g. "user", "assistant", or "system".
* **content** (str): The content of the message, e.g. a chat message or a tool call.
* **tool_calls** (Optional[List[ToolCall]]): A list of tool calls made by the agent in response to the message.

##### `ToolCall`
```python
class ToolCall:
    id: str
    type: str
    function: FunctionCall
class FunctionCall:
    name: str
    arguments: Dict[str, Any]

# Example input representation
{"id": "1","type": "function","function": {"name": "get_inbox","arguments": {"n": 10}}}
```

* **id** (str): A unique identifier for the tool call.
* **type** (str): The type of the tool call, e.g. "function".
* **function** (FunctionCall): The function call made by the agent.
    * **name** (str): The name of the function called.
    * **arguments** (Dict[str, Any]): The arguments passed to the function.

##### `ToolOutput`

```python
class ToolOutput:
    role: str = "tool"
    tool_call_id: str
    content: str | dict

# Example input representation
{"role": "tool","tool_call_id": "1","content": {"id": "1","subject": "Hello","from": "Alice","date": "2024-01-01"}]}
```

* **tool_call_id** (str): The identifier of a previous `ToolCall` that this output corresponds to.
* **content** (str | dict): The content of the tool output, e.g. the result of a function call. This can be a parsed dictionary or a string of the JSON output.
 
##### Trace Example

The format suitable for the analyzer is a list of messages like the one shown here:

```python 
messages = [
    # Message(role="user", ...):
    {"role": "user", "content": "What's in my inbox?"}, 
    # Message(role="assistant", ...):
    {"role": "assistant", "content": None, "tool_calls": [
        # ToolCall
        {"id": "1","type": "function","function": {"name": "get_inbox","arguments": {}}}
    ]}, 
    # ToolOutput:
    {"role": "tool","tool_call_id": "1","content": [ 
        {"id": "1","subject": "Hello","from": "Alice","date": "2024-01-01"},
        {"id": "2","subject": "Meeting","from": "Bob","date": "2024-01-02"}
    ]},
    # Message(role="user", ...):
    {"role": "user", "content": "Say hello to Alice."}, 
]
```

`ToolCalls` must be nested within `Message(role="assistant")` objects, and `ToolOutputs` are their own top-level objects.

#### Predicates

If repetitive conditions and patterns arise in your policies, you can define predicates to encapsulate these conditions and reuse them across multiple rules. Predicates are defined as follows:

```python
is_affirmative(m: Message) := 
    "yes" in m.content or "true" in m.content

raise PolicyViolation("The assistant should not reply affirmatively", message=msg) if:
    (msg: Message)
    m.role == "assistant"
    is_affirmative(msg)
```

Here, we define a predicate `is_affirmative_assistant` that checks if a message's content contains the words "yes" or "true". We then use this predicate in a rule that checks if the assistant specifically replies in an affirmative manner as defined by the predicate.

<!-- TODO #### Value Matching: write more about <EMAIL>, <LOCATION>, regex and moderated content matching-->

<!-- TODO #### External Functions and Standard Library: write about different parts of the stdlib library, how to important functions and where they are defined -->

### Integration

The Invariant Policy Language is used by the security analyzer and can be used either to detect and uncover security issues with pre-recorded agent traces or to monitor agents in real-time. 

The following sections discuss both use cases in more detail, including how to monitor [OpenAI-based](#real-time-monitoring-of-an-openai-agent) and [`langchain`](#real-time-monitoring-of-a-langchain-agent) agents.

#### Analyzing Agent Traces

The simplest way to use the analyzer is to analyze a pre-recorded agent trace. This can be useful to learning more about one's agent's behavior and to detect potential security issues.

To get started, make sure your traces are in [the expected format](#trace-format) and define a policy that specifies the security properties you want to check for. Then, you can use the `Policy` class to analyze the trace:

```python
from invariant import Policy

# simple chat messages
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the temperature in Paris, France?"},
    # assistant calls tool
    {
        "role": "assistant", 
        "content": None, 
        "tool_calls": [
            {
                "id": "1",
                "type": "function",
                "function": {
                    "name": "get_temperature",
                    "arguments": {
                        "x": "Paris, France"
                    }
                }
            }
        ]
    },
    {
        "role": "tool",
        "tool_call_id": "1",
        "content": 2001
    }
]

policy = Policy.from_string(
r"""
from invariant import Message, match, PolicyViolation, ToolCall, ToolOutput

# check that the agent does not leak location data
raise PolicyViolation("Location data was passed to a get_temperature call", call=call) if:
    (call: ToolCall)
    call is tool:get_temperature({
        x: <LOCATION>
    })

# check that the temperature is not too high
raise PolicyViolation("get_temperature returned a value higher than 50", call=call) if:
    (call: ToolOutput)
    call.content > 50
""")

policy.analyze(messages)
# AnalysisResult(
#   errors=[
#     PolicyViolation(Location data was passed to a get_temperature call, call={'id': '1', 'type': 'function', 'function':
#     {'name': 'get_temperature', 'arguments': {'x': 'Paris, France'}}})
#     PolicyViolation(get_temperature returned a value higher than 50, call={'role': 'tool', 'tool_call_id': '1', 'content':
#     2001})
#   ]
# )
```

In this example, we define a policy that checks two things: (1) whether location data is passed to a `get_temperature` call, and (2) whether the result is higher than 50. These properties may be applicable when the agent is not supposed to handle location data, to prevent leaking personally-identifiable data (PII), or when the temperature is expected to be below a certain threshold (e.g. for sanity checks). For PII checks, the analyzer relies on the [`presidio-analyzer`](https://github.com/microsoft/presidio) library, but can also be extended to detect and classify other types of sensitive data. 

Since both specified security properties are violated by the given message trace, the analyzer returns an `AnalysisResult` with two `PolicyViolation` errors.

#### Real-Time Monitoring of an OpenAI Agent

The analyzer can also be used to monitor AI agents in real-time. This allows you to prevent security issues and data breaches before they happen, and to take the appropriate steps to secure your deployed agents.

For instance, consider the following example of an OpenAI agent based on OpenAI tool calling:

```python
from invariant import Monitor
from openai import OpenAI

# create an Invariant Monitor initialized with a policy
monitor = Monitor.from_string(
"""
raise PolicyViolation("Disallowed tool sequence", a=call1, b=call2) if:
    (call1: ToolCall) -> (call2: ToolCall)
    print(call1, call2)
    call1 is tool:something
    call1.function.arguments["x"] > 2
    call2 is tool:something_else
""", raise_unhandled=True)

# ... (prepare OpenAI agent)

# in the core agent loop
while True:
    # determine next agent action
    model_response = <invoke LLM>
    messages.append(model_response.to_dict())

    # 1. check message trace for security violations
    monitor.check(messages)
    
    # actually call the tools, inserting results into 'messages'
    for tool_call in model_response.tool_calls:
        # ...
    
    # (optional) check message trace again to detect violations
    # in tool outputs right away (e.g. before sending them to the user)
    monitor.check(messages)
```
> For the full snippet, see [invariant/examples/openai_agent_example.py](./invariant/examples/openai_agent_example.py)

To enable real-time monitoring for policy violations you can use a `Monitor` as shown, and integrate it into your agent's execution loop. With a `Monitor`, policy checking is performed eagerly, i.e. after each tool call, to ensure that the agent does not violate the policy at any point in time.

This way, all tool interactions of the agent are monitored in real-time. As soon as a violation is detected, an exception is raised. This stops the agent from executing a potentially unsafe tool call and allows you to take appropriate action, such as filtering out the call or ending the session.


#### Real-Time Monitoring of a `langchain` Agent

To monitor a `langchain`-based agent, you can use a `MonitoringAgentExecutor`, which will automatically intercept tool calls and check them against the policy, before they are executed.

```python
from invariant import Monitor
from invariant.integrations.langchain_integration import MonitoringAgentExecutor

from langchain_openai import ChatOpenAI
from langchain.agents import tool, create_openai_functions_agent
from langchain import hub

monitor = Monitor.from_string(
"""
raise PolicyViolation("Disallowed tool call sequence", a=call1, b=call2) if:
    (call1: ToolCall) -> (call2: ToolCall)
    call1 is tool:something
    call1.function.arguments["x"] > 2
    call2 is tool:something_else
""")

# setup prompt+LLM
prompt = hub.pull("hwchase17/openai-functions-agent")
llm = ChatOpenAI(model="gpt-4o")

# define the tools
@tool def something(x: int) -> int: ...
@too def something_else(x: int) -> int: ...
# construct the tool calling agent
agent = create_openai_functions_agent(llm, [something, something_else], prompt)

# create a monitoring agent executor
agent_executor = MonitoringAgentExecutor(agent=agent, tools=[something, something_else],
                                         verbose=True, monitor=monitor)
```
> For the full snippet, see [invariant/examples/lc_flow_example.py](./invariant/examples/lc_flow_example.py)

The `MonitoringAgentExecutor` will automatically check all tool calls, ensuring that the agent never violates the policy. If a violation is detected, the executor will raise an exception.

#### Automatic Issue Resolution (Handlers)

Invariant Analyzer also offers an extension that enables to specify automatic issue resolution handlers. These handlers can be used to automatically resolve detected security issues, allowing the agent to continue its execution without manual intervention. 

However, this feature is still _under development_ and not intended to be used in its current form (experimental). For a preview, see [invariant/examples/lc_example.py](./invariant/examples/lc_example.py) for an example of how to use handlers in a monitored `langchain` agent.

### Roadmap

_More Information Coming Soon_

## Development

This project uses [`rye`](https://github.com/astral-sh/rye). To setup a development environment, run:

```bash
rye sync
```

### Testing 

To run all standard unit tests, run:

```bash
rye test
```

To run all example snippets in `invariant/examples/` as unit tests, run:

```bash
rye run python -m unittest discover -s invariant/examples -p "*_example.py"
```

### Dependency Management and Extras

Due to the nature of the analyzer and the included checkers in the standard library, not all dependencies are specified as direct dependency in `pyproject.toml`'s main `[project]` section. Instead, for dependencies that are not required for the core functionality of the analyzer, we use runtime dependency resolution, as implemented by the class `Extra` in `invariant/extras.py`.

For instance, a module that relies on `presidio-analyzer`, can import it using the following code:

```python
# in extras.py you'll have
presidio_extra = Extra("PII and Secrets Scanning (using Presidio)", "Enables the detection of personally identifiable information (PII) and secret scanning in text", {
    "presidio_analyzer": ExtrasImport("presidio_analyzer", "presidio-analyzer", ">=2.2.354"),
    "spacy": ExtrasImport("spacy", "spacy", ">=3.7.5")
})

# to then import a component from the `presidio_analyzer` package, you can use
AnalyzerEngine = presidio_extra.package("presidio_analyzer").import_names('AnalyzerEngine')
```


This way, the analyzer can operate without many of the extra dependencies, but as soon as a feature that requires an `Extra` dependency is used (e.g. the code above runs), it will prompt the user to install the required dependencies, with the option to automatically install them using `pip`.

To learn more about all available extras, you can run the `invariant-cli list` command after installing the analyzer. This gives you a list of all available extras and their descriptions. If you want to install an extra already before the first use, you can use `invariant-cli add <extra>` to install any `Extra` ahead of time.

**Testing** If you need to write tests that require extra dependencies to be installed, you can declare the relevant `test_*` methods using the following decorator:

```python
from invariant.extras import extras_available, presidio_extra

class TestSomething:
    @unittest.skipUnless(extras_available(presidio_extra), "presidio-analyzer is not installed")
    def test_presidio_analyzer(self):
        ...
```

This way, all relevant tests will be skipped if the required dependencies are not installed, allowing us to test setups with and without the extra dependencies in place.

For convenience, all extra dependencies are also specified as a dev dependency in `pyproject.toml`'s `[tool.rye.dev-dependencies]` section, so that they are automatically installed when running `rye sync`. This way, during development, all extra dependencies will always be installed, even though testing without them is recommended. If you want to test a setup without any extra dependencies, you can simply run `rye sync --no-dev` to install only the core dependency set.