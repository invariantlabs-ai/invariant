import ast
import asyncio
import json
import subprocess
import tempfile
from typing import Literal

from pydantic import BaseModel
from pydantic.dataclasses import Field

from invariant.analyzer.runtime.runtime_errors import InvariantAttributeError
from invariant.analyzer.runtime.utils.base import BaseDetector, DetectorResult

CodeSeverity = Literal["info", "warning", "error"]


class CodeIssue(BaseModel):
    description: str
    severity: CodeSeverity

    def __invariant_attribute__(self, name: str):
        if name in ["description", "severity"]:
            return getattr(self, name)
        raise InvariantAttributeError(
            f"Attribute {name} not found in CodeIssue. Available attributes are: description, severity"
        )


class PythonDetectorResult(BaseModel):
    """
    Represents the analysis results of a Python code snippet.

    Usage in IPL:

    ```
    from invariant.analyzer.detectors.code import python_code

    raise ... if:
        program := python_code(...)
        "os" in program.imports
    ```
    """

    # imported modules
    imports: list[str] = Field(default_factory=list, description="List of imported modules.")
    # built-in functions used
    builtins: list[str] = Field(
        default_factory=list, description="List of built-in functions used."
    )
    # whether code has syntax errors
    syntax_error: bool = Field(
        default=False, description="Flag which is true if code has syntax errors."
    )
    syntax_error_exception: str | None = Field(
        default=None, description="Exception message if syntax error occurred."
    )
    # function call identifier names
    function_calls: set[str] = Field(
        default_factory=set,
        description="Set of function call targets as returned by 'ast.unparse(node.func).strip()'",
    )

    def add_import(self, module: str):
        self.imports.append(module)

    def add_builtin(self, builtin: str):
        self.builtins.append(builtin)

    def add_function_call(self, function: str):
        self.function_calls.add(function)

    def extend(self, other: "PythonDetectorResult"):
        if type(other) != PythonDetectorResult:
            raise ValueError("Expected PythonDetectorResult object")
        self.imports.extend(other.imports)
        self.builtins.extend(other.builtins)
        self.function_calls.update(other.function_calls)
        if other.syntax_error:
            self.syntax_error = True

    def __invariant_attribute__(self, name: str):
        if name in [
            "imports",
            "builtins",
            "function_calls",
            "syntax_error",
            "syntax_error_exception",
            "function_calls",
        ]:
            return getattr(self, name)
        raise InvariantAttributeError(
            f"Attribute {name} not found in PythonDetectorResult. Available attributes are: imports, builtins, function_calls"
        )


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
            res.append(DetectorResult(type, loc, loc + len(source_seg), 0.5))
            text = text[loc + len(source_seg) :]

        return res

    def visit_Name(self, node):
        if node.id in self._builtins:
            self.res.add_builtin(node.id)

    def visit_Import(self, node):
        for alias in node.names:
            self.res.add_import(alias.name)

    def visit_ImportFrom(self, node):
        self.res.add_import(node.module)

    def visit_Call(self, node):
        self.res.add_function_call(ast.unparse(node.func).strip())
        self.generic_visit(node)


class PythonCodeDetector(BaseDetector):
    """Detector which extracts entities from Python code.

    The detector extracts the following entities:

    - Imported modules
    - Built-in functions used
    """

    def __init__(self, ipython_mode=False):
        super().__init__()

    def ipython_preprocess(self, text: str) -> str:
        """
        Preprocesses the text like in IPython cell parsing (e.g. handles indentation differences,
        cell magic commands, etc.).
        """
        from IPython.core.inputtransformer2 import TransformerManager

        transformer_manager = TransformerManager()
        return transformer_manager.transform_cell(text)

    def detect(self, text: str, ipython_mode=False) -> PythonDetectorResult:
        try:
            if ipython_mode:
                text = self.ipython_preprocess(text)
            ast_visitor = ASTDetectionVisitor(text)
            tree = ast.parse(text)
            ast_visitor.visit(tree)
        except Exception as e:
            return PythonDetectorResult(syntax_error=True, syntax_error_exception=str(e))
        return ast_visitor.res


class SemgrepDetector(BaseDetector):
    """Detector which uses Semgrep for safety evaluation."""

    CODE_SUFFIXES = {
        "python": ".py",
        "bash": ".sh",
    }

    def write_to_temp_file(self, code: str, lang: str) -> str:
        suffix = self.CODE_SUFFIXES.get(lang, ".txt")
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
        with open(temp_file.name, "w") as fou:
            fou.write(code)
        return temp_file.name

    def get_severity(self, severity: str) -> CodeSeverity:
        if severity == "ERROR":
            return "error"
        elif severity == "WARNING":
            return "warning"
        return "info"

    async def adetect_all(self, code: str, lang: str) -> list[CodeIssue]:
        temp_file = self.write_to_temp_file(code, lang)
        if lang == "python":
            config = "r/python.lang.security"
        elif lang == "bash":
            config = "r/bash"
        else:
            raise ValueError(f"Unsupported language: {lang}")

        cmd = [
            "poetry",
            "run",
            "semgrep",
            "scan",
            "--json",
            "--config",
            config,
            "--metrics",
            "off",
            "--quiet",
            temp_file,
        ]
        try:
            out = await asyncio.create_subprocess_exec(
                *cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = await out.communicate()
            semgrep_res = json.loads(stdout.decode("utf-8"))
        except Exception:
            out = await asyncio.create_subprocess_exec(
                *cmd[2:], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = await out.communicate()
            semgrep_res = json.loads(stdout.decode("utf-8"))
        issues = []
        for res in semgrep_res["results"]:
            severity = self.get_severity(res["extra"]["severity"])
            source = res["extra"]["metadata"]["source"]
            message = res["extra"]["message"]
            lines = res["extra"]["lines"]
            description = f"{message} (source: {source}, lines: {lines})"
            issues.append(CodeIssue(description=description, severity=severity))
        return issues
