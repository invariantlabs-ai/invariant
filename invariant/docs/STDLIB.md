# Standard Library

The Invariant Security Analyzer comes with a built-in standard library of checkers and predicates that can be used to detect common security issues and data types. The standard library is designed to be extensible, allowing you to add custom checkers and predicates to suit your specific needs.

### Sensitive Data Detection (Personal Identifiable Information)

The standard library includes a set of checkers for detecting sensitive data in agent traces. These checkers can be used to detect and prevent the leakage of personally identifiable information (PII), email addresses, phone numbers, and other sensitive data.

The available checkers are defined in [`invariant/stdlib/detectors/pii.py`](../invariant/stdlib/invariant/detectors/pii.py). For example, it can be used to analyze agent traces for PII leaks:

```python
from invariant.analyzer.detectors import pii

raise PolicyViolation("found pii", msg) if:
    (msg: Message)
    'EMAIL_ADDRESS' in pii(msg)
```

See the [`presidio` documentation](https://microsoft.github.io/presidio/supported_entities/) for an overview of all supported entities and patterns that can be detected by the PII checker.

### Prompt Injection Detection

> **Disclaimer:** Note that classifier-based prompt injection detection [is inherently flawed](https://lve-project.org/blog/how-effective-are-llm-safety-filters.html) and cannot be used as the only security measure, as classifiers can easily be tricked or circumvented. That's why it's important not to rely solely on prompt injection classifiers, but also to leverage more advanced techniques like semantic matching and data flow analysis, as provided by the Invariant analyzer.

The standard library also includes checkers for statically detecting prompt injections that may be contained in individual messages or tool calls. 

The available checkers are defined in [`invariant/stdlib/detectors/prompt_injection.py`](../invariant/stdlib/invariant/detectors/prompt_injection.py). For example, it can be used to analyze agent traces for prompt injections:

```python
from invariant.analyzer.detectors.prompt_injection import prompt_injection

raise PolicyViolation("prompt injection found in tool output", call=out) if:
    (out: ToolOutput)
    prompt_injection(out, threshold=0.8, model="<model>")
```

A `threshold` parameter can be used to adjust the sensitivity of the prompt injection detection, as some classifiers may have a higher false positive rate than others. The `model` parameter can be used to specify the name of the prompt injection detection model as available on [Hugging Face](https://huggingface.co/models).

### Moderation Violation Detection

Another concern when building AI agents is to ensure that the agent's responses are appropriate and do not contain any inappropriate, toxic or harmful content. To address this, the standard library includes checkers for detecting moderation violations in agent responses.

The available checkers are defined in [`invariant/stdlib/detectors/moderated.py`](../invariant/stdlib/invariant/detectors/moderation.py). For example, it can be used to analyze agent traces for moderation violations:

```python
from invariant.analyzer.detectors.moderation import moderated

raise PolicyViolation("assistant message triggered moderation layer", msg=msg) if:
    (msg: Message)
    msg.role == "assistant"
    moderated(msg, cat_thresholds={"self-harm": 0.4})
```

The `cat_thresholds` parameter can be used to specify the threshold for each moderation category, allowing you to adjust the sensitivity of the moderation violation detection.

### Code Analysis

If an AI agent relies on code generation and execution, it is important to ensure that the generated code is safe or restricted to a specific set of operations, to prevent security issues and common forms of agent failure.

For this, the standard library includes checkers for analyzing code, using methods like static code analysis. For instance, the analyzer can be used to detect unsafe code patterns or imports of unsafe modules.

The available checkers are defined in [`invariant/stdlib/detectors/code.py`](../invariant/stdlib/invariant/detectors/code.py). For example, it can be used to analyze agent traces for unsafe code patterns or imports:

```python
from invariant.analyzer.detectors import python_code

raise PolicyViolation("must not use 'os' module in generated code", out=msg) if:
        (msg: Message)
        msg.role == "assistant"
        "os" in python_code(msg.content).imports
```

For instance, this rule checks that the assistant does not generate code that imports the `os` module, which could be used to execute unsafe operations. The standard library function `python_code` automatically parses a string as Python code and extracts information about the code, such as imports, function calls, and more.

### Secrets Scanning

If an AI agent interacts with external services or systems, it is important to ensure that the agent does not leak any sensitive information, such as API keys, passwords, or other secrets. The standard library includes checkers for detecting secrets in agent messages or tool outputs.

The available checkers are defined in [`invariant/stdlib/detectors/secrets.py`](../invariant/stdlib/invariant/detectors/secrets.py). For example, it can be used to analyze agent traces for secret leaks:

```python
from invariant.analyzer.detectors import secrets

raise PolicyViolation("found secrets", msg) if:
    (msg: Message)
    "AWS_ACCESS_KEY" in secrets(msg)
```

The `secrets` function can be used to detect common secret patterns in messages, such as `AWS_ACCESS`. For the list of supported secret patterns, see `SECRETS_PATTERNS` in [this file](../invariant/runtime/utils/secrets.py).

### Custom Checkers

Lastly, you can also provide your own custom checking functions to the analyzer. This can be useful if you have specific security requirements or need to check for custom patterns or conditions that are not covered by the built-in checkers.

Since the Invariant policy language interoperates seamlessly with Python, you can define custom checkers as regular Python functions and use them in your policy rules. For example, you can define a custom checker to detect the presence of a specific keyword in a message:

```python
# in your_project/checkers.py
def contains_hello(msg: dict) -> bool:
    return "hello" in msg["content"]
```

```python
# in Policy.from_string(...)
from your_project.checkers import contains_hello

raise PolicyViolation("message contains 'hello'", msg=msg) if:
    (msg: Message)
    msg.role == "assistant"
    contains_hello(msg)
```

Note that in the implementation of the custom checker, all inputs will be passed as dictionaries, not as classes like `Message` or `ToolOutput`. For property access, you thus must use the dictionary syntax, e.g., `msg["content"]` instead of `msg.content`.