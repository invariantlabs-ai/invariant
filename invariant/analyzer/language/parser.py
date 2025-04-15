"""
Invariant Policy Language parser.
"""

import textwrap

import lark

from invariant.analyzer.language.ast import *
from invariant.analyzer.language.ast import BinaryExpr, FunctionCall, Identifier, ValueReference
from invariant.analyzer.language.optimizer import optimize
from invariant.analyzer.language.typing import typing

"""
Lark EBNF grammar for the Invariant Policy Language.
"""
parser = lark.Lark(r"""
    %import common.NUMBER

    start: statement*

    statement: raise_stmt | def_stmt | decl_stmt | import_stmt

    import_stmt: full_import | from_import
    full_import: "import" import_spec
    from_import: "from" IMPORT_MODULE "import" import_spec ("," import_spec)*
    import_spec: ID | IMPORT_MODULE "as" ID
    IMPORT_MODULE: ID ("." ID)*

    raise_stmt: "raise" ( ID | func_call | STRING ) "if" INDENT NEWLINE? expr (NEWLINE expr)* DEDENT
    def_stmt: "def" func_signature INDENT NEWLINE? statement* DEDENT
    decl_stmt: ( ID | func_signature ) ":=" expr | ( ID | func_signature ) INDENT NEWLINE? expr (NEWLINE expr)* DEDENT

    expr: ID | assignment_expr | "(" expr ("," expr)* ")" | block_expr | import_stmt

    quantifier_expr: ( "not" )? ( func_call | ID ) INDENT NEWLINE? expr (NEWLINE expr)* DEDENT
    block_expr: INDENT expr (NEWLINE expr)* DEDENT

    assignment_expr: ( ID ":=" binary_expr ) | binary_expr
    binary_expr: cmp_expr LOGICAL_OPERATOR cmp_expr | cmp_expr
    cmp_expr: ( term CMP_OPERATOR term ) | term
    term: factor TERM_OPERATOR factor | factor
    factor: power FACTOR_OPERATOR power | power
    power: atom POWER_OPERATOR atom | atom
    atom: unary_expr | NUMBER | multiline_string | STRING | ID | "(" expr ")" | member_access | key_access | expr | func_call | quantifier_expr | typed_identifier | tool_ref | object_literal | list_literal | STAR | value_ref | list_comprehension | ternary_op

    unary_expr: UNARY_OPERATOR expr
    func_call: expr  "(" ( (expr ("," expr)*)? ("," kwarg ("," kwarg)*)? ) ")" | \
               expr  "(" (kwarg ("," kwarg)*)? ")"
    kwarg: ID "=" expr
    func_signature: ID "(" (parameter_decl ("," parameter_decl)*)? ")"
    parameter_decl: ID ":" ID

    member_access: expr "." ID
    key_access: expr "[" expr "]"

    typed_identifier: "(" ID ":" ID ")"
    tool_ref: "tool" ":" ID

    object_literal: "{" ( object_entry ("," object_entry)* )? "}"
    object_entry: (ID|STRING) ":" expr
    list_literal: "[" ( expr ("," expr)* )? "]"
    list_comprehension: "[" expr "for" ID "in" expr ("if" expr)? "]"
    STAR: "*"
    value_ref: VALUE_TYPE

    multiline_string: ML_STRING | SINGLE_ML_STRING

    STRING: QUOTED_STRING | SINGLE_QUOTED_STRING
    ML_STRING: ("r" | "f")? /\"\"\"(?:[^"\\]|\\.|"{1,2}(?!"))*\"\"\"/
    SINGLE_ML_STRING: ("r" | "f")? /'''(?:[^'\\]|\\.|'{1,2}(?!'))*'''/

    # from common.lark
    _STRING_INNER: /.*?/
    _STRING_ESC_INNER: _STRING_INNER /(?<!\\)(\\\\)*?/

    QUOTED_STRING: ("r"|"f")? "\"" _STRING_ESC_INNER "\""
    SINGLE_QUOTED_STRING: ("r"|"f")? "'" _STRING_ESC_INNER "'"

    INDENT: "|INDENT|"
    DEDENT: "|DEDENT|"

    ID.2: /[a-zA-Z_]([a-zA-Z0-9_])*/
    UNARY_OPERATOR.3: /not[\n\t ]/ | "-" | "+"
    LOGICAL_OPERATOR: /and[\n\t ]/ | /or[\n\t ]/
    CMP_OPERATOR: "==" | "!=" | ">" | "<" | ">=" | "<=" | /is[\n\t ]/ | /contains_only[\n\t ]/ | /in[\n\t ]/ | "->" | "~>"
    VALUE_TYPE: /<[a-zA-Z_:]+>/
    ternary_op: expr "if" expr "else" expr

    TERM_OPERATOR: "+" | "-"
    FACTOR_OPERATOR: "*" | "/" | "%"
    POWER_OPERATOR: "**"

    NEWLINE: "\n"

    %ignore " "
    %ignore "\t"
    %ignore "\n"
    %ignore COMMENT
    COMMENT: /#.*/
""")


def indent_level(line, unit=1):
    # count the number of leading spaces
    return (len(line) - len(line.lstrip())) // unit


def derive_indentation_units(text):
    # derive the indentation unit from the first non-empty line
    lines = text.split("\n")
    indents = set()
    for line in lines:
        if indent_level(line) > 0:
            indents.add(indent_level(line))
    if len(indents) == 0:
        return 1
    return min(indents)


def parse_indents(text):
    """
    This function parses an intended snippet of IPL code and returns a version of the code
    where indents are replaced by |INDENT| and |DEDENT| tokens.

    This allows our actual language grammar above to be context-free, as it does not need to
    handle indentation, but can rely on the |INDENT| and |DEDENT| tokens instead.

    |INDENT| and |DEDENT| tokens fulfill the same role as e.g. `{` and `}` in C-like languages.

    Example:
    ```
    def foo:
        bar
    ```

    is transformed into:

    ```
    def foo: |INDENT|
    bar |DEDENT|
    ```
    """
    indent_unit = derive_indentation_units(text)
    lines = text.split("\n")

    line_mappings = {}
    result = ""
    indent = 0

    for i, line in enumerate(lines):
        n = indent_level(line, unit=indent_unit)
        if line.lstrip() == "":
            continue

        if n > indent and (result.rstrip().endswith(":") or result.rstrip().endswith(":=")):
            result_stripped = (
                result.rstrip()[:-1] if result.rstrip().endswith(":") else result.rstrip()[:-2]
            )
            result = result_stripped + (" |INDENT|" * (n - indent))
            indent = n
            line = line  # [n * indent_unit :]

        dedents = ""
        while n < indent:
            dedents = "|DEDENT|" + dedents
            indent -= 1

        result += dedents + "\n" + line
        char_offset = (1 + n * indent_unit) if n > 0 else 1
        line_mappings[len(result.split("\n"))] = (
            i,
            char_offset,
        )  # line number, character offset

    if indent > 0:
        result += "\n" + "|DEDENT| " * indent

    # for i,line in enumerate(result.split("\n")):
    #     print(i, "->", line_mappings.get(i, ""), ":", line)

    return result, line_mappings


class IPLTransformer(lark.Transformer):
    """
    Constructs the AST, given some IPL parse tree.
    """

    def __init__(self, line_mappings=None, source_code=None):
        self.line_mappings = line_mappings or {}
        self.source_code = source_code

    def filter(self, items):
        IGNORED = ["INDENT", "DEDENT", "NEWLINE"]
        results = []
        for i in items:
            if type(i) is lark.lexer.Token and i.type in IGNORED:
                continue
            results.append(i)
        return results

    def start(self, items):
        return PolicyRoot(items)

    def statement(self, items):
        return items[0]

    def import_stmt(self, items):
        return items[0]

    def full_import(self, items):
        return Import(items[0].name, [], alias=items[0].alias).with_location(self.loc(items))

    def from_import(self, items):
        return Import(items[0], self.filter(items[1:])).with_location(self.loc(items))

    def import_spec(self, items):
        if len(items) == 1:
            return ImportSpecifier(items[0].name, None).with_location(self.loc(items))
        return ImportSpecifier(items[0], items[1].name).with_location(self.loc(items))

    def IMPORT_MODULE(self, items):
        return str(items)

    def raise_stmt(self, items):
        body = items[1:]
        # filter hidden body tokens
        body = self.filter(body)
        # flatten exprs
        while type(body) is list and len(body) == 1:
            body = body[0]
        if type(body) is not list:
            body = [body]

        return RaisePolicy(items[0], body).with_location(self.loc(items))

    def quantifier_expr(self, items):
        quantifier_call = items[0]
        body = self.filter(items[1:])
        # unpack body if it's a indented block
        while type(body) is list and len(body) == 1:
            body = body[0]
        return Quantifier(quantifier_call, body).with_location(self.loc(items))

    def def_stmt(self, items):
        return FunctionDefinition(
            items[0], self.filter(items[1:1]), self.filter(items[2:])
        ).with_location(self.loc(items))

    def decl_stmt(self, items):
        return Declaration(items[0], self.filter(items[1:])).with_location(self.loc(items))

    def func_signature(self, items):
        return FunctionSignature(items[0], self.filter(items[1:])).with_location(self.loc(items))

    def parameter_decl(self, items):
        return ParameterDeclaration(items[0], items[1]).with_location(self.loc(items))

    def expr(self, items):
        return items[0]

    def assignment_expr(self, items):
        if len(items) == 1:
            return items[0]
        return BinaryExpr(items[0], ":=", items[1]).with_location(self.loc(items))

    def block_expr(self, items):
        return self.filter(items)

    def binary_expr(self, items):
        if len(items) == 1:
            return items[0]
        return BinaryExpr(items[0], items[1].strip(), items[2]).with_location(self.loc(items))

    def cmp_expr(self, items):
        if len(items) == 1:
            return items[0]
        return BinaryExpr(items[0], items[1].strip(), items[2]).with_location(self.loc(items))

    def term(self, items):
        if len(items) == 1:
            return items[0]
        return BinaryExpr(items[0], items[1].strip(), items[2]).with_location(self.loc(items))

    def factor(self, items):
        if len(items) == 1:
            return items[0]
        return BinaryExpr(items[0], items[1].strip(), items[2]).with_location(self.loc(items))

    def power(self, items):
        if len(items) == 1:
            return items[0]
        return BinaryExpr(items[0], items[1].strip(), items[2]).with_location(self.loc(items))

    def atom(self, items):
        if len(items) == 1:
            return items[0]
        return BinaryExpr(items[0], items[1].strip(), items[2]).with_location(self.loc(items))

    def unary_expr(self, items):
        return UnaryExpr(items[0].strip(), items[1]).with_location(self.loc(items))

    def typed_identifier(self, items):
        return TypedIdentifier(items[1].name, items[0].name).with_location(self.loc(items))

    def func_call(self, items):
        return FunctionCall(items[0], items[1:]).with_location(self.loc(items))

    def tool_ref(self, items):
        return ToolReference(items[0].name).with_location(self.loc(items))

    def kwarg(self, items):
        return (items[0].name, items[1])

    def object_literal(self, items):
        return ObjectLiteral(items).with_location(self.loc(items))

    def object_entry(self, items):
        key = items[0]
        if type(key) is Identifier:
            key = key.name
        elif type(key) is StringLiteral:
            key = key.value
        else:
            key = str(key)
        return ObjectEntry(key, items[1]).with_location(self.loc(items))

    def list_literal(self, items):
        return ArrayLiteral(items).with_location(self.loc(items))

    def list_comprehension(self, items):
        # Extract components of the list comprehension
        expr = items[0]  # Expression to evaluate for each item
        var_name = items[1]  # Variable name (ID node)
        iterable = items[2]  # Iterable to loop over
        condition = None

        # If there's a condition ('if' clause)
        if len(items) > 3:
            condition = items[3]

        return ListComprehension(expr, var_name, iterable, condition).with_location(self.loc(items))

    def STAR(self, items):
        return Wildcard().with_location(self.loc(items))

    def value_ref(self, items):
        return ValueReference(str(items[0])[1:-1]).with_location(self.loc(items[0]))

    def VALUE_TYPE(self, items):
        return items

    def member_access(self, items):
        return MemberAccess(items[0], items[1].name).with_location(self.loc(items))

    def key_access(self, items):
        return KeyAccess(items[0], items[1]).with_location(self.loc(items))

    def STRING(self, items):
        offset = 1
        quote_type = str(items)[0]
        modifier = None
        if str(items)[0] != '"' and str(items)[0] != "'":
            modifier = str(items)[0]
            offset = 2
            quote_type = str(items)[1]
        return StringLiteral(
            items[offset:-1], quote_type=quote_type, modifier=modifier
        ).with_location(self.loc(items))

    def multiline_string(self, items):
        return items[0]

    def ML_STRING(self, items):
        offset = 3
        quote_type = str(items)[1]
        modifier = None
        if str(items)[0] != '"' and str(items)[0] != "'":
            modifier = str(items)[0]
            offset = 4
            quote_type = str(items)[2]
        value = items[offset:-3]
        return StringLiteral(
            value, multi_line=True, quote_type=quote_type, modifier=modifier
        ).with_location(self.loc(items))

    def SINGLE_ML_STRING(self, items):
        offset = 3
        quote_type = str(items)[1]
        modifier = None
        if str(items)[0] != '"' and str(items)[0] != "'":
            modifier = str(items)[0]
            offset = 4
            quote_type = str(items)[2]
        value = items[offset:-3]
        return StringLiteral(
            value, multi_line=True, quote_type=quote_type, modifier=modifier
        ).with_location(self.loc(items))

    def ID(self, items):
        if str(items) == "None":
            return NoneLiteral().with_location(self.loc(items))
        if str(items) == "True":
            return BooleanLiteral(True).with_location(self.loc(items))
        if str(items) == "False":
            return BooleanLiteral(False).with_location(self.loc(items))
        return Identifier(str(items)).with_location(self.loc(items))

    def NUMBER(self, items):
        try:
            return NumberLiteral(int(str(items))).with_location(self.loc(items))
        except ValueError:
            return NumberLiteral(float(str(items))).with_location(self.loc(items))

    def loc(self, items):
        return Location.from_items(items, self.line_mappings, self.source_code)

    def ternary_op(self, items):
        return TernaryOp(items[0], items[1], items[2]).with_location(self.loc(items))


def transform(policy):
    """
    Basic transformations to simplify the AST
    """

    class PostParsingTransformations(Transformation):
        # transforms FunctionCall with a ToolReference target into a SemanticPattern
        def visit_FunctionCall(self, node: FunctionCall):
            if type(node.name) is ToolReference:
                return SemanticPattern(
                    node.name,
                    node.args,
                ).with_location(node.location)
            return super().visit_FunctionCall(node)

    policy = PostParsingTransformations().visit(policy)
    return policy


def parse(text, path=None, verbose=True, optimize_rules=True):
    """
    Multi-stage parsing process to transform a string of IPL code into an Invariant Policy AST.

    The parsing stages are as follows:

    1. Indentation parsing: The input code is transformed into a version where indents are marked with |INDENT| and |DEDENT| tokens, instead of actual indentation.
    2. Lark parsing: The indented code is parsed using the Lark parser as defined by the grammar above.
    3. AST construction: The Lark parse tree is transformed into an AST.
    4. AST post-processing: The AST is simplified and transformed.
    5. Type checking: The AST is type-checked.

    """

    # removes common leading indent (e.g. when parsing from an indented multiline string)
    text = textwrap.dedent(text)
    # creates source code handle
    source_code = SourceCode(text, path=path, verbose=verbose)

    # translates an indent-based code into code in which indented
    # blocks are marked with |INDENT| and |DEDENT| tokens
    # mapping contains the line number and character offset of the original code, which allows
    # us to translate lark errors back to the actual code
    indented_text, mappings = parse_indents(text)

    try:
        # runs actual lark parser
        parse_tree = parser.parse(indented_text)

        # parse tree -> AST
        transformer = IPLTransformer(mappings, source_code)
        policy = transformer.transform(parse_tree)

        # AST post-processing (basic simplifications)
        policy = transform(policy)

        # scoping and type checking (populate type information into the AST)
        policy = typing(policy)

        # optimize policy for inference
        if optimize_rules:
            policy = optimize(policy)

        policy.source_code = source_code

        return policy

    except lark.exceptions.UnexpectedCharacters as e:
        error_line = e.line
        error_column = e.column

        line, char = mappings.get(error_line, (0, 0))
        error_line = line
        # error_column += char

        policy = PolicyRoot([])

        error_node = Node().with_location(Location(error_line, error_column, source_code))
        policy.errors = [PolicyError(str(e), error_node)]

        # # get 2 lines before and after the error line
        # source_code.print_error(e, error_line, error_column, 2)

        return policy


def parse_file(file):
    with open(file) as f:
        text = f.read()
    return parse(text, path=file)
