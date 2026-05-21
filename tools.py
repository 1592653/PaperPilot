"""Tool definitions and executors shared across all modules."""

import io
import json
import traceback
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path


def read_file(path: str) -> dict:
    try:
        p = Path(path)
        if not p.exists():
            return {"error": f"File not found: {path}"}
        return {"path": str(p), "size": p.stat().st_size, "content": p.read_text(encoding="utf-8")[:80000]}
    except Exception as e:
        return {"error": str(e)}


def write_file(path: str, content: str) -> dict:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"path": str(p), "bytes_written": len(content.encode("utf-8"))}
    except Exception as e:
        return {"error": str(e)}


def list_dir(path: str = ".") -> dict:
    try:
        entries = []
        for item in sorted(Path(path).iterdir()):
            entries.append({"name": item.name, "type": "dir" if item.is_dir() else "file",
                            "size": item.stat().st_size if item.is_file() else 0})
        return {"path": path, "count": len(entries), "entries": entries}
    except Exception as e:
        return {"error": str(e)}


def run_python(code: str) -> dict:
    """Execute Python code and capture stdout/stderr."""
    stdout_buf, stderr_buf = io.StringIO(), io.StringIO()
    result = {}
    try:
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            exec(compile(code, "<paperpilot>", "exec"), {"__builtins__": __builtins__})
        result["status"] = "success"
    except Exception:
        result["status"] = "error"
    result["stdout"] = stdout_buf.getvalue()[:15000]
    result["stderr"] = stderr_buf.getvalue()[:15000] if result["status"] == "error" else stderr_buf.getvalue()[:5000]
    return result


# --- Tool definitions for Claude API ---

COMMON_TOOLS = [
    {
        "name": "read_file",
        "description": "Read a file's content. Use to inspect datasets, code, or results.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file. Creates directories as needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_dir",
        "description": "List files in a directory.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Directory path"}},
        },
    },
    {
        "name": "run_python",
        "description": "Execute Python code. Use for data analysis, computation, visualization, or running ML experiments.",
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "Python code to execute"}},
            "required": ["code"],
        },
    },
]

TOOL_MAP = {
    "read_file": lambda **kw: read_file(kw["path"]),
    "write_file": lambda **kw: write_file(kw["path"], kw["content"]),
    "list_dir": lambda **kw: list_dir(kw.get("path", ".")),
    "run_python": lambda **kw: run_python(kw["code"]),
}


def execute_tool(name: str, inputs: dict) -> dict:
    fn = TOOL_MAP.get(name)
    if not fn:
        return {"error": f"Unknown tool: {name}"}
    return fn(**inputs)
