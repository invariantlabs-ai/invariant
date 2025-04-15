import unittest

from invariant.analyzer import ast, parse


class TestParser(unittest.TestCase):
    def test_import(self):
        policy = parse("""
        import invariant
        """)
        assert len(policy.statements) == 1
        import_ = policy.statements[0]
        assert type(import_) is ast.Import
        assert import_.module == "invariant"

    def test_import_from(self):
        policy = parse("""
        from invariant import invariant as inv
        """)
        assert len(policy.statements) == 1
        import_ = policy.statements[0]
        assert type(import_) is ast.Import
        assert import_.module == "invariant"
        assert len(import_.import_specifiers) == 1
        assert import_.import_specifiers[0].name == "invariant"
        assert import_.import_specifiers[0].alias == "inv"

    def test_raise_str(self):
        policy = parse("""
        from invariant import ToolCall

        raise "You must not trust this tool" if:
            (call: ToolCall)
            call is tool:something_you_dont_trust
        """)
        assert len(policy.statements) == 2
        raise_ = policy.statements[1]
        assert type(raise_) is ast.RaisePolicy

        assert len(raise_.body) == 2
        assert type(raise_.body[0]) is ast.TypedIdentifier
        assert raise_.body[0].name == "call"
        assert raise_.body[0].type_ref == "ToolCall"

        assert type(raise_.body[1]) is ast.BinaryExpr
        assert raise_.body[1].op == "is"
        assert type(raise_.body[1].left) is ast.Identifier
        assert raise_.body[1].left.name == "call"
        assert type(raise_.body[1].right) is ast.ToolReference
        assert raise_.body[1].right.name == "something_you_dont_trust"

    def test_function(self):
        policy = parse("""
        from invariant import ToolCall

        def FilterPII():
            raise "call with no mapping" if:
                (call: ToolCall)
                call is tool:something_you_dont_trust
                call.state.mapping is None

            raise "call with mapping" if:
                (call: ToolCall)
                call is tool:something_you_dont_trust
                call.state.mapping is not None
        """)
        assert len(policy.statements) == 2
        function = policy.statements[1]
        assert type(function) is ast.FunctionDefinition
        assert function.name.name.name == "FilterPII"
        assert len(function.params) == 0
        assert len(function.body) == 2

        raise_1 = function.body[0]
        assert type(raise_1) is ast.RaisePolicy

        raise_2 = function.body[1]
        assert type(raise_2) is ast.RaisePolicy

    def test_raise(self):
        policy = parse("""
        from invariant import Message
        from invariant.content import is_medical

        raise "You must not give medical advice" if:
            (message: Message)
            is_medical(message.content)
            message.role == "assistant"
        """)
        assert len(policy.statements) == 3
        raise_ = policy.statements[2]
        assert type(raise_) is ast.RaisePolicy
        assert type(raise_.exception_or_constructor) is ast.StringLiteral
        assert raise_.exception_or_constructor.value == "You must not give medical advice"

    def test_variable(self):
        policy = parse("""
        NON_COMPANY_DOMAIN := r"^[^@]*@(?!acme\\.com)"
        """)
        assert len(policy.statements) == 1
        variable = policy.statements[0]
        assert type(variable) is ast.Declaration
        assert variable.name.name == "NON_COMPANY_DOMAIN"
        assert type(variable.value[0]) is ast.StringLiteral

    def test_rule(self):
        policy = parse("""
        from invariant.re import match

        credit_card_number(s: str) :=
            match(r"\\d{4}-\\d{4}-\\d{4}-\\d{4}", s) or
            match(r"\\d{16}", s)
        """)
        assert len(policy.statements) == 2
        rule = policy.statements[1]
        assert type(rule) is ast.Declaration
        assert rule.name.name.name == "credit_card_number"

        assert len(rule.value) == 1
        assert type(rule.value[0]) is ast.BinaryExpr
        assert rule.value[0].op == "or"

    def test_raise2(self):
        policy = parse("""
        from invariant import Message
        from invariant.codegen import PythonProgram, FunctionCall, Keyword

        def PythonNoEval():
            raise msg if:
                (message: Message)
                program := PythonProgram(message.content)
                (call: FunctionCall) in program
                call.target.name == "eval"
                
                msg := f"Code contains eval statement at line {call.line_number}. You must not use eval."
        """)
        assert len(policy.statements) == 3
        function = policy.statements[2]
        assert type(function) is ast.FunctionDefinition
        assert len(function.body) == 1
        raise_ = function.body[0]
        assert type(raise_) is ast.RaisePolicy

    def test_float_value(self):
        policy = parse("""
        THRESHOLD := 0.5
        """)
        assert len(policy.statements) == 1
        variable = policy.statements[0]
        assert type(variable) is ast.Declaration
        assert variable.name.name == "THRESHOLD"
        assert type(variable.value[0]) is ast.NumberLiteral
        assert variable.value[0].value == 0.5, variable.value[0].value

    def test_three_messages(self):
        policy = parse(
            """
        from invariant import Message, PolicyViolation, match

        raise PolicyViolation("Cannot send assistant message:", msg) if:
            (msg: Message)
            (msg2: Message)
            (msg3: Message)
            msg.role == "assistant"
            match(r".*X.*", msg.content)
            msg2.role == "assistant"
            msg2.role == msg3.role
        """
        )
        self.assertIsInstance(policy.statements[1].body[0], ast.TypedIdentifier)
        self.assertIsInstance(policy.statements[1].body[1], ast.TypedIdentifier)
        self.assertIsInstance(policy.statements[1].body[2], ast.TypedIdentifier)
        self.assertIsInstance(policy.statements[1].body[3], ast.BinaryExpr)
        self.assertIsInstance(policy.statements[1].body[4], ast.FunctionCall)
        self.assertIsInstance(policy.statements[1].body[5], ast.BinaryExpr)
        self.assertIsInstance(policy.statements[1].body[6], ast.BinaryExpr)

    def test_tool_reference(self):
        policy = parse(
            """
        from invariant import ToolCall, PolicyViolation

        raise PolicyViolation("Cannot send assistant message:", call) if:
            (call: ToolCall)
            call is tool:assistant
            call is tool:something({
                "x": 2.5
            })
        """
        )
        self.assertIsInstance(policy.statements[1].body[1], ast.BinaryExpr)
        self.assertIsInstance(policy.statements[1].body[1].right, ast.ToolReference)
        self.assertEqual(policy.statements[1].body[1].right.name, "assistant")

        self.assertIsInstance(policy.statements[1].body[2], ast.BinaryExpr)
        self.assertIsInstance(policy.statements[1].body[2].right, ast.SemanticPattern)
        self.assertEqual(policy.statements[1].body[2].right.tool_ref.name, "something")
        self.assertEqual(policy.statements[1].body[2].right.args[0].entries[0].key, "x")
        self.assertIsInstance(
            policy.statements[1].body[2].right.args[0].entries[0].value, ast.NumberLiteral
        )
        self.assertEqual(policy.statements[1].body[2].right.args[0].entries[0].value.value, 2.5)

    def test_string_ops(self):
        policy_str = """
        second_more_words(m1: Message, m2: Message) :=
            len(m1.content.split(" ")) > {placeholder}

        raise PolicyViolation("Content too long!", m1, m2) if:
            (m1: Message)
            (m2: Message)
            second_more_words(m1, m2)
        """
        policy = parse(policy_str.format(placeholder="5"))
        self.assertIsInstance(policy.statements[0].value[0], ast.BinaryExpr)

        policy2 = parse(policy_str.format(placeholder='len(m2.content.split(" "))'))
        self.assertIsInstance(policy2.statements[0].value[0], ast.BinaryExpr)

    def test_strings(self):
        policy = parse("""
        a := "hello"
        b := "world\\""
        c := "world'"
        d := "world\\"d\\"e\\""
        # single quote
        e := 'world'
        f := 'world\\''
        g := 'world"'
        h := 'world\\'d\\'e\\''
        """)

        assert policy.statements[0].value[0].value == "hello"
        assert policy.statements[1].value[0].value == 'world"', (
            'Expected world" but got ' + policy.statements[1].value[0].value
        )
        assert policy.statements[2].value[0].value == "world'", (
            "Expected world' but got " + policy.statements[2].value[0].value
        )
        assert policy.statements[3].value[0].value == 'world"d"e"', (
            'Expected world"d"e" but got ' + policy.statements[3].value[0].value
        )
        assert policy.statements[4].value[0].value == "world", (
            "Expected world but got " + policy.statements[4].value[0].value
        )
        assert policy.statements[5].value[0].value == "world'", (
            "Expected world' but got " + policy.statements[5].value[0].value
        )
        assert policy.statements[6].value[0].value == 'world"', (
            'Expected world" but got ' + policy.statements[6].value[0].value
        )
        assert policy.statements[7].value[0].value == "world'd'e'", (
            "Expected world'd'e' but got " + policy.statements[7].value[0].value
        )

    def test_modified_strings(self):
        policy = parse("""
        a := f"abc"
        b := r"abc"
        c := f'abc'
        d := r'abc'
        """)

        assert policy.statements[0].value[0].value == "abc"
        assert policy.statements[0].value[0].modifier == "f"
        assert policy.statements[1].value[0].value == "abc"
        assert policy.statements[1].value[0].modifier == "r"
        assert policy.statements[2].value[0].value == "abc"
        assert policy.statements[2].value[0].modifier == "f"
        assert policy.statements[3].value[0].value == "abc"
        assert policy.statements[3].value[0].modifier == "r"

    def test_ml_strings(self):
        policy = parse("""
        a := \"\"\"
        abc
        \"\"\"
        # with modifier
        b := r\"\"\"
        abc
        \"\"\"
        # f modifier
        c := f\"\"\"
        abc
        \"\"\"
                       
        # single quote
        d := \'\'\'
        abc
        \'\'\'
        # with modifier
        e := r\'\'\'
        abc
        \'\'\'
        # f modifier
        f := f\'\'\'
        abc
        \'\'\'
        """)

        assert policy.statements[0].value[0].value == "\nabc\n"
        assert policy.statements[1].value[0].value == "\nabc\n"
        assert policy.statements[1].value[0].modifier == "r"
        assert policy.statements[2].value[0].value == "\nabc\n"
        assert policy.statements[2].value[0].modifier == "f"

        assert policy.statements[3].value[0].value == "\nabc\n"
        assert policy.statements[4].value[0].value == "\nabc\n"
        assert policy.statements[4].value[0].modifier == "r"
        assert policy.statements[5].value[0].value == "\nabc\n"
        assert policy.statements[5].value[0].modifier == "f"

    def test_unary_func_call_precedence(self):
        policy = parse("""
        from invariant import Message, PolicyViolation

        raise PolicyViolation("Cannot send assistant message:", call) if:
            (call: Message)
            not call.content()
        """)
        self.assertIsInstance(policy.statements[1].body[1], ast.UnaryExpr)
        self.assertIsInstance(policy.statements[1].body[1].expr, ast.FunctionCall)

    def test_multi_binary(self):
        policy = parse("""
        raise "found result" if:
            (output: ToolOutput)
            a := "Cheerio" + "1" + "test"
        """)
        self.assertIsInstance(policy.statements[0].body[1], ast.BinaryExpr)
        # left is id
        self.assertIsInstance(policy.statements[0].body[1].left, ast.Identifier)
        # right is binary
        self.assertIsInstance(policy.statements[0].body[1].right, ast.BinaryExpr)
        rhs = policy.statements[0].body[1].right
        # left or rhs is binary
        self.assertIsInstance(rhs.left, ast.BinaryExpr)
        self.assertIsInstance(rhs.right, ast.StringLiteral)
        # left is id
        self.assertIsInstance(rhs.left.left, ast.StringLiteral)
        # right is id
        self.assertIsInstance(rhs.left.right, ast.StringLiteral)

    def test_in_with_member(self):
        policy = parse("""
        raise "found result" if:
            (output: ToolOutput)
            "abc" + "efg" in output.content
        """)

        self.assertIsInstance(policy.statements[0].body[1], ast.BinaryExpr)
        self.assertIsInstance(policy.statements[0].body[1].left, ast.BinaryExpr)

        self.assertIsInstance(policy.statements[0].body[1].left.left, ast.StringLiteral)
        self.assertIsInstance(policy.statements[0].body[1].left.right, ast.StringLiteral)

        self.assertIsInstance(policy.statements[0].body[1].right, ast.MemberAccess)
        self.assertIsInstance(policy.statements[0].body[1].right.expr, ast.Identifier)
        self.assertEqual(policy.statements[0].body[1].right.member, "content")
        self.assertEqual(policy.statements[0].body[1].op, "in")

    def test_in_with_member_three_components(self):
        policy = parse("""
        raise "found result" if:
            (output: ToolOutput)
            "abc" + "efg" + "hij" in output.content
        """)

        self.assertIsInstance(policy.statements[0].body[1], ast.BinaryExpr)
        self.assertIsInstance(policy.statements[0].body[1].left, ast.BinaryExpr)

        self.assertIsInstance(policy.statements[0].body[1].left.left, ast.BinaryExpr)
        self.assertIsInstance(policy.statements[0].body[1].left.right, ast.StringLiteral)

        self.assertIsInstance(policy.statements[0].body[1].left.left.left, ast.StringLiteral)
        self.assertIsInstance(policy.statements[0].body[1].left.left.right, ast.StringLiteral)

        self.assertIsInstance(policy.statements[0].body[1].right, ast.MemberAccess)
        self.assertIsInstance(policy.statements[0].body[1].right.expr, ast.Identifier)
        self.assertEqual(policy.statements[0].body[1].right.member, "content")

    def test_with_member_access_call_in_addition(self):
        policy = parse("""
        raise "found result" if:
            (to: ToolOutput)
            "File " + tc.function.arguments.arg.strip() + " not found" in to.content
        """)
        self.assertIsInstance(policy.statements[0].body[1], ast.BinaryExpr)
        self.assertIsInstance(policy.statements[0].body[1].left, ast.BinaryExpr)
        self.assertIsInstance(policy.statements[0].body[1].left.left, ast.BinaryExpr)

        self.assertIsInstance(policy.statements[0].body[1].left.left.left, ast.StringLiteral)
        self.assertIsInstance(policy.statements[0].body[1].left.left.right, ast.FunctionCall)

        self.assertIsInstance(policy.statements[0].body[1].left.left.right.name, ast.MemberAccess)
        self.assertIsInstance(
            policy.statements[0].body[1].left.left.right.name.expr, ast.MemberAccess
        )
        self.assertEqual(policy.statements[0].body[1].left.left.right.name.member, "strip")
        self.assertEqual(policy.statements[0].body[1].left.left.right.name.expr.member, "arg")
        self.assertEqual(
            policy.statements[0].body[1].left.left.right.name.expr.expr.member, "arguments"
        )
        self.assertEqual(
            policy.statements[0].body[1].left.left.right.name.expr.expr.expr.member, "function"
        )
        self.assertIsInstance(
            policy.statements[0].body[1].left.left.right.name.expr.expr.expr.expr, ast.Identifier
        )

    def test_assign_in(self):
        policy = parse("""
        raise "error" if:
            (msg: Message)
            flag := ["a", "b"] in ["a"]
        """)
        self.assertEqual(policy.statements[0].body[1].op, ":=")

    def test_quantifier_with_args(self):
        policy = parse("""
from invariant import count

raise "found result" if:
    count(min=2, max=4):
        (tc: ToolCall)
        tc is tool:get_inbox
    """)
        self.assertIsInstance(policy.statements[1].body[0], ast.Quantifier)
        self.assertIsInstance(policy.statements[1].body[0].body[0], ast.TypedIdentifier)

    def test_quantifier_without_args(self):
        policy = parse("""
from invariant import forall
        
raise "found result" if:
    forall:
        (call: ToolCall)
        call is tool:send_mail
    """)
        self.assertIsInstance(policy.statements[1].body[0], ast.Quantifier)
        self.assertIsInstance(policy.statements[1].body[0].body[0], ast.TypedIdentifier)

    def test_negated_without_args(self):
        policy = parse("""
from invariant import forall

raise "found result" if:
    not forall:
        (call: ToolCall)
        call is tool:send_mail
    """)
        self.assertIsInstance(policy.statements[1].body[0], ast.UnaryExpr)
        self.assertIsInstance(policy.statements[1].body[0].expr, ast.Quantifier)
        self.assertIsInstance(policy.statements[1].body[0].expr.body[0], ast.TypedIdentifier)

    def test_negated_with_args(self):
        policy = parse("""
from invariant import count
                       
raise "found result" if:
    not count(min=2, max=4):
        (tc: ToolCall)
        tc is tool:get_inbox
    """)
        self.assertIsInstance(policy.statements[1].body[0], ast.UnaryExpr)
        self.assertIsInstance(policy.statements[1].body[0].expr, ast.Quantifier)
        self.assertIsInstance(policy.statements[1].body[0].expr.body[0], ast.TypedIdentifier)


if __name__ == "__main__":
    unittest.main()
