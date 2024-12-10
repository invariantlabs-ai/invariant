<div align="center">
  <h1 align="center"><img src="https://invariantlabs.ai/theme/images/logo.svg"/></h1>
  <h1 align="center">Invariant <code>testing</code></h1>

  <p align="center">
    Helps you build better AI agents through debuggable unit testing
  </p>
  <p align="center">
    

 <a href="https://discord.gg/dZuZfhKnJ4"><img src="https://img.shields.io/discord/1265409784409231483?style=plastic&logo=discord&color=blueviolet&logoColor=white" height=18/></a>

[Documentation](https://explorer.invariantlabs.ai/docs/testing/)

  </p>
</div>
<br/>

Invariant `testing` is a lightweight library to write and run AI agent tests. It provides helpers and assertions that enable you to write robust tests for your agentic applications.

Using localized assertions, testing always points you to the exact part of the agent's behavior that caused a test to fail, making it easy to debug and resolve issues (think: stacktraces for agents).

<br/>
<br/>

<div align="center">
  
<img src="https://github.com/user-attachments/assets/7b568167-7746-4a42-8ebf-6b101e910236" width="70%"/>
</div>

## Installation

```
pip install invariant-ai
```

## A quick example

The example below uses `extract(...)` to detect `locations` from messages. This uses the `gpt-4o` model from OpenAI.

Setup your OpenAI key as

```bash
export OPENAI_API_KEY=<your-key>
```

Code:

```python
# content of tests/test_weather.py
import invariant.testing.functional as F
from invariant.testing import Trace, assert_equals

def test_weather():
    # create a Trace object from your agent trajectory
    trace = Trace(
        trace=[
            {"role": "user", "content": "What is the weather like in Paris?"},
            {"role": "agent", "content": "The weather in London is 75°F and sunny."},
        ]
    )

    # make assertions about the agent's behavior
    with trace.as_context():
        # extract the locations mentioned in the agent's response using OpenAI
        locations = trace.messages()[0]["content"].extract("locations")

        # assert that the agent responded about Paris and only Paris
        assert_equals(1, F.len(locations),
            "The agent should respond about one location only")

        assert_equals("Paris", locations[0], "The agent should respond about Paris")

```

**Execute it on the command line**:

```py
$ invariant test
________________________________ test_weather _________________________________
ERROR: 1 hard assertions failed:

 
    # assert that the agent responded about Paris and only Paris
    assert_equals(1, locations.len(), 
        "The agent should respond about one location only")
    
>   assert_equals("Paris", locations[0], "The agent should respond about Paris")
________________________________________________________________________________

ASSERTION FAILED: The agent should respond about Paris (expected: 'Paris', actual: 'London')
________________________________________________________________________________

#       role:  "user"
#       content:  "What is the weather like in Paris?"
#     },
#     {
#       role:  "agent"
        content:   "The weather in London is 75°F and sunny."
#     },
#  ]
```
The test result precisely [localizes the failure in the provided agent trace](https://explorer.invariantlabs.ai/docs/testing/Writing_Tests/2_Tests/).

**Visual Test Viewer (Explorer):**

As an alternative to the command line, you can also [visualize test results](https://explorer.invariantlabs.ai/docs/testing/Running_Tests/Visual_Debugger/) on the [Invariant Explorer](https://explorer.invariantlabs.ai/):

```py
$ invariant test --push
```

![image](https://github.com/user-attachments/assets/8305e202-0d63-435c-9e71-0988a6f9d24a)


Like the terminal output, the Explorer highlights the relevant ranges, but does so even more precisely, marking the exact words that caused the assertion to fail.

## Features

* Comprehensive `Trace` API for easily navigating and checking agent traces.
* Assertions library to check agent behavior, including fuzzy checkers such as _Levenshtein distance_, _semantic similarity_ and _LLM-as-a-judge_ pipelines.
* Full `pytest` compatibility for easy integration with existing test and CI/CD pipelines.
* Parameterized tests for testing multiple scenarios with a single test function.
* Visual test viewer for exploring large traces and debugging test failures in [Explorer](https://explorer.invariantlabs.ai)

To learn more [read the documentation](https://explorer.invariantlabs.ai/docs/testing/)
