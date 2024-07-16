import re
from invariant.stdlib.invariant.errors import PolicyViolation
from pathlib import Path
from pydantic.dataclasses import dataclass
from typing import Optional

@dataclass
class File:
    path: str
    content: str

def filter_path(path: list[Path], pattern: Optional[str]) -> Path:
    return pattern is None or path.match(pattern)

def join_paths(workspace_path: str, path: str) -> Path:
    """Checks if path is inside workspace_path and it exists."""
    joined_path = Path(workspace_path) / Path(path)
    if (not joined_path.is_relative_to(workspace_path)) or  (not joined_path.exists()):
        raise FileNotFoundError("Path does not exist or is not inside the workspace.")
    return joined_path

def get_files(workspace_path: str, path: str = ".", pattern: Optional[str] = None) -> list[str]:
    """Returns the list of files in the current agent workspace."""
    path = join_paths(workspace_path, path)
    return [file for file in path.iterdir() if file.is_file() and filter_path(file, pattern)]

def get_tree_files(workspace_path: str, path: str = ".", pattern: Optional[str] = None) -> list[str]:
    """Returns the list of files in the whole directory tree of the agent workspace."""
    path = join_paths(workspace_path, path)
    return [file for file in path.glob("**/*") if file.is_file() and filter_path(file, pattern)]

def get_file_content(workspace_path: str, file_path: str) -> File:
    """Returns the content of a file in the agent workspace."""
    file_path = join_paths(workspace_path, file_path)
    with open(file_path, "r") as file:
        return File(str(file_path), file.read())

def get_file_contents(workspace_path: str, path: str = ".", pattern: Optional[str] = None, tree: bool = True) -> list[File]:
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
    

