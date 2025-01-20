import unittest
from invariant.analyzer import parse, ast

class TestParser(unittest.TestCase):
    def test_semantic_patterns(self):
        policy = parse(
        """
        from invariant import ToolCall
        
        raise "You must not give medical advice" if:
            (call: ToolCall)
            call is tool:something_you_dont_trust({
                "key": *,
                email: 'abc'
            }, *)
        """
        )

    def test_wildcards_disallowed(self):
        policy = parse(
        """
        from invariant import ToolCall
        
        raise "You must not give medical advice" if:
            (call: ToolCall)
            # this is okay
            m := 1 * 2
            # this is not okay
            n := *
        """, verbose=False
        )

        assert len(policy.errors) == 1
        assert "You cannot use wildcards outside of semantic patterns" in str(policy.errors[0])
    
    def test_value_references_disallowed(self):
        policy = parse(
        """
        from invariant import ToolCall
        
        raise "You must not give medical advice" if:
            (call: ToolCall)
            # this is not okay
            m := <EMAIL_ADDRESS>
        """, verbose=False
        )

        assert len(policy.errors) == 1
        assert "You cannot use value references outside of semantic patterns" in str(policy.errors[0]), str(policy.errors[0])

    def test_value_references(self):
        policy = parse(
        """
        from invariant import ToolCall
        
        raise "You must not give medical advice" if:
            (call: ToolCall)
            # this is okay
            call is tool:something_you_dont_trust({
                email: <EMAIL_ADDRESS>
            }, *)
        """
        )
        assert len(policy.errors) == 0
        
        raise_policy = policy.statements[1]
        assert isinstance(raise_policy, ast.RaisePolicy)

        # get semantic pattern
        semantic_pattern = raise_policy.body[1].right
        assert isinstance(semantic_pattern, ast.SemanticPattern)

        arg = semantic_pattern.args[0]
        assert isinstance(arg, ast.ObjectLiteral)
        value_ref = arg.entries[0].value
        assert isinstance(value_ref, ast.ValueReference)
        assert value_ref.value_type == "EMAIL_ADDRESS"

        arg1 = semantic_pattern.args[1]
        assert isinstance(arg1, ast.Wildcard)


if __name__ == "__main__":
    unittest.main()