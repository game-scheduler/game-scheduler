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


"""Unit tests for scripts/check_test_assertions.py."""

import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest import mock

_SCRIPT_PATH = Path(__file__).parent.parent.parent.parent / "scripts" / "check_test_assertions.py"
_spec = importlib.util.spec_from_file_location("check_test_assertions", _SCRIPT_PATH)
_mod: ModuleType = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

check_test_assertions = _mod


def _parse_func(source: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node
    msg = "No function found in source"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# has_assertion
# ---------------------------------------------------------------------------


def test_has_assertion_with_assert_statement() -> None:
    source = "def test_foo():\n    assert x == 1\n"
    func = _parse_func(source)
    assert check_test_assertions.has_assertion(func) is True


def test_has_assertion_with_assert_called_once_with() -> None:
    source = "def test_foo():\n    mock_obj.assert_called_once_with(42)\n"
    func = _parse_func(source)
    assert check_test_assertions.has_assertion(func) is True


def test_has_assertion_with_assert_awaited_once() -> None:
    source = "def test_foo():\n    mock_obj.assert_awaited_once()\n"
    func = _parse_func(source)
    assert check_test_assertions.has_assertion(func) is True


def test_has_assertion_with_pytest_raises() -> None:
    source = "def test_foo():\n    with pytest.raises(ValueError):\n        fn()\n"
    func = _parse_func(source)
    assert check_test_assertions.has_assertion(func) is True


def test_has_assertion_with_no_assertion_returns_false() -> None:
    source = "def test_foo():\n    result = fn()\n"
    func = _parse_func(source)
    assert check_test_assertions.has_assertion(func) is False


# ---------------------------------------------------------------------------
# get_unasserted_named_mocks
# ---------------------------------------------------------------------------


def test_get_unasserted_named_mocks_unverified_alias() -> None:
    source = "def test_foo():\n    with patch('x') as mock_x:\n        fn()\n"
    func = _parse_func(source)
    result = check_test_assertions.get_unasserted_named_mocks(func)
    assert result == ["mock_x"]


def test_get_unasserted_named_mocks_verified_alias_returns_empty() -> None:
    source = (
        "def test_foo():\n"
        "    with patch('x') as mock_x:\n"
        "        fn()\n"
        "    mock_x.assert_called_once()\n"
    )
    func = _parse_func(source)
    result = check_test_assertions.get_unasserted_named_mocks(func)
    assert result == []


def test_get_unasserted_named_mocks_no_with_returns_empty() -> None:
    source = "def test_foo():\n    fn()\n"
    func = _parse_func(source)
    result = check_test_assertions.get_unasserted_named_mocks(func)
    assert result == []


def test_get_unasserted_named_mocks_pytest_raises_alias_excluded() -> None:
    source = (
        "def test_foo():\n"
        "    with pytest.raises(ValueError) as exc_info:\n"
        "        fn()\n"
        "    assert exc_info.value.args[0] == 'bad'\n"
    )
    func = _parse_func(source)
    result = check_test_assertions.get_unasserted_named_mocks(func)
    assert result == []


def test_get_unasserted_named_mocks_pytest_raises_excluded_patch_still_checked() -> None:
    source = (
        "def test_foo():\n"
        "    with patch('x') as mock_x, pytest.raises(ValueError) as exc_info:\n"
        "        fn()\n"
        "    assert exc_info.value.args[0] == 'bad'\n"
    )
    func = _parse_func(source)
    result = check_test_assertions.get_unasserted_named_mocks(func)
    assert result == ["mock_x"]


# ---------------------------------------------------------------------------
# check_file
# ---------------------------------------------------------------------------


def test_check_file_full_mode_no_assertions_reports_violation(tmp_path: Path) -> None:
    test_file = tmp_path / "test_example.py"
    test_file.write_text("def test_foo():\n    result = fn()\n")
    violations = check_test_assertions.check_file(test_file, diff_only=False)
    assert len(violations) == 1
    lineno, message = violations[0]
    assert lineno == 1
    assert "test_foo" in message


def test_check_file_full_mode_with_assertion_returns_empty(tmp_path: Path) -> None:
    test_file = tmp_path / "test_example.py"
    test_file.write_text("def test_foo():\n    assert True\n")
    violations = check_test_assertions.check_file(test_file, diff_only=False)
    assert violations == []


def test_check_file_diff_only_skips_function_outside_diff(tmp_path: Path) -> None:
    test_file = tmp_path / "test_example.py"
    test_file.write_text("def test_foo():\n    result = fn()\n")
    with mock.patch.object(check_test_assertions, "get_modified_line_ranges", return_value=set()):
        violations = check_test_assertions.check_file(test_file, diff_only=True)
    assert violations == []


def test_check_file_diff_only_reports_function_in_diff(tmp_path: Path) -> None:
    test_file = tmp_path / "test_example.py"
    test_file.write_text("def test_foo():\n    result = fn()\n")
    with mock.patch.object(check_test_assertions, "get_modified_line_ranges", return_value={1}):
        violations = check_test_assertions.check_file(test_file, diff_only=True)
    assert len(violations) == 1


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def test_main_clean_file_exits_zero(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "test_clean.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    assert True\n")

    staged_output = "tests/test_clean.py\n"
    mock_result = mock.Mock(stdout=staged_output)

    with mock.patch.object(check_test_assertions.subprocess, "run", return_value=mock_result):
        with mock.patch.object(
            check_test_assertions, "get_staged_test_files", return_value=[test_file]
        ):
            with mock.patch.object(sys, "argv", ["check_test_assertions.py"]):
                exit_code = check_test_assertions.main()
    assert exit_code == 0


def test_main_file_with_no_assertion_exits_one(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "test_bad.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_missing():\n    fn()\n")

    with mock.patch.object(
        check_test_assertions, "get_staged_test_files", return_value=[test_file]
    ):
        with mock.patch.object(sys, "argv", ["check_test_assertions.py"]):
            exit_code = check_test_assertions.main()
    assert exit_code == 1


def test_main_diff_only_function_outside_diff_exits_zero(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "test_outside.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_missing():\n    fn()\n")

    with mock.patch.object(
        check_test_assertions, "get_staged_test_files", return_value=[test_file]
    ):
        with mock.patch.object(
            check_test_assertions, "get_modified_line_ranges", return_value=set()
        ):
            with mock.patch.object(sys, "argv", ["check_test_assertions.py", "--diff-only"]):
                exit_code = check_test_assertions.main()
    assert exit_code == 0


# ---------------------------------------------------------------------------
# get_all_test_files
# ---------------------------------------------------------------------------


def test_get_all_test_files_returns_sorted_python_files() -> None:
    mock_files = [Path("tests/test_b.py"), Path("tests/test_a.py")]
    with mock.patch.object(Path, "glob", return_value=iter(mock_files)):
        result = check_test_assertions.get_all_test_files()
    assert result == sorted(mock_files)


def test_main_all_flag_uses_get_all_test_files(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "test_all.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    assert True\n")

    with mock.patch.object(
        check_test_assertions, "get_all_test_files", return_value=[test_file]
    ) as mock_all:
        with mock.patch.object(check_test_assertions, "get_staged_test_files") as mock_staged:
            with mock.patch.object(sys, "argv", ["check_test_assertions.py", "--all"]):
                exit_code = check_test_assertions.main()
    mock_all.assert_called_once()
    mock_staged.assert_not_called()
    assert exit_code == 0
