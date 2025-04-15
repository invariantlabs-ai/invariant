import unittest

from invariant.analyzer import Policy, PolicyLoadingError, parse


class TestParser(unittest.TestCase):
    def test_failed_import(self):
        policy_root = parse("""
        from invariant.detectors import pii, semgrep

        raise PolicyViolation("found unsafe code") if:
            (call1: ToolCall) -> (call2: ToolCall)
            call1.function.name == "edit"
            (issue: CodeIssue) in semgrep(call1.function.arguments["code"])
            call2.function.name == "python"
        """)
        assert len(policy_root.errors) == 1, "Expected 1 error, got " + str(len(policy_root.errors))

    def test_policy_load_fails(self):
        # We should not silently continue when there are policy errors
        with self.assertRaises(PolicyLoadingError):
            Policy.from_string("""
            from invariant.detectors import pii, semgrep

            raise PolicyViolation("found unsafe code") if:
                (call1: ToolCall) -> (call2: ToolCall)
                call1.function.name == "edit"
                (issue: CodeIssue) in semgrep(call1.function.arguments["code"])
                call2.function.name == "python"
            """).preload()

    def test_error_localization_declaration(self):
        try:
            p = Policy.from_string(
                """
            from invariant.detectors import pii, semgrep

            abc :=
                12 + CodeIssue

            raise CodeIssue("found unsafe code") if:
                    (call1: ToolCall) -> (call2: ToolCall)
                    call1.function.name == "edit" + CodeIssue
                    (issue: CodeIssue) in semgrep(call1.function.arguments["code"])
                    call2.function.name == "python"
            """
            )
            p.preload()
            assert False, "Expected a PolicyLoadingError, but got none."
        except PolicyLoadingError as e:
            msg = str(e)

        assert contains_successive_block(["12 + CodeIssue", "     ^"], msg), (
            "Did not find the correct error localization at '12 + |C|odeIssue' in " + msg
        )

        assert not contains_successive_block(["12 + CodeIssue", "       ^"], msg), (
            "Found an incorrect error localization at '12 + C|o|deIssue' in " + msg
        )

    def test_error_localization_indented(self):
        try:
            p = Policy.from_string(
                """
            from invariant.detectors import pii, semgrep

            abc :=
                12 + CodeIssue

            raise CodeIssue("found unsafe code") if:
                    (call1: ToolCall) -> (call2: ToolCall)
                    call1.function.name == "edit" + CodeIssue
                    (issue: CodeIssue) in semgrep(call1.function.arguments["code"])
                    call2.function.name == "python"
            """
            )
            p.preload()
            assert False, "Expected a PolicyLoadingError, but got none."
        except PolicyLoadingError as e:
            msg = str(e)

        assert contains_successive_block(["(issue: CodeIssue)", " ^"], msg), (
            "Did not find the correct error localization at '(|i|ssue: CodeIssue) in' in " + msg
        )

        # negative case

        assert not contains_successive_block(["(issue: CodeIssue)", "      ^"], msg), (
            "Found an incorrect error localization at '(issue: |C|odeIssue) in' in " + msg
        )

    def test_error_localization_in_expr(self):
        try:
            p = Policy.from_string(
                """
            from invariant.detectors import pii, semgrep

            abc :=
                12 + CodeIssue

            raise CodeIssue("found unsafe code") if:
                    (call1: ToolCall) -> (call2: ToolCall)
                    call1.function.name == "edit" + CodeIssue
                    (issue: CodeIssue) in semgrep(call1.function.arguments["code"])
                    call2.function.name == "python"
            """
            )
            p.preload()
            assert False, "Expected a PolicyLoadingError, but got none."
        except PolicyLoadingError as e:
            msg = str(e)

        assert contains_successive_block(['raise CodeIssue("found ', "      ^"], msg), (
            "Did not find the correct error localization at 'raise |C|odeIssue(\"found' in " + msg
        )

    def test_localization_single_indent(self):
        try:
            p = Policy.from_string(
                """
            from invariant.detectors import pii, semgrep

            abc :=
                12 + CodeIssue

            raise CodeIssue("found unsafe code") if:
                (call1: ToolCall) -> (call2: ToolCall)
                call1.function.name == "edit" + CodeIssue
                  (issue: CodeIssue) in semgrep(call1.function.arguments["code"])
                call2.function.name == "python"
            """
            )
            p.preload()
            assert False, "Expected a PolicyLoadingError, but got none."
        except PolicyLoadingError as e:
            msg = str(e)

        assert contains_successive_block(['raise CodeIssue("found ', "      ^"], msg), (
            "Did not find the correct error localization at 'raise |C|odeIssue(\"found' in " + msg
        )

        assert contains_successive_block(
            ['call1.function.name == "edit" + CodeIssue', "                                ^"], msg
        ), (
            "Did not find the correct error localization at 'call1.function.name == \"edit|\"' in "
            + msg
        )

        # same but for the 3rd rule body line
        assert contains_successive_block(["  (issue: CodeIssue) in semgrep", "   ^"], msg), (
            "Did not find the correct error localization at 'call2.function.name == \"|python\"' in "
            + msg
        )


def contains_successive_block(block_lines, contents):
    content_lines = contents.split("\n")
    for i in range(len(content_lines)):
        current_line = content_lines[i]
        first_block_line = block_lines[0]
        # find index of first block line in current line
        index = current_line.find(first_block_line)
        if index == -1:
            continue
        is_match = True
        # check if the rest of the block lines are present in the following lines
        for j in range(i + 1, i + len(block_lines)):
            next_line = content_lines[j][index:]
            next_block_line = block_lines[j - i]
            if not next_line.startswith(next_block_line):
                is_match = False
        if is_match:
            return True
    return False


if __name__ == "__main__":
    unittest.main()
