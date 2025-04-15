import unittest

from invariant.analyzer import Policy
from invariant.analyzer.extras import extras_available, presidio_extra, transformers_extra
from invariant.analyzer.monitor import Monitor
from invariant.analyzer.traces import assistant, system, tool, tool_call, user


class TestFlow(unittest.TestCase):
    def test_simple(self):
        policy = Policy.from_string(
            """
        raise PolicyViolation("you must not call something_else after something", call=call, call2=call2) if:
            (call: ToolCall) -> (call2: ToolCall)
            call is tool:something({x: 2})
            call2 is tool:something_else({x: 10})
        """
        )

        trace = [
            system("You are a helpful assistant."),
            user("What is the result of something(2)?"),
            assistant(None, tool_call("1", "something", {"x": 2})),
            tool("1", 2001),
            assistant(None, tool_call("2", "something_else", {"x": 10})),
            tool("2", 2001),
        ]
        result = policy.analyze(trace)
        assert len(result.errors) == 1

    def test_inverted(self):
        policy = Policy.from_string(
            """
        raise "you must not call something_else after something" if:
            (call: ToolCall) -> (call2: ToolCall)
            call2 is tool:something({x: 2})
            call is tool:something_else({x: 10})
        """
        )

        trace = [
            system("You are a helpful assistant."),
            user("What is the result of something(2)?"),
            assistant(None, tool_call("1", "something", {"x": 2})),
            tool("1", 2001),
            assistant(None, tool_call("2", "something_else", {"x": 10})),
            tool("2", 2001),
        ]
        result = policy.analyze(trace)
        assert len(result.errors) == 0

    def test_with_intermediate_step(self):
        policy = Policy.from_string(
            """
        raise "you must not call something_else after something" if:
            (call: ToolCall) -> (call2: ToolCall)
            call is tool:something({x: 2})
            call2 is tool:something
        """
        )

        trace = [
            system("You are a helpful assistant."),
            user("What is the result of something(2)?"),
            assistant(None, tool_call("1", "something", {"x": 2})),
            tool("1", 2001),
            assistant(None, tool_call("2", "something_else", {"x": 10})),
            tool("2", 2001),
            assistant(None, tool_call("3", "something", {"x": 2})),
            tool("3", 2001),
        ]
        result = policy.analyze(trace)
        assert len(result.errors) == 1

    def test_with_intermediate_step_nonmatching_tool(self):
        policy = Policy.from_string(
            """
        raise "you must not call something_else after something" if:
            (call: ToolCall) -> (call2: ToolCall)
            call is tool:something({x: 2})
            call2 is tool:something_else
        """
        )

        trace = [
            system("You are a helpful assistant."),
            user("What is the result of something(2)?"),
            assistant(None, tool_call("1", "something", {"x": 2})),
            tool("1", 2001),
            assistant(None, tool_call("2", "something", {"x": 10})),
            tool("2", 2001),
            assistant(None, tool_call("3", "something", {"x": 2})),
            tool("3", 2001),
        ]
        result = policy.analyze(trace)
        assert len(result.errors) == 0

    def test_user_message_to_tool(self):
        policy = Policy.from_string(
            """
        raise "you must not call something_else after something" if:
            (message: Message) -> (call: ToolCall)
            message.role == "user"
            "abc" in message.content
            call is tool:something({x: 2})
        """
        )

        trace = [
            system("You are a helpful assistant."),
            user("What is the result of something(2)? abc"),
            assistant(None, tool_call("1", "something", {"x": 2})),
            tool("1", 2001),
            assistant(None, tool_call("2", "something_else", {"x": 10})),
            tool("2", 2001),
        ]
        result = policy.analyze(trace)
        assert len(result.errors) == 1

    def test_user_message_to_tool_wo_abc(self):
        policy = Policy.from_string(
            """
        raise "you must not call something_else after something" if:
            (message: Message) -> (call: ToolCall)
            message.role == "user"
            "abc" in message.content
            call is tool:something({x: 2})
        """
        )

        trace = [
            system("You are a helpful assistant."),
            user("What is the result of something(2)?"),
            assistant(None, tool_call("1", "something", {"x": 2})),
            tool("1", 2001),
            assistant(None, tool_call("2", "something_else", {"x": 10})),
            tool("2", 2001),
        ]
        result = policy.analyze(trace)
        assert len(result.errors) == 0

    def test_user_message_to_answer(self):
        policy = Policy.from_string(
            """
        raise "you must not call something_else after something" if:
            (message: Message) -> (message2: Message)
            message.role == "user"
            "abc" in message.content
            message2.role == "assistant"
            "def" in message2.content
        """
        )

        trace = [
            system("You are a helpful assistant."),
            user("What is the result of something(2)? abc"),
            assistant("The result is 2001. def"),
        ]
        result = policy.analyze(trace)
        assert len(result.errors) == 1

    @unittest.skipUnless(
        extras_available(presidio_extra, transformers_extra),
        "At least one of presidio-analyzer, transformers, and torch are not installed",
    )
    def test_moderated_to_tool(self):
        policy = Policy.from_string(
            """
        from invariant.detectors import moderated, pii

        raise PolicyViolation("you must not call something_else after something", call=call, message=message) if:
            (message: Message) -> (call: ToolCall)
            moderated(message.content, cat_thresholds={"self-harm": 0.4})
            call is tool:something
        """
        )

        trace = [
            system("You are a helpful assistant."),
            user("I hate this shit"),
            assistant(None, tool_call("1", "something", {"x": 20})),
        ]
        result = policy.analyze(trace)
        assert len(result.errors) >= 1

    def test_assistant_to_tool(self):
        policy = Policy.from_string(
            """
        raise PolicyViolation("error", message, call) if:
            (message: Message) -> (call: ToolCall)
            "Hey" in message.content
        """
        )
        trace = [assistant("Hey", tool_call("1", "something", {"x": 2}))]
        res = policy.analyze(trace)
        self.assertEqual(len(res.errors), 1)

    def test_separate_path(self):
        policy = Policy.from_string(
            """
        raise PolicyViolation("error", message, call) if:
            (message: Message)
            (call: ToolCall)
            message -> call
            call.function.arguments["x"] == len(message.role) - 2
        """
        )
        trace = [
            user("What is the result of something(2)?"),
            assistant(None, tool_call("1", "something", {"x": 2})),
        ]
        res = policy.analyze(trace)
        self.assertEqual(len(res.errors), 1)

    def test_multipath(self):
        policy = Policy.from_string(
            """
        raise PolicyViolation("error") if:
            (m1: Message)
            (m2: Message)
            (call: ToolCall)
            m1 -> call
            m1 -> m2
            m1.role == "user"
            m2.role == "user"
        """
        )
        trace = [
            user("Hi how are you?"),
            user("What is the result of something(2)?"),
            assistant(None, tool_call("1", "something", {"x": 2})),
        ]
        res = policy.analyze(trace)
        self.assertEqual(len(res.errors), 1)

    def test_stateful_vs_stateless(self):
        policy_str = """
        raise PolicyViolation("error") if:
            (m: Message)
            "Hi" in m.content
        """
        trace = [
            user("Hi how are you?"),
        ]
        # stateful analysis
        policy = Monitor.from_string(policy_str)
        self.assertEqual(len(policy.analyze(trace).errors), 1)
        self.assertEqual(len(policy.analyze(trace).errors), 0)
        # stateless analysis
        policy = Policy.from_string(policy_str)
        self.assertEqual(len(policy.analyze(trace).errors), 1)
        self.assertEqual(len(policy.analyze(trace).errors), 1)


class TestFlowImmediatePredecessor(unittest.TestCase):
    def test_simple(self):
        policy = Policy.from_string(
            """
            raise PolicyViolation("error") if:
                (msg1: Message) ~> (msg2: Message)
                msg1.role == "user"
                msg2.role == "assistant"
            """
        )

        trace = [
            user("Hi how are you?"),
            assistant("I'm fine, thank you!"),
        ]
        res = policy.analyze(trace)
        self.assertEqual(len(res.errors), 1)

        trace = [
            assistant("How can I help you?"),
            user("Dunno bud"),
        ]
        res = policy.analyze(trace)
        self.assertEqual(len(res.errors), 0)

        trace = [
            user("Hi how are you?"),
            assistant("I'm fine, thank you!"),
            user("Hi how are you now?"),
            assistant("Still good, thanks!"),
        ]
        res = policy.analyze(trace)
        # Only produces 2 errors. "->" would produce 3.
        self.assertEqual(len(res.errors), 2)

        trace = [
            user("Hi how are you?"),
            user("Hi how are you now?"),
            assistant("Still good, thanks!"),
            user("Hi how are you now?"),
        ]

        res = policy.analyze(trace)
        self.assertEqual(len(res.errors), 1)

    def test_tool_parent_is_calling_message(self):
        policy = Policy.from_string(
            """
            raise PolicyViolation("error") if:
                (msg: Message) ~> (call: ToolCall)
                msg.role == "user"
            """
        )

        trace = [
            user("Hi how are you?"),
            assistant(
                None,
                [
                    tool_call("1", "something", {"x": 2}),
                    tool_call("2", "something_else", {"x": 10}),
                ],
            ),
        ]
        res = policy.analyze(trace)
        # No errors should be found, as the predecessor
        # of the tool call is the assistant message
        # it is embedded in or previous tool calls
        self.assertEqual(len(res.errors), 0)

        policy = Policy.from_string(
            """
            raise PolicyViolation("error") if:
                (msg: ToolCall) ~> (call: ToolCall)
            """
        )

        res = policy.analyze(trace)
        # We should find exactly one error as the
        # predecessor of the tool call is the
        # assistant message it is embedded in or previous tool calls
        self.assertEqual(len(res.errors), 1)

    def test_order(self):
        policy = Policy.from_string(
            """
            raise PolicyViolation("error") if:
                (msg1: Message) ~> (msg2: Message)
                msg1.role == "user"
                msg2.role == "assistant"
            """
        )

        trace = [
            assistant("How can I help you??"),
            user("What is the result of something(2)?"),
        ]
        res = policy.analyze(trace)
        self.assertEqual(len(res.errors), 0)


if __name__ == "__main__":
    unittest.main()
