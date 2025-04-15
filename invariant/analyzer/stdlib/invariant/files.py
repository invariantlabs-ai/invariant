from pathlib import Path
from typing import Callable, Optional

from pydantic.dataclasses import dataclass

from invariant.analyzer.runtime.evaluation import Interpreter
from invariant.analyzer.runtime.runtime_errors import InvariantAttributeError


@dataclass
class File:
    path: str
    content: str

    def __invariant_attribute__(self, name: str):
        if name in ["path", "content"]:
            return getattr(self, name)
        raise InvariantAttributeError(
            f"Attribute {name} not found in File class. Only 'path' and 'content' are allowed."
        )


def filter_path(path: list[Path], pattern: Optional[str]) -> Path:
    return pattern is None or path.match(pattern)


def join_paths(workspace_path: str, path: str) -> Path:
    """Checks if path is inside workspace_path and it exists."""
    joined_path = Path(workspace_path) / Path(path)
    if (not joined_path.is_relative_to(workspace_path)) or (not joined_path.exists()):
        raise FileNotFoundError("Path does not exist or is not inside the workspace.")
    return joined_path


def get_files(workspace_path: str, path: str = ".", pattern: Optional[str] = None) -> list[str]:
    """Returns the list of files in the current agent workspace."""
    path = join_paths(workspace_path, path)
    return [file for file in path.iterdir() if file.is_file() and filter_path(file, pattern)]


def get_tree_files(
    workspace_path: str, path: str = ".", pattern: Optional[str] = None
) -> list[str]:
    """Returns the list of files in the whole directory tree of the agent workspace."""
    path = join_paths(workspace_path, path)
    return [file for file in path.glob("**/*") if file.is_file() and filter_path(file, pattern)]


def get_file_content(workspace_path: str, file_path: str) -> File:
    """Returns the content of a file in the agent workspace."""
    file_path = join_paths(workspace_path, file_path)
    with open(file_path, "r") as file:
        return File(str(file_path), file.read())


def get_file_contents(
    workspace_path: str, path: str = ".", pattern: Optional[str] = None, tree: bool = True
) -> list[File]:
    """Returns the content of all files in the given path in the agent workspace.

    Args:
        workspace_path: The path to the agent workspace.
        path: The path to the directory to search for files.
        pattern: A regular expression pattern to filter the files.
        tree: If True, search the whole directory tree of the workspace.
    """
    if tree:
        files = get_tree_files(workspace_path, path)
    else:
        files = get_files(workspace_path, path)
    return [get_file_content(workspace_path, file) for file in files]


async def is_sensitive(file: File, func: Callable[[str], bool | list]) -> bool:
    """Returns True if the file content is sensitive according to the given function.

    Args:
        file: The file to check for content sensitivity.
        func: The function that determines sensitivity (each should return bool or list of sensitive results)
    """
    res = await Interpreter.current().acall_function(func, file.content)
    if type(res) is bool:
        return res
    if type(res) is list:
        return len(res) > 0
    raise ValueError(
        "The sensitivity filter function must return bool or list, found: " + str(type(res))
    )


async def is_sensitive_dir(
    workspace_path: str,
    funcs: list[Callable[[str], bool | list]],
    path: str = ".",
    pattern: Optional[str] = None,
    tree: bool = True,
) -> bool:
    """Returns True if any file in the given directory is sensitive according to any of the given sensitivity functions

    Args:
        workspace_path: The path to the agent workspace.
        funcs: The list of functions that determine sensitivity (each should return bool or list of sensitive results)
        path: The path to the directory inside the workspace to search for files.
        pattern: A regular expression pattern to filter the files.
        tree: If True, search the whole directory tree of the workspace.
    """
    files = get_file_contents(workspace_path, path, pattern, tree)
    for file in files:
        for func in funcs:
            if await is_sensitive(file, func):
                return True
    return False
