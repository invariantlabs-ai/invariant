import invariant.testing.functional as F
import urllib3
from invariant.testing import Trace, assert_false, assert_true, expect_true
from invariant.testing.custom_types.trace_factory import TraceFactory

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def does_not_click_on_firefox_menu(trace: Trace):
    """Agent should not click on the firefox hamburger menu on the right."""
    for tool_out in trace.tool_outputs(data_type="image"):
        assert_false(tool_out["content"].ocr_contains_all("New tab", "New window"))


def does_not_make_python_error(trace: Trace):
    """Agent should not produce code that results in ModuleNotFoundError."""
    for tool_out in trace.messages(role="tool"):
        assert_false(tool_out["content"].contains("ModuleNotFoundError"))


def does_not_make_file_edit_errors(trace: Trace):
    """Agent should not make file edit errors."""
    for tool_out in trace.tool_outputs():
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

        expect_true(
            max(
                F.frequency(
                    F.filter(
                        lambda x: "http" in x.value,
                        F.map(
                            lambda tc: tc.argument("text"),
                            trace.tool_calls(
                                {"arguments.action": "type", "name": "computer"}
                            ),
                        ),
                    )
                ).values()
            )
            <= 1
        )
        # assert that the last screenshot contains the text "annotated" and text "nice nice"
        last_screenshot = trace.messages(role="tool")[-1]["content"]
        assert_true(last_screenshot.ocr_contains_all(["annotated", "nice nice"]))


def test_upload_traces():
    trace = run_agent("""upload a dataset of 100 traces using a browser""")
    with trace.as_context():
        trace.run_assertions(global_asserts)
        assert_false(
            F.any(
                F.map(
                    lambda x: x.argument("command").contains_all("100", "EOF", ".py"),
                    trace.tool_calls(name="bash"),
                )
            )
        )


def test_food_dataset():
    trace = run_agent(
        """create an empty dataset "chats-about-food", then use sdk to push 4 different traces 
    to it and then finally use sdk to update the metadata of the dataset to have "weather="snowy day" and "mood"="great"
    after that go to the UI and verify that there are 4 traces and metadata is good"""
    )
    with trace.as_context():
        assert_true(
            F.any(
                F.map(
                    lambda x: x.argument("file_text").contains(
                        "create_request_and_push_trace"
                    ),
                    trace.tool_calls(name="str_replace_editor"),
                )
            )
        )


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
        assert_true(file_text.contains_any("import anthropic", "from anthropic import"))

        # Extract the dataset name from a tool output and check if it's in the last screenshot
        tool_outs = trace.messages(role="tool")
        dataset_name = F.match(
            r"Dataset: (\w+)", F.map(lambda x: x["content"], tool_outs), 1
        )[0]
        tool_out = trace.messages(role="tool")[-1]
        assert_true(tool_out["content"].ocr_contains(dataset_name))


def test_code_agent_fastapi():
    trace = run_agent(
        """use fastapi to create a count_words api that receives a string and counts 
    the number of words in it, then write a small client that tests it with a couple of different inputs"""
    )

    with trace.as_context():
        trace.run_assertions(global_asserts)

        for tool_call, tool_out in trace.tool_pairs():
            assert_false(
                tool_call["function"]["name"] == "bash"
                and tool_out.get("content", "").contains("Permission denied")
            )

        tool_calls = trace.tool_calls({"name": "str_replace_editor"})

        max_freq = max(
            F.frequency(F.map(lambda x: x.argument("file_text"), tool_calls)).values()
        )
        assert_true(
            max_freq <= 2, "At least 3 edits to the same file with the same text"
        )


def test_fibonacci():
    trace = run_agent(
        """write me a python function compute_fibonacci(n) that computes n-th fibonacci number and test it on a few inputs"""
    )
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
