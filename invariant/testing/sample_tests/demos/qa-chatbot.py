import openai
import pytest
from invariant.testing import Trace, assert_true, get_agent_param
from invariant.testing import functional as F
from invariant.testing.custom_types.trace_factory import TraceFactory


def run_agent(prompt: str) -> Trace:
    agent_prompt = get_agent_param("prompt")
    agent_model = get_agent_param("model")

    client = openai.OpenAI()
    messages = [
        {"role": "system", "content": agent_prompt},
        {"role": "user", "content": prompt},
    ]
    response = client.chat.completions.create(
        model=agent_model,
        messages=messages,
    )
    return TraceFactory.from_openai(
        messages + [response.choices[0].message.model_dump()]
    )


@pytest.mark.parametrize(
    "country,capital",
    [
        ("France", "Paris"),
        ("Germany", "Berlin"),
        ("Italy", "Rome"),
        ("Spain", "Madrid"),
    ],
)
def test_capitals(country, capital):
    trace = run_agent(f"What's the capital of {country}?")
    with trace.as_context():
        assert_true(trace.messages(role="assistant")[0]["content"].contains(capital))


@pytest.mark.parametrize("n", [5, 10])
def test_emails(n):
    trace = run_agent(f"Write {n} randomly generated e-mail addresses")
    with trace.as_context():
        emails = list(
            trace.messages(role="assistant")[0]["content"].match_all(
                r"[a-zA-Z0-9_\.]+@[a-zA-Z0-9\._]+"
            )
        )
        assert_true(F.len(emails) == n)


def test_small_big():
    trace = run_agent("What is the opposite of small? Answer with one word only.")
    with trace.as_context():
        assert_true(trace.messages(role="assistant")[0]["content"].is_similar("big"))


def test_haiku():
    trace = run_agent("Write a haiku that mentions 7 cities in Switzerland")
    with trace.as_context():
        msg = trace.messages(role="assistant")[0]["content"]
        assert_true(F.len(msg.extract("city in Switzerland")) == 7)


def test_python_code():
    trace = run_agent(
        "Write a function that takes a list of numbers and returns the sum of the squares of the numbers"
    )
    with trace.as_context():
        msg = trace.messages(role="assistant")[0]["content"]
        if "```python" in msg:
            code = msg.match("```python(.*)```", 1)
            assert_true(code.is_valid_code("python"))
        else:
            res = msg.is_valid_code("python")
            assert_true(res)
