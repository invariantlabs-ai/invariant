import os
import tempfile
import unittest

from invariant.analyzer import Policy
from invariant.analyzer.extras import extras_available, presidio_extra


class TestStdlibFunctions(unittest.TestCase):
    def test_simple(self):
        policy = Policy.from_string(
            """
        from invariant import Message, PolicyViolation
        
        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            msg.role == "assistant"
            match(r".*X.*", msg.content)
        """
        )
        input = []
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 0, "Expected no errors, but got: " + str(
            analysis_result.errors
        )

        input.append({"role": "assistant", "content": "Hello, Y"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 0, "Expected no errors, but got: " + str(
            analysis_result.errors
        )

        input.append({"role": "assistant", "content": "Hello, X"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 1, "Expected one error, but got: " + str(
            analysis_result.errors
        )


class TestFiles(unittest.TestCase):
    @unittest.skipUnless(os.getenv("LOCAL_POLICY") == "1", "LOCAL_POLICY is not set to 1")
    def test_sensitive_types(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with open(temp_dir + "/file1.docx", "w") as f:
                f.write("test")
            policy = Policy.from_string(
                """
            from invariant.files import get_tree_files

            raise "error" if:
                not empty(get_tree_files(input.workspace, pattern="*.docx"))
            """
            )
            res = policy.analyze([], workspace=temp_dir)
            self.assertEqual(len(res.errors), 1)

    @unittest.skipUnless(extras_available(presidio_extra), "presidio-analyzer is not installed")
    # skip unless LOCAL_POLICY is set to True
    @unittest.skipUnless(os.getenv("LOCAL_POLICY") == "1", "LOCAL_POLICY is not set to 1")
    def test_sensitive_contents(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with open(temp_dir + "/file1.txt", "w") as f:
                f.write("bob@gmail.com")
            with open(temp_dir + "/file2.txt", "w") as f:
                f.write("AB")

            policy = Policy.from_string(
                """
            from invariant.files import get_file_contents, File

            raise "error" if:
                (msg: Message)
                file_contents := get_file_contents(input.workspace)
                (file: File) in file_contents
                msg.content in file.content
            """
            )
            res = policy.analyze([{"role": "user", "content": "AB"}], workspace=temp_dir)
            self.assertEqual(len(res.errors), 1)
            res = policy.analyze([{"role": "user", "content": "GH"}], workspace=temp_dir)
            self.assertEqual(len(res.errors), 0)

            policy2 = Policy.from_string(
                """
            from invariant.files import is_sensitive_dir
            from invariant.detectors import pii

            raise "error" if:
                (msg: Message)
                is_sensitive_dir(input.workspace, [pii])
                "AB" in msg.content
            """
            )
            input = [{"role": "user", "content": "AB"}]
            res = policy2.analyze(input, workspace=temp_dir)
            self.assertEqual(len(res.errors), 1)

            with open(temp_dir + "/file1.txt", "w") as f:
                f.write("CD")
            input = [{"role": "user", "content": "AB"}]
            res = policy2.analyze(input, workspace=temp_dir)
            self.assertEqual(len(res.errors), 0)


if __name__ == "__main__":
    unittest.main()
