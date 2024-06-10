<div align="center">
  <h1 align="center">🕵️‍♂️</h1>
  <h1 align="center">Invariant Security Analyzer</h1>

  <p align="center">
    A security scanner for LLM-based AI agents.
  </p>
</div>
<br/>

The Invariant Security Analyzer (ISA) is an open source security scanner for detecting vulnerabilities and security threats in AI agents. It scans and analyzes an agent's execution traces to identify security threats like data leaks.

![Invariant Security Analyzer](https://github.com/invariantlabs-ai/invariant/assets/17903049/709fa811-566b-4623-8601-4cab15bc688c)


## Use Cases

* **Scanning of agent traces** for security violations and data leaks, including tool use and data flow.

* **Real-Time Monitoring of AI agents** to prevent security issues and data breaches during runtime.

To understand better what ISA can do, read about one of the example use cases: [Secure Your RAG-based Chat Agent](#enforce-access-control-in-your-rag-based-chat-agent) or  [Prevent Data Leaks In Your Productivity Agent](#prevent-data-leaks-in-your-productivity-agent) 
or [Detect Vulnerabilities in Your Code Generation Systems](#detect-vulnerabilities-in-your-code-generation-agent).

## Why An Agent Security Analyzer?

AI agents are a powerful new paradigm in computing, finding applications in customer support, software engineering, and data analysis. However, these systems are also vulnerable to novel types of security issues like model failure, non-deterministic behavior, prompt injections and data breaches. Due to the versatility and complexity of these systems, traditional security tools and simple safeguards are often insufficient to protect them from sophisticated attacks and failures. The Invariant Security Analyzer (ISA) is designed to address these challenges by providing an advanced security scanning tool that can track agent behavior and detects security patterns and vulnerabilities, using classifiers, rule-matching and dataflow analysis techniques.

## Features

* Many *built-in checkers* for detecting **sensitive data, prompt injections, moderation violations, and more.**

* Expressive rule language for defining security policies and constraints with support for incremental checking.

* Dataflow analysis for tracking flows of private data within agents, APIs and services.

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

Retrieval-Augmented Generation (RAG) is a populare method to enhance AI agents with private knowledge and data. However, during information retrieval, it is important to ensure that the agent does not violate access control policies, e.g. enabling unauthorized access to sensitive data, especially when strict access control policies are to be enforced.

To detect and prevent this, ISA supports the definition of, for instance, role-based access control policies over retrieval results and data sources:

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

This RBAC policy ensures that only users with the correct roles can access the data retrieved by the agent. If they cannot, the analyzer will raise an `AccessControlViolation` error, which can then be handled by the agent (e.g. by filtering out the unauthorized chunks) or logged, if detected offline when analyzing recorded agent traces.

### Prevent Data Leaks In Your Productivity Agent

> **Vulnerability**: An email agent inadvertently sends sensitive data to unauthorized recipients.

In productivity agents (e.g. personal email assistants), sensitive data is forwarded between components such as email, calendar, and other productivity tools. This opens up the possibility of data leaks, where sensitive information is inadvertently shared with unauthorized parties. To prevent this, ISA can be used to check and enforce data flow policies.

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

As shown here, ISA can be used to detect the flows of interest, select specific attributes of the data, and check them against each other. This can be used to prevent data leaks and unauthorized data sharing in productivity agents.

### Detect Vulnerabilities in Your Code Generation Agent

> **Vulnerability**: An AI code agent executes unsafe code generated based on untrusted input.

When using AI agents that generate and execute code, a whole new set of security challenges arises. For instance, unsafe code may be generated or the agent may be actively tricked into executing malicious code, which in turn extracts secrets or private data, such as proprietary code, passwords, or other access credentials.

For example, this policy rule detects if an agent has read an untrusted URL and then executes code that relies on the `os` module:

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

This policy prevents an agent from following malicious instructions that may be hidden on an untrusted website. This snippet also demonstrates how ISA's analysis extends into the generated code, such as checking for unsafe imports or other security-sensitive code patterns.

## Documentation

Contents

- [Getting Started](#getting-started)
- [Policy Language](#policy-language)
- [Integration](#integration)
    * [Analyzing Agent Traces](#analyzing-agent-traces)
    * [Real-Time Monitoring of an OpenAI Agent](#real-time-monitoring-of-an-openai-agent)
    * [Real-Time Monitoring of a `langchain` Agent](#real-time-monitoring-of-a-langchain-agent)

### Policy Language

### Integration

#### Analyzing Agent Traces
TODO

#### Real-Time Monitoring of an OpenAI Agent
TODO

#### Real-Time Monitoring of a `langchain` Agent
TODO

### Roadmap

_Coming soon_