"""Tests different modes of using the library."""

import io
import subprocess
import tempfile


class WorkspaceHelper:
    """A temporary workspace for running tests."""

    def __init__(self, files):
        self.files = files
        self.workspace = tempfile.TemporaryDirectory(prefix="invariant_runner_test_")
        for filename, contents in files.items():
            with open(f"{self.workspace.name}/{filename}", "w", encoding="utf-8") as f:
                f.write(contents)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.workspace.cleanup()

    def run_pytest(self):
        """Run pytest in the workspace and return the exit code and output."""
        exit_code = 0
        buffer = None

        p = subprocess.Popen(
            ["pytest", self.workspace.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = p.communicate()

        exit_code = p.returncode
        buffer = io.StringIO()
        buffer.write(stdout)
        buffer.write(stderr)

        return exit_code, buffer.getvalue()

    def run_invariant_test(self):
        """Run invariant test in the workspace and return the exit code and output."""
        exit_code = 0
        buffer = None

        import os

        p = subprocess.Popen(
            ["invariant", "test", self.workspace.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={  # extend PYTHONPATH to include the current directory
                **os.environ,
                "PYTHONPATH": f"{os.getcwd()}{os.pathsep}{os.getenv('PYTHONPATH', '')}",
            },
        )
        stdout, stderr = p.communicate()

        exit_code = p.returncode
        buffer = io.StringIO()
        buffer.write(stdout)
        buffer.write(stderr)

        return exit_code, buffer.getvalue()


def test_pytest_no_context():
    """Test that Invariant assertions work with pytest (not tracked, but raised)."""
    with WorkspaceHelper(
        {
            "test_file1.py": """
from invariant.testing import assert_true

def test_true():
    assert_true(True)

def test_false():
    assert_true(False)
"""
        }
    ) as workspace:
        exit_code, result = workspace.run_pytest()

        assert exit_code == 1, "Exit code should be 1"

        assert (
            """\
def test_false():
>   assert_true(False)
"""
            in result
        ), "Expected failure message for test_false"

        assert (
            """\
def test_true():
>   assert_true(True)
"""
            not in result
        ), "Expected no failure message for test_true"

        assert "1 failed, 1 passed" in result, "Expected summary of 1 failed, 1 passed"


def test_pytest_no_context_regular_assertions():
    """With just pytest, regular assertions should still work and produce correct error messages"""
    with WorkspaceHelper(
        {
            "test_file1.py": """
def test_true():
    assert True

def test_false():
    assert False
"""
        }
    ) as workspace:
        exit_code, result = workspace.run_pytest()

        assert exit_code != 0, "Exit code should be 1"

        assert (
            """\
    def test_false():
>       assert False
E       assert False"""
            in result
        ), "Expected failure message for test_false"

        assert "def test_true():" not in result, "Expected no failure message for test_false"


def test_pytest_with_context():
    """With just pytest, Invariant assertions should be tracked and produce correct
    error messages (but you can't push)
    """
    with WorkspaceHelper(
        {
            "test_file1.py": """
from invariant.testing import assert_false, Trace


def test_my_trace():
    trace = Trace(
        trace=[
            {
                "role": "user",
                "content": "Could you kindly show me the list of files in tmp directory in my file system including the hidden one?",
            },
            {
                "role": "assistant",
                "content": "In the current directory, there is one file: **report.txt**. There are no hidden files listed.",
            },
        ]
    )

    with trace.as_context():
        assert_false(
            trace.messages(1)["content"].contains("current"),
            "Assistant message content should not contain the word 'current'",
        )
"""
        }
    ) as workspace:
        exit_code, result = workspace.run_pytest()

        assert exit_code != 0, "Exit code should not be 0"

        # test summary
        assert "ERROR: 1 hard assertions failed" in result, "Expected 1 hard assertion failure"

        # correct code localization
        assert ">       assert_false(" in result, "Expected code localization"

        # error message
        assert (
            "ASSERTION FAILED: Assistant message content should not contain the word 'current'"
            in result
        ), "Expected failure message for test_my_trace"

        # correctly highlighted part of the trace
        assert (
            """\
#       role:  "assistant"
        content:   "In the current directory, there is one file: **report.txt**. There are no hidden files listed."
#     },"""
            in result
        ), "Expected trace in failure message"


def test_pytest_with_context_regular_assertions():
    """With just pytest, regular assertions should still work and produce correct error messages"""
    with WorkspaceHelper(
        {
            "test_file1.py": """
from invariant.testing import assert_false, Trace

def test_my_trace():
    trace = Trace(
        trace=[
            {
                "role": "user",
                "content": "Could you kindly show me the list of files in tmp directory in my file system including the hidden one?",
            },
            {
                "role": "assistant",
                "content": "In the current directory, there is one file: **report.txt**. There are no hidden files listed.",
            },
        ]
    )

    with trace.as_context():
        assert False
"""
        }
    ) as workspace:
        exit_code, result = workspace.run_pytest()

        assert exit_code != 0, "Exit code should not be 0"

        # check that normal pytest assertions fail correctly
        assert (
            """\
        with trace.as_context():
>           assert False
E           assert False"""
            in result
        ), "Expected failure message for test_false"

        # test for summary
        assert "=== 1 failed" in result


def test_invariant_no_context():
    """With invariant test, Invariant assertions should be tracked and
    produce correct error messages (and you can push)
    """
    with WorkspaceHelper(
        {
            "test_file1.py": """
from invariant.testing import assert_true

def test_true():
    assert_true(True)

def test_false():
    assert_true(False)
"""
        }
    ) as workspace:
        exit_code, result = workspace.run_invariant_test()

        print(result)
        assert exit_code == 1, "Exit code should be 1"

        assert (
            """\
def test_false():
>   assert_true(False)
"""
            in result
        ), "Expected failure message for test_false"

        assert (
            """\
def test_true():
>   assert_true(True)
"""
            not in result
        ), "Expected no failure message for test_true"

        assert "1 failed, 1 passed" in result, "Expected summary of 1 failed, 1 passed"


def test_invariant_no_context_regular_assertions():
    """With invariant test, regular assertions should still work and produce correct error messages"""
    with WorkspaceHelper(
        {
            "test_file1.py": """
def test_true():
    assert True

def test_false():
    assert False
"""
        }
    ) as workspace:
        exit_code, result = workspace.run_invariant_test()

        assert exit_code != 0, "Exit code should be 1"

        assert (
            """\
    def test_false():
>       assert False
E       assert False"""
            in result
        ), "Expected failure message for test_false"

        assert "def test_true():" not in result, "Expected no failure message for test_false"


def test_invariant_with_context():
    """With invariant test, Invariant assertions should be tracked and produce correct
    error messages. Also, there should be the Invariant summary of your tests (and you can push)
    """
    with WorkspaceHelper(
        {
            "test_file1.py": """
from invariant.testing import assert_false, Trace


def test_my_trace():
    trace = Trace(
        trace=[
            {
                "role": "user",
                "content": "Could you kindly show me the list of files in tmp directory in my file system including the hidden one?",
            },
            {
                "role": "assistant",
                "content": "In the current directory, there is one file: **report.txt**. There are no hidden files listed.",
            },
        ]
    )

    with trace.as_context():
        assert_false(
            trace.messages(1)["content"].contains("current"),
            "Assistant message content should not contain the word 'current'",
        )
"""
        }
    ) as workspace:
        exit_code, result = workspace.run_invariant_test()

        assert exit_code != 0, "Exit code should not be 0"

        # test summary
        assert "ERROR: 1 hard assertions failed" in result, "Expected 1 hard assertion failure"

        # correct code localization
        assert ">       assert_false(" in result, "Expected code localization"

        # error message
        assert (
            "ASSERTION FAILED: Assistant message content should not contain the word 'current'"
            in result
        ), "Expected failure message for test_my_trace"

        # correctly highlighted part of the trace
        assert (
            """\
#       role:  "assistant"
        content:   "In the current directory, there is one file: **report.txt**. There are no hidden files listed."
#     },"""
            in result
        ), "Expected trace in failure message"


def test_invariant_with_context_regular_assertions():
    """With invariant test, regular assertions should still work and produce correct error
    messages (they show up in summary, but error messages are not localized in the trace)
    """
    with WorkspaceHelper(
        {
            "test_file1.py": """
from invariant.testing import assert_false, Trace

def test_my_trace():
    trace = Trace(
        trace=[
            {
                "role": "user",
                "content": "Could you kindly show me the list of files in tmp directory in my file system including the hidden one?",
            },
            {
                "role": "assistant",
                "content": "In the current directory, there is one file: **report.txt**. There are no hidden files listed.",
            },
        ]
    )

    with trace.as_context():
        assert False, "this will always fail"
"""
        }
    ) as workspace:
        exit_code, result = workspace.run_invariant_test()

        assert exit_code != 0, "Exit code should not be 0"

        assert "Invariant Test summary" in result, (
            "'Invariant test summary' should be included in output when running with 'invariant test'"
        )

        # check that normal pytest assertions fail correctly
        assert (
            """\
>           assert False, "this will always fail"
E           AssertionError: this will always fail
E           assert False"""
            in result
        ), "Expected failure message for test_false"

        # test for summary
        assert "=== 1 failed" in result
