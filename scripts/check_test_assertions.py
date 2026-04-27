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

try:
    import jedi as _jedi  # type: ignore[import-untyped]
except ImportError:
    _jedi = None  # type: ignore[assignment]

_ASSERT_PREFIXES = ("assert_",)
_WEAK_ASSERT_MARKER = "# assert-not-weak"
_VALID_WEAK_ASSERT_MARKER = "# assert-not-weak: "


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

_MOCK_VERIFICATION_ATTRS: frozenset[str] = frozenset({
    "called",
    "call_count",
    "awaited",
    "await_count",
    "call_args",
    "call_args_list",
    "method_calls",
    "mock_calls",
})

_ALL_ANY_ATTRS: frozenset[str] = frozenset({
    "assert_called_once_with",
    "assert_awaited_once_with",
})


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


def _is_patch_call(context_expr: ast.expr) -> bool:
    """Return True if the context expression is patch(...) or patch.object(...)."""
    if not isinstance(context_expr, ast.Call):
        return False
    func = context_expr.func
    if isinstance(func, ast.Name):
        return func.id == "patch"
    if isinstance(func, ast.Attribute):
        return func.attr in ("patch", "object") and (
            (isinstance(func.value, ast.Name) and func.value.id in ("patch", "mock"))
            or (isinstance(func.value, ast.Attribute) and func.value.attr == "patch")
        )
    return False


def get_unasserted_named_mocks(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[str]:
    """Return names of patch(...)/patch.object(...) aliases that have no assert_* call."""
    aliases: list[str] = [
        item.optional_vars.id
        for node in ast.walk(func_node)
        if isinstance(node, ast.With)
        for item in node.items
        if item.optional_vars
        and isinstance(item.optional_vars, ast.Name)
        and _is_patch_call(item.context_expr)
    ]

    def _root_name(node: ast.expr) -> str | None:
        """Return the root Name id of an attribute chain, or None."""
        while isinstance(node, ast.Attribute):
            node = node.value
        return node.id if isinstance(node, ast.Name) else None

    unasserted = []
    for alias in aliases:
        has_assert_call = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr.startswith("assert_")
            and _root_name(node.func.value) == alias
            for node in ast.walk(func_node)
        )
        has_attr_verification = any(
            isinstance(node, ast.Attribute)
            and node.attr in _MOCK_VERIFICATION_ATTRS
            and isinstance(node.value, ast.Name)
            and node.value.id == alias
            for node in ast.walk(func_node)
        )
        if not (has_assert_call or has_attr_verification):
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


def _patch_target_from_item(item: ast.withitem) -> tuple[str, str] | None:
    """Return (alias, dotted_target) if item is `patch("target") as alias`, else None."""
    if not (item.optional_vars and isinstance(item.optional_vars, ast.Name)):
        return None
    expr = item.context_expr
    if not (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Name)
        and expr.func.id == "patch"
        and expr.args
        and isinstance(expr.args[0], ast.Constant)
    ):
        return None
    return item.optional_vars.id, expr.args[0].value


def _collect_patch_aliases(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> dict[str, str]:
    """Return {alias_name: dotted_patch_target} for all `with patch("target") as alias:` blocks."""
    result: dict[str, str] = {}
    for node in ast.walk(func_node):
        if not isinstance(node, ast.With):
            continue
        for item in node.items:
            pair = _patch_target_from_item(item)
            if pair is not None:
                result[pair[0]] = pair[1]
    return result


_PROJECT_ROOT = str(Path(__file__).parent.parent)


def _jedi_param_count(dotted_path: str) -> int | None:
    """Return non-self/cls param count for dotted_path via Jedi, or None if unavailable."""
    if _jedi is None:
        return None
    try:
        module_path, sep, name = dotted_path.rpartition(".")
        if not sep:
            return None
        source = f"from {module_path} import {name}\n{name}("
        script = _jedi.Script(source, project=_jedi.Project(path=_PROJECT_ROOT))
        sigs = script.get_signatures(2, len(name) + 1)
        if not sigs:
            return None
        return len([
            p
            for p in sigs[0].params
            if p.name not in ("self", "cls", "/", "*") and "=" not in p.description
        ])
    except Exception:
        return None


def _jedi_annotation_violation(
    lineno: int,
    root: str,
    patch_aliases: dict[str, str],
    func_name: str,
) -> tuple[int, str] | None:
    """Return a violation if the # assert-no-args annotation on root is incorrect."""
    patch_target = patch_aliases.get(root)
    if patch_target is None:
        return None
    param_count = _jedi_param_count(patch_target)
    if param_count is None or param_count == 0:
        return None
    short_name = patch_target.rsplit(".", 1)[-1]
    return (
        lineno,
        f"{func_name}: `{_VALID_WEAK_ASSERT_MARKER}<reason>` on `{root}` is wrong"
        f" — `{short_name}()` has {param_count} parameter(s); use"
        " assert_called_once_with(...)",
    )


def _marker_present(lineno: int, source_lines: list[str]) -> bool:
    """Return True if the weak-assert marker appears on lineno or the preceding line."""
    current = source_lines[lineno - 1] if lineno <= len(source_lines) else ""
    if _VALID_WEAK_ASSERT_MARKER in current:
        return True
    preceding = source_lines[lineno - 2] if lineno > 1 else ""
    return _VALID_WEAK_ASSERT_MARKER in preceding


def _is_weak_assert_exempt(method_name: str | None, lineno: int, source_lines: list[str]) -> bool:
    """Return True if this assert_called_once() should be exempted from the weak-assert check."""
    if method_name in _NO_ARG_METHODS:
        return True
    return _marker_present(lineno, source_lines)


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
            f"prefer assert_called_once_with(...) or add"
            f" '{_VALID_WEAK_ASSERT_MARKER}<reason>' if args are opaque"
        )
    else:
        suggestion = (
            f"add arguments or add '{_VALID_WEAK_ASSERT_MARKER}<reason>'"
            " if the function genuinely takes no args"
        )
    return (node.lineno, f"{func_name}: `{call_form}` — {suggestion}")


def _is_any_value(node: ast.expr) -> bool:
    """Return True if node is ANY (bare or attribute form like mock.ANY)."""
    if isinstance(node, ast.Name) and node.id == "ANY":
        return True
    return isinstance(node, ast.Attribute) and node.attr == "ANY"


def _is_all_any_call(node: ast.Call) -> bool:
    """Return True if node is assert_called_once_with or assert_awaited_once_with with all ANY args.

    Detects calls like assert_called_once_with(ANY, ANY) where every argument is ANY.
    """
    if not isinstance(node.func, ast.Attribute):
        return False
    if node.func.attr not in _ALL_ANY_ATTRS:
        return False
    if not node.args and not node.keywords:
        return False
    return all(_is_any_value(a) for a in node.args) and all(
        _is_any_value(kw.value) for kw in node.keywords
    )


def _is_weak_assert_call(node: ast.Call) -> bool:
    """Return True if node is assert_called_once() or assert_called_once_with() with no args."""
    if not isinstance(node.func, ast.Attribute):
        return False
    attr = node.func.attr
    return attr == "assert_called_once" or (
        attr == "assert_called_once_with" and not node.args and not node.keywords
    )


def _exempt_or_marker_violation(
    node: ast.Call,
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    patch_aliases: dict[str, str],
    source_lines: list[str],
) -> tuple[bool, tuple[int, str] | None]:
    """Return (should_skip, optional_violation) for a confirmed weak-assert node."""
    if not isinstance(node.func, ast.Attribute):
        return False, None
    receiver_dotted = _receiver_dotted_name(node.func.value)
    if receiver_dotted and _has_call_args_check(func_node, receiver_dotted):
        return True, None
    if receiver_dotted:
        patch_target = patch_aliases.get(receiver_dotted)
        if patch_target and patch_target.rsplit(".", 1)[-1] in _NO_ARG_METHODS:
            return True, None
    if not _marker_present(node.lineno, source_lines):
        return False, None
    if node.func.attr == "assert_called_once":
        return True, (
            node.lineno,
            f"{func_node.name}: `assert_called_once()  {_VALID_WEAK_ASSERT_MARKER}<reason>` —"
            " use `assert_called_once_with()` to verify no arguments were passed",
        )
    v = None
    if isinstance(node.func.value, ast.Name):
        v = _jedi_annotation_violation(
            node.lineno, node.func.value.id, patch_aliases, func_node.name
        )
    return True, v


def _dispatch_weak_assert(
    node: ast.Call,
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    patch_aliases: dict[str, str],
    source_lines: list[str],
) -> tuple[int, str] | None:
    """Return a violation for a confirmed weak-assert node, or None if exempt/clean."""
    skip, v = _exempt_or_marker_violation(node, func_node, patch_aliases, source_lines)
    if skip:
        return v
    return _weak_assert_violation(node, func_node.name, source_lines)


def _all_any_violation(
    node: ast.Call,
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    source_lines: list[str],
) -> tuple[int, str] | None:
    """Return a (lineno, message) violation if node is an all-ANY assert call not exempted."""
    if not isinstance(node.func, ast.Attribute):
        return None
    receiver_dotted = _receiver_dotted_name(node.func.value)
    if receiver_dotted and _has_call_args_check(func_node, receiver_dotted):
        return None
    if _marker_present(node.lineno, source_lines):
        return None
    method_name = _receiver_method_name(node)
    attr = node.func.attr
    call_form = f"{method_name}.{attr}(ALL ANY)" if method_name else f"{attr}(ALL ANY)"
    hint = f"`{_VALID_WEAK_ASSERT_MARKER}<reason>` if arguments are genuinely opaque"
    return (
        node.lineno,
        f"{func_node.name}: `{call_form}` — use concrete expected arguments or add {hint}",
    )


def get_weak_assert_violations(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    source_lines: list[str],
) -> list[tuple[int, str]]:
    """Return (lineno, message) for assert_called_once() calls that should be stronger.

    Flags:
    - assert_called_once() — no argument verification at all
    - assert_called_once_with() with no args — equivalent weakness
    - '# assert-not-weak: <reason>' on a call whose patch target has parameters (via Jedi)

    Exempts calls on known no-arg methods (flush, commit, etc.), any line
    carrying a '# assert-not-weak: <reason>' comment, and calls where the same receiver's
    .call_args or .call_args_list is accessed elsewhere in the same test.
    Also flags assert_called_once_with/assert_awaited_once_with where every argument is ANY.
    """
    patch_aliases = _collect_patch_aliases(func_node)
    violations = []
    for node in ast.walk(func_node):
        if not isinstance(node, ast.Call):
            continue
        if _is_weak_assert_call(node):
            v = _dispatch_weak_assert(node, func_node, patch_aliases, source_lines)
        elif _is_all_any_call(node):
            v = _all_any_violation(node, func_node, source_lines)
        else:
            continue
        if v is not None:
            violations.append(v)
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


def _patch_target_at_assert_call(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
    lineno: int,
) -> str | None:
    """Return the patch target for the first assert_called_once* on lineno, or None."""
    patch_aliases = _collect_patch_aliases(func_node)
    for call_node in ast.walk(func_node):
        if not isinstance(call_node, ast.Call):
            continue
        if call_node.lineno != lineno:
            continue
        if not isinstance(call_node.func, ast.Attribute):
            continue
        if call_node.func.attr not in ("assert_called_once", "assert_called_once_with"):
            continue
        if not isinstance(call_node.func.value, ast.Name):
            return None
        return patch_aliases.get(call_node.func.value.id)
    return None


def _has_assert_call_at_line(node: ast.FunctionDef | ast.AsyncFunctionDef, line: int) -> bool:
    """Return True if node contains an assert_called_once* call on the given line."""
    return any(
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr in ("assert_called_once", "assert_called_once_with")
        and call.lineno == line
        for call in ast.walk(node)
    )


def _resolve_assert_line(node: ast.FunctionDef | ast.AsyncFunctionDef, lineno: int) -> int | None:
    """Return the line of an assert_called_once* call at lineno or lineno+1, or None."""
    if _has_assert_call_at_line(node, lineno):
        return lineno
    if _has_assert_call_at_line(node, lineno + 1):
        return lineno + 1
    return None


def _jedi_verifies_no_args_at_line(source: str, lineno: int) -> bool:
    """Return True if Jedi confirms the patched function takes no args.

    Accepts the marker inline on the assertion line or on the preceding line
    (in which case lineno is the marker line and the assert is on lineno+1).
    Returns True when neither lineno nor lineno+1 has an assert_called_once*
    call — the marker is inside a string literal or other non-annotation context.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        end = getattr(node, "end_lineno", node.lineno)
        if not (node.lineno <= lineno <= end):
            continue
        assert_line = _resolve_assert_line(node, lineno)
        if assert_line is None:
            return True
        patch_target = _patch_target_at_assert_call(node, assert_line)
        if patch_target is None:
            return False
        param_count = _jedi_param_count(patch_target)
        return param_count is not None and param_count == 0
    return False


def _count_unverified_markers(pending: list[tuple[str, int]]) -> int:
    """Count markers from pending list that Jedi cannot confirm as correct."""
    count = 0
    for filepath, lineno in pending:
        try:
            source = Path(filepath).read_text(encoding="utf-8")
        except OSError:
            count += 1
            continue
        if not _jedi_verifies_no_args_at_line(source, lineno):
            count += 1
    return count


def _count_weak_assert_markers_in_staged_diff() -> int:
    """Count '# assert-not-weak' annotations added in staged diff that Jedi cannot verify."""
    git = shutil.which("git") or "git"
    result = subprocess.run(  # noqa: S603
        [git, "diff", "--cached", "-U0"],
        capture_output=True,
        text=True,
        check=False,
    )
    pending: list[tuple[str, int]] = []
    current_file = ""
    new_lineno = 0
    for line in result.stdout.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            new_lineno = 0
        elif line.startswith("@@"):
            parts = line.split("+")[1].split("@@")[0].strip()
            start, _, _ = parts.partition(",")
            new_lineno = int(start) - 1
        elif line.startswith("++"):
            pass
        elif line.startswith("+"):
            new_lineno += 1
            if current_file.endswith(".py") and _WEAK_ASSERT_MARKER in line:
                pending.append((current_file, new_lineno))
        elif not line.startswith("-"):
            new_lineno += 1
    return _count_unverified_markers(pending)


def _select_files(scan_all: bool, explicit_files: list[Path]) -> list[Path]:
    if explicit_files:
        return explicit_files
    if scan_all:
        return get_all_test_files()
    return get_staged_test_files()


def _check_marker_quota(scan_all: bool, explicit_files: list[Path]) -> bool:
    if scan_all or explicit_files:
        return False
    marker_count = _count_weak_assert_markers_in_staged_diff()
    approved = int(os.environ.get("APPROVED_WEAK_ASSERTIONS", "0"))
    if marker_count > approved:
        print(
            f"\nERROR: {marker_count} '{_WEAK_ASSERT_MARKER}'"
            " annotation(s) added in staged changes."
        )
        print(
            "Ask the user for explicit permission if justified after reading"
            " .github/instructions/quality-check-overrides.instructions.md"
        )
        return True
    return False


def main() -> int:
    """Entry point; returns 0 if clean, 1 if violations found."""
    scan_all = "--all" in sys.argv
    diff_only = "--diff-only" in sys.argv and not scan_all
    explicit_files = [Path(a) for a in sys.argv[1:] if not a.startswith("--")]
    files = _select_files(scan_all, explicit_files)
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

    marker_failed = _check_marker_quota(scan_all, explicit_files)
    return 1 if (counts or marker_failed) else 0


if __name__ == "__main__":
    sys.exit(main())
