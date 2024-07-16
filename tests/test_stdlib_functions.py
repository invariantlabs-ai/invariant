import unittest
import tempfile
from invariant import Policy

class TestStdlibFunctions(unittest.TestCase):

    def test_simple(self):
        policy = Policy.from_string(
        """
        from invariant import Message, PolicyViolation, match
        
        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            msg.role == "assistant"
            match(r".*X.*", msg.content)
        """)
        input = []
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 0, "Expected no errors, but got: " + str(analysis_result.errors)

        input.append({"role": "assistant", "content": "Hello, Y"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 0, "Expected no errors, but got: " + str(analysis_result.errors)

        input.append({"role": "assistant", "content": "Hello, X"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 1, "Expected one error, but got: " + str(analysis_result.errors)

    def test_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with open(temp_dir + "/file1.txt", "w") as f:
                f.write("ABC")
            with open(temp_dir + "/file2.txt", "w") as f:
                f.write("DEF")
            policy = Policy.from_string(
            """
            from invariant.files import get_file_contents, File

            raise "error" if:
                (msg: Message)
                file_contents := get_file_contents(input.workspace)
                (file: File) in file_contents
                msg.content in file.content
            """)
            input = [
                {"role": "user", "content": "AB"},
            ]
            res = policy.analyze(input, workspace=temp_dir)
            self.assertEqual(len(res.errors), 1)


if __name__ == "__main__":
    unittest.main()
