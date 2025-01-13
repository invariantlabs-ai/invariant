import re

import urllib3
from invariant.testing import (
    Trace,
    TraceFactory,
    assert_false,
    assert_true,
    expect_true,
)
from invariant.testing.custom_types.invariant_image import InvariantImage

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def does_not_click_on_firefox_menu(trace: Trace):
    """Given a trace, assert that the agent does not click on the firefox hamburger menu on the right."""
    tool_outs = trace.messages(role="tool")
    for tool_out in tool_outs:
        if isinstance(tool_out["content"], InvariantImage):
            assert_false(
                tool_out["content"].ocr_contains("New tab")
                and tool_out["content"].ocr_contains("New window")
            )


def does_not_make_python_error(trace: Trace):
    """Given a trace, assert that the agent does not make a python error."""
    tool_outs = trace.messages(role="tool")
    for tool_out in tool_outs:
        assert_false(tool_out["content"].contains("ModuleNotFoundError"))


def does_not_make_file_edit_errors(trace: Trace):
    """Given a trace, assert that the agent does not make a file edit error."""
    tool_outs = trace.messages(role="tool")
    for tool_out in tool_outs:
        assert_false(
            tool_out["content"].contains(
                "Cannot overwrite files using command `create`."
            )
        )


global_asserts = [
    does_not_click_on_firefox_menu,
    does_not_make_python_error,
    does_not_make_file_edit_errors,
]


def run_agent(prompt: str) -> Trace:
    if "annotate" in prompt:
        return TraceFactory.from_explorer("mbalunovic/tests-1732714692", 1)
    elif "100 traces" in prompt:
        return TraceFactory.from_explorer("mbalunovic/tests-1732714692", 2)
    elif "chats-about-food" in prompt:
        return TraceFactory.from_explorer("mbalunovic/tests-1732714692", 3)
    elif "anthropic" in prompt:
        return TraceFactory.from_explorer("mbalunovic/tests-1732714692", 4)
    elif "fastapi" in prompt:
        return TraceFactory.from_explorer("mbalunovic/tests-1732714692", 5)
    elif "fibonacci" in prompt:
        return TraceFactory.from_explorer("mbalunovic/tests-1732714692", 6)


def test_annotation():
    trace = run_agent(
        """Go to this snippet https://explorer.invariantlabs.ai/trace/9d55fa77-18f5-4a3b-9f7f-deae06833c58
        and annotate the first comment with: "nice nice" """
    )

    with trace.as_context():
        trace.run_assertions(global_asserts)
        assert_true(trace.messages(0)["content"].contains("nice nice"))

        type_tool_calls = trace.tool_calls(
            {"arguments.action": "type", "name": "computer"}
        )

        # assert that it doesn't type in the same url twice
        num_occ = {}
        for tc in type_tool_calls:
            text = tc.argument("text").value
            num_occ[text] = num_occ.get(text, 0) + 1
            if "http" in text:
                expect_true(num_occ[text] <= 1)

        # assert that the last screenshot contains the text "annotated" and text "nice nice"
        last_screenshot = trace.messages(role="tool")[-1]["content"]
        assert_true(last_screenshot.ocr_contains("annotated"))
        assert_true(last_screenshot.ocr_contains("nice nice"))


def test_firefox_menu():
    trace = run_agent("""upload a dataset of 100 traces using a browser""")
    with trace.as_context():
        trace.run_assertions(global_asserts)


def test_module_error():
    trace = run_agent(
        """create an empty dataset "chats-about-food", then use sdk to push 4 different traces 
    to it and then finally use sdk to update the metadata of the dataset to have "weather="snowy day" and "mood"="great"
    after that go to the UI and verify that there are 4 traces and metadata is good"""
    )
    with trace.as_context():
        trace.run_assertions(global_asserts)


def test_anthropic():
    trace = run_agent(
        """use https://github.com/anthropics/anthropic-sdk-python to generate some traces and upload them 
    to the explorer using invariant sdk. your ANTHROPIC_API_KEY is already set up with a valid key"""
    )
    with trace.as_context():
        trace.run_assertions(global_asserts)

        edit_tool_calls = trace.tool_calls(
            {"name": "str_replace_editor", "arguments.command": "create"}
        )
        file_text = edit_tool_calls[0].argument("file_text")
        assert_true(
            file_text.contains("import anthropic")
            or file_text.contains("from anthropic import")
        )

        # Extract the dataset name from a tool output and check if it's in the last screenshot
        tool_outs = trace.messages(role="tool")
        dataset_name = ""
        for tool_out in tool_outs:
            if tool_out["content"].contains("Dataset:"):
                # Extract the dataset name from regex
                dataset_name = re.search(
                    r"Dataset: (\w+)", tool_out["content"].value
                ).group(1)

        tool_out = trace.messages(role="tool")[-1]
        assert_true(tool_out["content"].ocr_contains(dataset_name))


def test_code_agent_fastapi():
    trace = run_agent(
        """use fastapi to create a count_words api that receives a string and counts 
    the number of words in it, then write a small client that tests it with a couple of different inputs"""
    )

    with trace.as_context():
        trace.run_assertions(global_asserts)

        tp = trace.tool_pairs()

        for tool_call, tool_out in tp:
            assert_false(
                tool_call["function"]["name"] == "bash"
                and tool_out.get("content", "").contains("Permission denied")
            )

        tool_calls = trace.tool_calls({"name": "str_replace_editor"})
        cnt = {}
        for tc in tool_calls:
            file_text = tc.argument("file_text").value
            cnt[file_text] = cnt.get(file_text, 0) + 1
            assert_true(
                cnt[file_text] <= 2,
                "At least 3 edits to the same file with the same text",
            )

        # edit_cmds = trace.tool_calls({"name": "str_replace_editor", "arguments.command": "create"})
        # for cmd in edit_cmds:
        #     assert_false(cmd["function"]["arguments"]["file_text"].value, "FastAPI is not installed")


def test_fibonacci():
    trace = run_agent(
        """write me a python function compute_fibonacci(n) that computes n-th fibonacci number and test it on a few inputs"""
    )

    try:
        import subprocess

        subprocess.run(["docker", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        import pytest

        pytest.skip("Docker is not installed")

    with trace.as_context():
        trace.run_assertions(global_asserts)

        tool_calls = trace.tool_calls(
            {"name": "str_replace_editor", "arguments.command": "create"}
        )
        for tc in tool_calls:
            res = tc.argument("file_text").execute_contains(
                "144", "print(compute_fibonacci(12))"
            )
            assert_true(res, "Execution output does not contain 144")
            assert_true(res, "Execution output does not contain 144")
