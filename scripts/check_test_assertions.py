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
import os
import shutil
import subprocess  # noqa: S404 - Used safely with hardcoded args and shell=False
import sys
import tomllib
from pathlib import Path

_ASSERT_PREFIXES = ("assert_",)
_WEAK_ASSERT_MARKER = "# assert-no-args"


def _load_no_arg_methods() -> frozenset[str]:
    """Load no-arg-methods from pyproject.toml [tool.check-test-assertions], with fallback."""
    fallback = frozenset({"flush", "commit", "rollback", "close"})
    for parent in Path(__file__).parents:
        candidate = parent / "pyproject.toml"
        if candidate.exists():
            try:
                data = tomllib.loads(candidate.read_text(encoding="utf-8"))
                methods = (
                    data.get("tool", {}).get("check-test-assertions", {}).get("no-arg-methods")
                )
                if methods is not None:
                    return frozenset(methods)
            except (OSError, tomllib.TOMLDecodeError):
                pass
            break
    return fallback


_NO_ARG_METHODS = _load_no_arg_methods()


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


def get_all_test_files() -> list[Path]:
    """Return all test file paths under tests/."""
    return sorted(Path("tests").glob("**/*.py"))


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


def _is_pytest_raises(context_expr: ast.expr) -> bool:
    """Return True if the context expression is a pytest.raises(...) call."""
    return (
        isinstance(context_expr, ast.Call)
        and isinstance(context_expr.func, ast.Attribute)
        and isinstance(context_expr.func.value, ast.Name)
        and context_expr.func.value.id == "pytest"
        and context_expr.func.attr == "raises"
    )


def get_unasserted_named_mocks(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[str]:
    """Return names of 'with ... as <name>:' aliases that have no assert_* call.

    pytest.raises(...) as exc_info aliases are excluded — they are verified via
    exc_info.value attribute access, not assert_* method calls.
    """
    aliases: list[str] = [
        item.optional_vars.id
        for node in ast.walk(func_node)
        if isinstance(node, ast.With)
        for item in node.items
        if item.optional_vars
        and isinstance(item.optional_vars, ast.Name)
        and not _is_pytest_raises(item.context_expr)
    ]

    def _root_name(node: ast.expr) -> str | None:
        """Return the root Name id of an attribute chain, or None."""
        while isinstance(node, ast.Attribute):
            node = node.value
        return node.id if isinstance(node, ast.Name) else None

    unasserted = []
    for alias in aliases:
        found = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr.startswith("assert_")
            and _root_name(node.func.value) == alias
            for node in ast.walk(func_node)
        )
        if not found:
            unasserted.append(alias)
    return unasserted


def _receiver_method_name(call_node: ast.Call) -> str | None:
    """Return the method name of the receiver in a chained call, or None."""
    if not isinstance(call_node.func, ast.Attribute):
        return None
    receiver = call_node.func.value
    return receiver.attr if isinstance(receiver, ast.Attribute) else None


def _receiver_dotted_name(node: ast.expr) -> str | None:
    """Return the dotted name of a Name or Attribute chain, or None."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _receiver_dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent is not None else None
    return None


def _has_call_args_check(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    receiver_dotted: str,
) -> bool:
    """Return True if the function accesses .call_args or .call_args_list on receiver."""
    return any(
        isinstance(node, ast.Attribute)
        and node.attr in ("call_args", "call_args_list")
        and _receiver_dotted_name(node.value) == receiver_dotted
        for node in ast.walk(func_node)
    )


def _is_weak_assert_exempt(method_name: str | None, lineno: int, source_lines: list[str]) -> bool:
    """Return True if this assert_called_once() should be exempted from the weak-assert check."""
    if method_name in _NO_ARG_METHODS:
        return True
    line_text = source_lines[lineno - 1] if lineno <= len(source_lines) else ""
    return _WEAK_ASSERT_MARKER in line_text


def _weak_assert_violation(
    node: ast.Call,
    func_name: str,
    source_lines: list[str],
) -> tuple[int, str] | None:
    """Return a (lineno, message) violation if node is a weak assert_called_once* call."""
    if not isinstance(node.func, ast.Attribute):
        return None
    attr = node.func.attr
    is_bare = attr == "assert_called_once"
    is_empty_with = attr == "assert_called_once_with" and not node.args and not node.keywords
    if not (is_bare or is_empty_with):
        return None
    method_name = _receiver_method_name(node)
    if _is_weak_assert_exempt(method_name, node.lineno, source_lines):
        return None
    call_form = f"{method_name}.{attr}()" if method_name else f"{attr}()"
    if is_bare:
        suggestion = (
            f"prefer assert_called_once_with(...) or add '{_WEAK_ASSERT_MARKER}' if args are opaque"
        )
    else:
        suggestion = (
            f"add arguments or add '{_WEAK_ASSERT_MARKER}' if the function genuinely takes no args"
        )
    return (node.lineno, f"{func_name}: `{call_form}` — {suggestion}")


def get_weak_assert_violations(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    source_lines: list[str],
) -> list[tuple[int, str]]:
    """Return (lineno, message) for assert_called_once() calls that should be stronger.

    Flags:
    - assert_called_once() — no argument verification at all
    - assert_called_once_with() with no args — equivalent weakness

    Exempts calls on known no-arg methods (flush, commit, etc.), any line
    carrying a '# assert-no-args' comment, and calls where the same receiver's
    .call_args or .call_args_list is accessed elsewhere in the same test.
    """
    violations = []
    for node in ast.walk(func_node):
        if not isinstance(node, ast.Call):
            continue
        violation = _weak_assert_violation(node, func_node.name, source_lines)
        if violation is None:
            continue
        if isinstance(node.func, ast.Attribute):
            receiver_dotted = _receiver_dotted_name(node.func.value)
            if receiver_dotted and _has_call_args_check(func_node, receiver_dotted):
                continue
        violations.append(violation)
    return violations


def check_file(filepath: Path, diff_only: bool) -> list[tuple[int, str]]:
    """Return (lineno, message) tuples for each violation in filepath."""
    source = filepath.read_text(encoding="utf-8")
    source_lines = source.splitlines()
    modified_lines = get_modified_line_ranges(filepath) if diff_only else None
    tree = ast.parse(source)
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
            violations.extend(get_weak_assert_violations(node, source_lines))
    return violations


def _count_weak_assert_markers_in_staged_diff() -> int:
    """Count '# assert-no-args' occurrences added in the staged diff."""
    git = shutil.which("git") or "git"
    result = subprocess.run(  # noqa: S603
        [git, "diff", "--cached", "-U0"],
        capture_output=True,
        text=True,
        check=False,
    )
    current_file = ""
    count = 0
    for line in result.stdout.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif (
            line.startswith("+")
            and not line.startswith("++")
            and current_file.endswith(".py")
            and _WEAK_ASSERT_MARKER in line
        ):
            count += 1
    return count


def main() -> int:
    """Entry point; returns 0 if clean, 1 if violations found."""
    scan_all = "--all" in sys.argv
    diff_only = "--diff-only" in sys.argv and not scan_all
    files = get_all_test_files() if scan_all else get_staged_test_files()
    counts: dict[Path, int] = {}
    for filepath in files:
        try:
            violations = check_file(filepath, diff_only=diff_only)
        except (SyntaxError, OSError):
            continue
        for lineno, message in violations:
            print(f"{filepath}:{lineno}: {message}")
            counts[filepath] = counts.get(filepath, 0) + 1
    if counts:
        print("\nViolations by file (fix highest count first):")
        for path, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {count:>3}  {path}")
        print("\nSee docs/developer/fix-test-assertion-violations.md for fix patterns.")

    marker_failed = False
    if not scan_all:
        marker_count = _count_weak_assert_markers_in_staged_diff()
        approved = int(os.environ.get("APPROVED_WEAK_ASSERTIONS", "0"))
        if marker_count > approved:
            print(
                f"\nERROR: {marker_count} '{_WEAK_ASSERT_MARKER}'"
                " annotation(s) added in staged changes."
            )
            print(f"Set APPROVED_WEAK_ASSERTIONS={marker_count} to permit if justified.")
            print("See docs/developer/fix-test-assertion-violations.md for guidance.")
            marker_failed = True

    return 1 if (counts or marker_failed) else 0


if __name__ == "__main__":
    sys.exit(main())
