import ast
import asyncio
from invariant.runtime.utils.base import BaseDetector, DetectorResult
from pydantic.dataclasses import dataclass, Field
from invariant.extras import codeshield_extra

@dataclass
class CodeIssue:
    description: str
    severity: str


@dataclass
class PythonDetectorResult:
    """
    Represents the analysis results of a Python code snippet.

    Usage in IPL:

    ```
    from invariant.detectors.code import python_code

    raise ... if:
        program := python_code(...)
        "os" in program.imports
    ```
    """

    # imported modules
    imports: list[str] = Field(default_factory=list, description="List of imported modules.")
    # built-in functions used
    builtins: list[str] = Field(default_factory=list, description="List of built-in functions used.")
    # whether code has syntax errors
    syntax_error: bool = Field(default=False, description="Flag which is true if code has syntax errors.")
    
    def add_import(self, module: str):
        self.imports.append(module)

    def add_builtin(self, builtin: str):
        self.builtins.append(builtin)

    def extend(self, other: "PythonDetectorResult"):
        if type(other) != PythonDetectorResult:
            raise ValueError("Expected PythonDetectorResult object")
        self.imports.extend(other.imports)
        self.builtins.extend(other.builtins)


class ASTDetectionVisitor(ast.NodeVisitor):

    def __init__(self, code: str):
        self.code = code
        self.res = PythonDetectorResult()
        self._builtins = globals()["__builtins__"].keys()

    # TODO: Not used right now, but can find source code corresponding to node (for e.g. masking or warning)
    def _get_match_results(self, type: str, text: str, node: ast.AST) -> list[DetectorResult]:
        source_seg = ast.get_source_segment(text, node)
        res = []

        while source_seg in text:
            loc = str.find(text, source_seg)
            res.append(DetectorResult(type, loc, loc+len(source_seg), 0.5))
            text = text[loc+len(source_seg):]

        return res
    
    def visit_Name(self, node):
        if node.id in self._builtins:
            self.res.add_builtin(node.id)

    def visit_Import(self, node):
        for alias in node.names:
            self.res.add_import(alias.name)

    def visit_ImportFrom(self, node):
        self.res.add_import(node.module)

class PythonCodeDetector(BaseDetector):
    """Detector which extracts entities from Python code.

    The detector extracts the following entities:

    - Imported modules
    - Built-in functions used
    """

    def __init__(self):
        super().__init__()

    def detect(self, text: str) -> PythonDetectorResult:
        ast_visitor = ASTDetectionVisitor(text)
        try:
            tree = ast.parse(text)
            ast_visitor.visit(tree)
        except Exception as e:
            return PythonDetectorResult(syntax_error=True)
        return ast_visitor.res


class CodeShieldDetector(BaseDetector):
    """Detector which uses Llama CodeShield for safety (currently based on regex and semgrep rules)"""

    async def scan_llm_output(self, llm_output_code):
        self.CodeShield = codeshield_extra.package("codeshield.cs").import_names("CodeShield")
        result = await self.CodeShield.scan_code(llm_output_code)
        return result

    def detect_all(self, text: str) -> list[CodeIssue]:
        res = asyncio.run(self.scan_llm_output(text))
        if res.issues_found is None:
            return []
        return [
            CodeIssue(description=issue.description, severity=str(issue.severity).lower())
            for issue in res.issues_found
        ]
