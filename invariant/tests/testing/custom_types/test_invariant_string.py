"""Test cases for the InvariantString class."""

import os
from unittest.mock import patch

import pytest
from pytest import approx

from invariant.testing.custom_types.invariant_bool import InvariantBool
from invariant.testing.custom_types.invariant_number import InvariantNumber
from invariant.testing.custom_types.invariant_string import InvariantString
from invariant.testing.scorers.code import Dependencies
from invariant.testing.utils.packages import is_program_installed


def test_invariant_string_initialization():
    """Test initialization of InvariantString."""
    string = InvariantString("Hello", ["addr1"])
    assert string.value == "Hello"
    assert string.addresses == ["addr1:0-5"]

    # Test default addresses
    string = InvariantString("World")
    assert string.addresses == []
    assert string.len() == 5
    assert string.upper() == "WORLD"
    assert string.lower() == "world"

    # The value field is read-only.
    with pytest.raises(AttributeError, match="'value' attribute cannot be reassigned"):
        string.value = "new value"

    # Test invalid value type
    with pytest.raises(TypeError, match="value must be a str"):
        InvariantString(123)

    # Test invalid addresses type
    with pytest.raises(TypeError, match="addresses must be a list of strings"):
        InvariantString("Hello", [1, 2, 3])


@pytest.mark.parametrize(
    "value1, value2, expected",
    [
        (InvariantString("Hello"), "Hello", True),
        (InvariantString("Hello"), "World", False),
        (InvariantString("Hello"), InvariantString("Hello"), True),
        (InvariantString("Hello"), InvariantString("World"), False),
    ],
)
def test_invariant_string_equality(value1, value2, expected):
    """Test equality of InvariantString objects."""
    result = value1 == value2
    assert isinstance(result, InvariantBool)
    assert result.value == expected


@pytest.mark.parametrize(
    "value1, value2, expected",
    [
        (InvariantString("Hello"), "Hello", False),
        (InvariantString("Hello"), "World", True),
        (InvariantString("Hello"), InvariantString("Hello"), False),
        (InvariantString("Hello"), InvariantString("World"), True),
    ],
)
def test_invariant_string_inequality(value1, value2, expected):
    """Test inequality of InvariantString objects."""
    result = value1 != value2
    assert isinstance(result, InvariantBool)
    assert result.value == expected


@pytest.mark.parametrize(
    "value, substring, expected",
    [
        (InvariantString("Hello World"), "World", True),
        (InvariantString("Hello World"), "world", True),  # Case-insensitive
        (InvariantString("Hello"), "Hell", True),
        (InvariantString("Hello"), "o", True),
        (InvariantString("Hello"), "Goodbye", False),
    ],
)
def test_invariant_string_contains(value, substring, expected):
    """Test the contains method of InvariantString."""
    result = value.contains(substring)
    assert isinstance(result, InvariantBool)
    assert result.value == expected


@pytest.mark.parametrize(
    "value, substrings, expected",
    [
        (InvariantString("Hello World"), ["Hello", "World"], True),
        (InvariantString("Hello World"), ["Hello", "world"], True),
        (InvariantString("Hello World"), ["Hello", "Goodbye"], False),
        (InvariantString("Hello World"), ["Hell", "o", "World"], True),
    ],
)
def test_invariant_string_contains_all(value, substrings, expected):
    """Test the contains_all method of InvariantString."""
    result = value.contains_all(*substrings)
    assert isinstance(result, InvariantBool)
    assert result.value == expected


@pytest.mark.parametrize(
    "value, substrings, expected",
    [
        (InvariantString("Hello World"), ["Hello", "Goodbye"], True),
        (InvariantString("Hello World"), ["goodbye", "farewell"], False),
        (InvariantString("Hello World"), ["Hell", "Bye"], True),
        (InvariantString("Hello World"), ["Goodbye", "Farewell"], False),
    ],
)
def test_invariant_string_contains_any(value, substrings, expected):
    """Test the contains_any method of InvariantString."""
    result = value.contains_any(*substrings)
    assert isinstance(result, InvariantBool)
    assert result.value == expected


@pytest.mark.parametrize(
    "value1, value2, expected_value, expected_addresses",
    [
        (InvariantString("Hello"), "World", "HelloWorld", []),
        (
            InvariantString("Hello", ["addr1"]),
            InvariantString("World", ["addr2"]),
            "HelloWorld",
            ["addr1:0-5", "addr2:0-5"],
        ),
        ("World", InvariantString("Hello", ["addr1"]), "WorldHello", ["addr1:0-5"]),
    ],
)
def test_invariant_string_concatenation(value1, value2, expected_value, expected_addresses):
    """Test the concatenation of InvariantString objects."""
    result = value1 + value2
    assert isinstance(result, InvariantString)
    assert result.value == expected_value
    assert result.addresses == expected_addresses


def test_invariant_string_len_not_implemented():
    """Test the __len__ method of InvariantString is not implemented."""
    with pytest.raises(NotImplementedError):
        len(InvariantString("Hello World"))


def test_invariant_string_get_item():
    """Test the _getitem__ method of InvariantString is not implemented."""
    string1 = InvariantString("Hello")
    assert string1[0] == "H"
    assert string1[-1] == "o"
    assert string1[0:2] == "He"
    assert string1[1:] == "ello"

    # Valid json
    string2 = InvariantString('{"key": "value"}')
    assert string2["key"] == "value"

    # Invalid json
    string2 = InvariantString('{"key": "value"')
    assert string2["key"] is None

    with pytest.raises(TypeError):
        string1[2.0]


def test_invariant_string_count():
    """Test the count method of InvariantString."""
    string1 = InvariantString("Hello World")
    assert string1.count("l") == 3
    assert string1.count("o") == 2
    assert string1.count("z") == 0


def test_invariant_string_str_and_repr():
    """Test string representation of InvariantString."""
    string = InvariantString("Hello", ["addr1"])
    assert str(string) == "InvariantString(value=Hello, addresses=['addr1:0-5'])"
    assert repr(string) == "InvariantString(value=Hello, addresses=['addr1:0-5'])"


def test_contains():
    """Test the contains transformer of InvariantString."""
    # res = InvariantString("hello", ["prefix"]).contains("el")
    # assert len(res.addresses) == 1 and res.addresses[0] == "prefix:1-3"
    assert not InvariantString("hello", [""]).contains("\\d")
    assert InvariantString("hello").contains(InvariantString("el"))


def test_contains_ignores_case_by_default():
    """Test that the contains method of InvariantString ignores case by default."""
    res = InvariantString("hello", ["prefix"]).contains("EL")
    assert len(res.addresses) == 1 and res.addresses[0] == "prefix:1-3"


def test_match():
    """Test the match transformer of InvariantString."""
    res = InvariantString("Dataset: demo\nAuthor: demo-agent", [""]).match("Dataset: (.*)", 1)
    assert res.value == "demo" and res.addresses == [":9-13"]
    res = InvariantString("Dataset: demo\nAuthor: demo-agent", [""]).match(
        "Author: (?P<author>.*)", "author"
    )
    assert res.value == "demo-agent" and res.addresses == [":22-32"]
    res = InvariantString("My e-mail is abc@def.com, and yours?", [""]).match(
        "[a-z\\.]*@[a-z\\.]*", 0
    )
    assert res.value == "abc@def.com" and res.addresses == [":13-24"]


def test_levenshtein():
    """Test the levenshtein transformer of InvariantString."""
    res = InvariantString("hello").levenshtein("hallo")
    assert isinstance(res, InvariantNumber)
    assert res == approx(0.8)

    with pytest.raises(ValueError, match="only supported for string values"):
        InvariantString("hello").levenshtein(other=123)


def test_is_valid_code():
    """Test the is_valid_code transformer of InvariantString."""
    assert InvariantString("def hello():\n\treturn 1").is_valid_code("python")

    res = InvariantString("""a = 2\n2x = a\nc=a""", ["messages.0.content"]).is_valid_code("python")
    assert isinstance(res, InvariantBool)
    assert len(res.addresses) == 1 and res.addresses[0] == "messages.0.content:6-12"
    assert not res

    invalid_json_example = """
    {
        "hello": "world",
        "foo": 'bar',
        "baz": 123
    }
    """

    res = InvariantString(invalid_json_example, ["messages.0.content"]).is_valid_code("json")
    assert isinstance(res, InvariantBool)
    assert len(res.addresses) == 1 and res.addresses[0] == "messages.0.content:33-54"
    assert not res

    assert InvariantString("""{"hello": "world"}""").is_valid_code("json")

    with pytest.raises(ValueError, match="Unsupported language"):
        InvariantString("def hello():\n\treturn 1").is_valid_code("java")


def test_is_similar():
    """Test the is_similar transformer of InvariantString."""
    res = InvariantString("hello", ["prefix"]).is_similar("hallo")
    assert isinstance(res, InvariantBool)
    assert len(res.addresses) == 1 and res.addresses[0] == "prefix:0-5"
    assert not InvariantString("banana").is_similar("quantum", 0.9)

    with pytest.raises(ValueError, match="only supported for string values"):
        InvariantString("hello").is_similar(other=123)


def test_moderation():
    """Test the moderation transformer of InvariantString."""
    res = InvariantString("hello there\ni want to kill them\nbye", [""]).moderation()
    assert isinstance(res, InvariantBool)
    assert len(res.addresses) == 1
    assert res.addresses[0] == ":11-31"


@pytest.mark.parametrize(
    ("model", "client"),
    [
        ("gpt-4o", "OpenAI"),
        pytest.param(
            "claude-3-5-sonnet-20241022",
            "Anthropic",
            marks=pytest.mark.skipif(
                not os.getenv("ANTHROPIC_API_KEY"),
                reason="Skipping because ANTHROPIC_API_KEY is not set",
            ),
        ),
    ],
)
def test_llm(model, client):
    """Test the llm transformer of InvariantString."""
    res = InvariantString("I am feeling great today!").llm(
        "Does the text have positive sentiment?",
        ["yes", "no"],
        model=model,
        client=client,
    )
    assert isinstance(res, InvariantString) and res.value == "yes"
    res = InvariantString("Heute ist ein schöner Tag").llm(
        "Which language is this text in?",
        ["en", "it", "de", "fr"],
        model=model,
        client=client,
    )
    assert isinstance(res, InvariantString) and res.value == "de"


@pytest.mark.parametrize(
    ("model", "client"),
    [
        ("gpt-4o", "OpenAI"),
        pytest.param(
            "claude-3-5-sonnet-20241022",
            "Anthropic",
            marks=pytest.mark.skipif(
                not os.getenv("ANTHROPIC_API_KEY"),
                reason="Skipping because ANTHROPIC_API_KEY is not set",
            ),
        ),
    ],
)
def test_extract(model, client):
    """Test the extract transformer of InvariantString."""
    res = InvariantString(
        "I like apples and carrots, but I don't like bananas.\nThe only thing better than apples are potatoes and pears.",
        ["message.0.content"],
    ).extract("fruits", model=model, client=client)
    assert isinstance(res, list)
    assert len(res) == 4
    assert res[0] == "apples" and res[0].addresses[0] == "message.0.content:7-13"
    assert res[1] == "bananas" and res[1].addresses[0] == "message.0.content:44-51"
    assert res[2] == "apples" and res[2].addresses[0] == "message.0.content:80-86"
    assert res[3] == "pears" and res[3].addresses[0] == "message.0.content:104-109"


@pytest.mark.skipif(not is_program_installed("docker"), reason="Skip for now, needs docker")
def test_execute_without_detect_packages():
    """Test the code execution transformer of InvariantString without detect_packages."""
    code = InvariantString("""def f(n):\treturn n**2""", ["messages.0.content"])
    res = code.execute_contains("25", "print(f(5))")
    assert res
    assert len(res.addresses) == 1 and res.addresses[0] == "messages.0.content:0-21"


@pytest.mark.skipif(not is_program_installed("docker"), reason="Skip for now, needs docker")
def test_execute_with_detect_packages():
    """Test the code execution transformer of InvariantString with detect_packages."""
    with patch("invariant.testing.scorers.code._get_dependencies") as mock_get_dependencies:
        mock_get_dependencies.return_value = Dependencies(dependencies=["numpy"])

        code = InvariantString(
            """import numpy as np; print(np.array([1, 2, 3, 4])**2)""",
            ["messages.0.content"],
        )
        assert code.execute_contains("4", detect_packages=True)
        assert code.execute_contains("9", detect_packages=True)
        assert code.execute_contains("16", detect_packages=True)
