# Copyright 2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""Check that all test functions contain at least one assertion."""

import ast
import shutil
import subprocess  # noqa: S404 - Used safely with hardcoded args and shell=False
import sys
from pathlib import Path

_ASSERT_PREFIXES = ("assert_called", "assert_awaited", "assert_any_call", "assert_not_called")


def get_staged_test_files() -> list[Path]:
    """Return staged test file paths matching tests/**/*.py."""
    git = shutil.which("git") or "git"
    result = subprocess.run(  # noqa: S603
        [git, "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [
        Path(p) for p in result.stdout.splitlines() if p.startswith("tests/") and p.endswith(".py")
    ]


def get_modified_line_ranges(filepath: Path) -> set[int]:
    """Return line numbers added or changed in the staged diff for filepath."""
    git = shutil.which("git") or "git"
    result = subprocess.run(  # noqa: S603
        [git, "diff", "--cached", "-U0", str(filepath)],
        capture_output=True,
        text=True,
        check=True,
    )
    lines: set[int] = set()
    for line in result.stdout.splitlines():
        if line.startswith("@@"):
            parts = line.split("+")[1].split("@@")[0].strip()
            start, _, length = parts.partition(",")
            start_n = int(start)
            count = int(length) if length else 1
            lines.update(range(start_n, start_n + count))
    return lines


def _call_is_assertion(node: ast.Call) -> bool:
    attr = None
    if isinstance(node.func, ast.Attribute):
        attr = node.func.attr
    elif isinstance(node.func, ast.Name):
        attr = node.func.id
    if attr and any(attr.startswith(p) for p in _ASSERT_PREFIXES):
        return True
    return isinstance(node.func, ast.Attribute) and node.func.attr == "raises"


def has_assertion(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if func_node contains at least one assertion."""
    return any(
        isinstance(node, ast.Assert) or (isinstance(node, ast.Call) and _call_is_assertion(node))
        for node in ast.walk(func_node)
    )


def get_unasserted_named_mocks(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[str]:
    """Return names of 'with ... as <name>:' aliases that have no assert_* call."""
    aliases: list[str] = [
        item.optional_vars.id
        for node in ast.walk(func_node)
        if isinstance(node, ast.With)
        for item in node.items
        if item.optional_vars and isinstance(item.optional_vars, ast.Name)
    ]

    unasserted = []
    for alias in aliases:
        found = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == alias
            and node.func.attr.startswith("assert_")
            for node in ast.walk(func_node)
        )
        if not found:
            unasserted.append(alias)
    return unasserted


def check_file(filepath: Path, diff_only: bool) -> list[tuple[int, str]]:
    """Return (lineno, message) tuples for each violation in filepath."""
    modified_lines = get_modified_line_ranges(filepath) if diff_only else None
    tree = ast.parse(filepath.read_text(encoding="utf-8"))
    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        if diff_only and modified_lines is not None and node.lineno not in modified_lines:
            continue
        if not has_assertion(node):
            violations.append((node.lineno, f"{node.name}: no assertions"))
        else:
            violations.extend(
                (node.lineno, f"{node.name}: named mock '{alias}' has no assert_* call")
                for alias in get_unasserted_named_mocks(node)
            )
    return violations


def main() -> int:
    """Entry point; returns 0 if clean, 1 if violations found."""
    diff_only = "--diff-only" in sys.argv
    files = get_staged_test_files()
    found_any = False
    for filepath in files:
        try:
            violations = check_file(filepath, diff_only=diff_only)
        except (SyntaxError, OSError):
            continue
        for lineno, message in violations:
            print(f"{filepath}:{lineno}: {message}")
            found_any = True
    return 1 if found_any else 0


if __name__ == "__main__":
    sys.exit(main())
