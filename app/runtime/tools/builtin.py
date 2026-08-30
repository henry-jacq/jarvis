import os
import subprocess
from typing import Dict, Any, List

def read_project_file(file_path: str, max_lines: int = 500) -> Dict[str, Any]:
    """
    Reads content from a project file safely.
    """
    if not os.path.exists(file_path):
        return {"status": "error", "error": f"File not found: {file_path}"}
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = [f.readline() for _ in range(max_lines)]
        return {
            "status": "success",
            "file_path": file_path,
            "content": "".join(lines),
            "lines_read": len(lines)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

def git_diff(repo_path: str = ".") -> Dict[str, Any]:
    """
    Executes git diff in the specified repository path.
    """
    try:
        result = subprocess.run(
            ["git", "diff"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        return {
            "status": "success",
            "diff": result.stdout or "No changes detected.",
            "stderr": result.stderr
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

def list_directory(dir_path: str = ".") -> Dict[str, Any]:
    """
    Lists entries in a directory.
    """
    if not os.path.exists(dir_path):
        return {"status": "error", "error": f"Directory not found: {dir_path}"}
    try:
        entries = os.listdir(dir_path)
        return {
            "status": "success",
            "dir_path": dir_path,
            "entries": entries
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

BUILTIN_TOOL_MAP = {
    "read_project_file": {
        "function": read_project_file,
        "description": "Reads contents of a specified file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute or relative file path to read"},
                "max_lines": {"type": "integer", "default": 500}
            },
            "required": ["file_path"]
        },
        "risk_level": "LOW"
    },
    "git_diff": {
        "function": git_diff,
        "description": "Returns current uncommitted git diff.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "default": "."}
            }
        },
        "risk_level": "LOW"
    },
    "list_directory": {
        "function": list_directory,
        "description": "Lists files and folders in a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dir_path": {"type": "string", "default": "."}
            }
        },
        "risk_level": "LOW"
    }
}
