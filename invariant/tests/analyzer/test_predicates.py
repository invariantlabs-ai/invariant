import unittest

from invariant.analyzer import Monitor, Policy
from invariant.analyzer.traces import chunked


class TestConstants(unittest.TestCase):
    def test_simple(self):
        policy = Monitor.from_string(
            """
        from invariant import Message, PolicyViolation
        
        invalid_pattern(m: Message) := 
            match(".*X.*", m.content)
            m.role == "assistant"

        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            invalid_pattern(msg)
        """
        )

        input = []

        input.append({"type": "Message", "role": "assistant", "content": "Hello, X"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 1, "Expected one error, but got: " + str(
            analysis_result.errors
        )
        assert "Cannot send assistant message" in str(analysis_result.errors[0]), (
            "Expected to find 'Cannot send assistant message' in error message, but got: " + str(e)
        )

        input.append({"type": "Message", "role": "assistant", "content": "Hello, Y"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 0, "Expected no errors, but got: " + str(
            analysis_result.errors
        )

        # user msg with X
        input.append({"type": "Message", "role": "user", "content": "Hello, X"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 0, "Expected no errors, but got: " + str(
            analysis_result.errors
        )

    def test_simple_chunked(self):
        policy = Monitor.from_string(
            """
        from invariant import Message, PolicyViolation

        invalid_pattern(m: Message) := 
            m.role == "assistant"
            (chunk: str) in text(m.content)
            match(".*X.*", chunk)

        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            invalid_pattern(msg)
        """
        )

        input = []

        input.append(chunked({"type": "Message", "role": "assistant", "content": "Hello X"}))
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 1, "Expected one error, but got: " + str(
            analysis_result.errors
        )
        assert "Cannot send assistant message" in str(analysis_result.errors[0]), (
            "Expected to find 'Cannot send assistant message' in error message, but got: "
            + str(analysis_result.errors[0])
        )

        input.append(chunked({"type": "Message", "role": "assistant", "content": "Hello Y"}))
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 0, "Expected no errors, but got: " + str(
            analysis_result.errors
        )

    def test_two_level(self):
        policy = Monitor.from_string(
            """
        from invariant import Message, PolicyViolation

        invalid_role(m: Message) :=
            m.role == "assistant"

        invalid_pattern(m: Message) :=
            match(".*X.*", m.content)
            invalid_role(m)

        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            invalid_pattern(msg)
        """
        )

        input = []

        input.append({"type": "Message", "role": "assistant", "content": "Hello, X"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 1, "Expected one error, but got: " + str(
            analysis_result.errors
        )
        assert "Cannot send assistant message" in str(analysis_result.errors[0]), (
            "Expected to find 'Cannot send assistant message' in error message, but got: " + str(e)
        )

        input.append({"type": "Message", "role": "assistant", "content": "Hello, Y"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 0, "Expected no errors, but got: " + str(
            analysis_result.errors
        )

        # user msg with X
        input.append({"type": "Message", "role": "user", "content": "Hello, X"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 0, "Expected no errors, but got: " + str(
            analysis_result.errors
        )

    def test_call_two_level(self):
        policy = Monitor.from_string(
            """
        from invariant import Message, PolicyViolation

        invalid_role(m: Message) :=
            m.role == "assistant"

        invalid_pattern(m: Message) :=
            match(".*X.*", m.content)

        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            invalid_pattern(msg)
            invalid_role(msg)
        """
        )

        input = []

        input.append({"type": "Message", "role": "assistant", "content": "Hello, X"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 1, "Expected one error, but got: " + str(
            analysis_result.errors
        )
        assert "Cannot send assistant message" in str(analysis_result.errors[0]), (
            "Expected to find 'Cannot send assistant message' in error message, but got: " + str(e)
        )

        input.append({"type": "Message", "role": "assistant", "content": "Hello, Y"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 0, "Expected no additional errors, but got: " + str(
            analysis_result.errors
        )

        # user msg with X
        input.append({"type": "Message", "role": "user", "content": "Hello, X"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 0, "Expected no additional errors, but got: " + str(
            analysis_result.errors
        )

    def test_predicate_and_constant(self):
        policy = Monitor.from_string(
            """
        from invariant import Message, PolicyViolation

        invalid_role(m: Message) :=
            m.role == "assistant"

        INVALID_PATTERN := "X"

        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            INVALID_PATTERN in msg.content
            invalid_role(msg)
        """
        )

        input = []

        input.append({"type": "Message", "role": "assistant", "content": "Hello, X"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 1, "Expected one error, but got: " + str(
            analysis_result.errors
        )
        assert "Cannot send assistant message" in str(analysis_result.errors[0]), (
            "Expected to find 'Cannot send assistant message' in error message, but got: " + str(e)
        )

        input.append({"type": "Message", "role": "assistant", "content": "Hello, Y"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 0, "Expected no errors, but got: " + str(
            analysis_result.errors
        )

        # user msg with X
        input.append({"type": "Message", "role": "user", "content": "Hello, X"})
        analysis_result = policy.analyze(input)
        assert len(analysis_result.errors) == 0, "Expected no errors, but got: " + str(
            analysis_result.errors
        )

    def test_string_contain(self):
        policy = Policy.from_string(
            """
        raise PolicyViolation("Content too long!", msg) if:
            (msg: Message)
            max(len("abc"), len(msg.content)) > 5
        """
        )
        self.assertEqual(
            len(policy.analyze([{"role": "assistant", "content": "Hi there!"}]).errors), 1
        )
        self.assertEqual(len(policy.analyze([{"role": "assistant", "content": "Hi"}]).errors), 0)

    def test_variables_and_predicates(self):
        policy = Policy.from_string(
            """
        GLOBAL_VAR := "abc"

        invalid_msg(m: Message) :=
            local_var := "def"
            GLOBAL_VAR in m.content
            local_var in m.content

        raise PolicyViolation("Invalid message", msg) if:
            (msg: Message)
            invalid_msg(msg)
        """
        )
        self.assertEqual(
            len(policy.analyze([{"role": "assistant", "content": "abcdef"}]).errors), 1
        )
        self.assertEqual(len(policy.analyze([{"role": "assistant", "content": "abc"}]).errors), 0)
        self.assertEqual(len(policy.analyze([{"role": "assistant", "content": "def"}]).errors), 0)

    def test_variables_and_predicates_disjunction(self):
        policy = Policy.from_string(
            """
        GLOBAL_VAR := "abc"

        invalid_msg(m: Message) :=
            local_var := "def"
            GLOBAL_VAR in m.content or local_var in m.content

        raise PolicyViolation("Invalid message", msg) if:
            (msg: Message)
            invalid_msg(msg)
        """
        )
        self.assertEqual(
            len(policy.analyze([{"role": "assistant", "content": "abcdef"}]).errors), 1
        )
        self.assertEqual(len(policy.analyze([{"role": "assistant", "content": "abc"}]).errors), 1)
        self.assertEqual(len(policy.analyze([{"role": "assistant", "content": "def"}]).errors), 1)
        self.assertEqual(len(policy.analyze([{"role": "assistant", "content": "ab"}]).errors), 0)


if __name__ == "__main__":
    unittest.main()
