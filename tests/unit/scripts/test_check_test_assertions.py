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

_MARKER = check_test_assertions._WEAK_ASSERT_MARKER


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


def test_get_unasserted_named_mocks_chained_assert_recognized() -> None:
    source = (
        "def test_foo():\n"
        "    with patch('x') as mock_x:\n"
        "        fn()\n"
        "    mock_x.some_method.assert_called_once()\n"
    )
    func = _parse_func(source)
    result = check_test_assertions.get_unasserted_named_mocks(func)
    assert result == []


def test_has_assertion_recognizes_assert_not_awaited() -> None:
    source = (
        "def test_foo():\n"
        "    with patch('x') as mock_x:\n"
        "        fn()\n"
        "    mock_x.assert_not_awaited()\n"
    )
    func = _parse_func(source)
    assert check_test_assertions.has_assertion(func) is True
    assert check_test_assertions.get_unasserted_named_mocks(func) == []


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
            with mock.patch.object(
                check_test_assertions, "_count_weak_assert_markers_in_staged_diff", return_value=0
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
    mock_all.assert_called_once_with()  # assert-no-args: get_all_test_files takes no arguments
    mock_staged.assert_not_called()
    assert exit_code == 0


# ---------------------------------------------------------------------------
# get_weak_assert_violations
# ---------------------------------------------------------------------------


def test_get_weak_assert_violations_bare_assert_called_once_is_violation() -> None:
    source = "def test_foo():\n    mock_require.assert_called_once()\n"
    func = _parse_func(source)
    result = check_test_assertions.get_weak_assert_violations(func, source.splitlines())
    assert len(result) == 1
    assert "assert_called_once()" in result[0][1]


def test_get_weak_assert_violations_chained_method_name_in_message() -> None:
    source = "def test_foo():\n    mock_session.execute.assert_called_once()\n"
    func = _parse_func(source)
    result = check_test_assertions.get_weak_assert_violations(func, source.splitlines())
    assert len(result) == 1
    assert "execute.assert_called_once()" in result[0][1]


def test_get_weak_assert_violations_flush_is_exempt() -> None:
    source = "def test_foo():\n    mock_db.flush.assert_called_once()\n"
    func = _parse_func(source)
    result = check_test_assertions.get_weak_assert_violations(func, source.splitlines())
    assert result == []


def test_get_weak_assert_violations_commit_is_exempt() -> None:
    source = "def test_foo():\n    mock_db.commit.assert_called_once()\n"
    func = _parse_func(source)
    result = check_test_assertions.get_weak_assert_violations(func, source.splitlines())
    assert result == []


def test_get_weak_assert_violations_rollback_is_exempt() -> None:
    source = "def test_foo():\n    mock_db.rollback.assert_called_once()\n"
    func = _parse_func(source)
    result = check_test_assertions.get_weak_assert_violations(func, source.splitlines())
    assert result == []


def test_get_weak_assert_violations_close_is_exempt() -> None:
    source = "def test_foo():\n    mock_conn.close.assert_called_once()\n"
    func = _parse_func(source)
    result = check_test_assertions.get_weak_assert_violations(func, source.splitlines())
    assert result == []


def test_get_weak_assert_violations_inline_marker_exempts() -> None:
    source = f"def test_foo():\n    mock_get_config.assert_called_once_with()  {_MARKER}\n"
    func = _parse_func(source)
    result = check_test_assertions.get_weak_assert_violations(func, source.splitlines())
    assert result == []


def test_get_weak_assert_violations_assert_called_once_with_not_flagged() -> None:
    source = "def test_foo():\n    mock_require.assert_called_once_with(db, guild_id)\n"
    func = _parse_func(source)
    result = check_test_assertions.get_weak_assert_violations(func, source.splitlines())
    assert result == []


def test_get_weak_assert_violations_empty_assert_called_once_with_is_violation() -> None:
    source = "def test_foo():\n    mock_get_client.assert_called_once_with()\n"
    func = _parse_func(source)
    result = check_test_assertions.get_weak_assert_violations(func, source.splitlines())
    assert len(result) == 1
    assert "assert_called_once_with()" in result[0][1]


def test_get_weak_assert_violations_empty_with_marker_is_exempt() -> None:
    source = f"def test_foo():\n    mock_get_client.assert_called_once_with()  {_MARKER}\n"
    func = _parse_func(source)
    result = check_test_assertions.get_weak_assert_violations(func, source.splitlines())
    assert result == []


def test_get_weak_assert_violations_empty_with_on_flush_is_exempt() -> None:
    source = "def test_foo():\n    mock_db.flush.assert_called_once_with()\n"
    func = _parse_func(source)
    result = check_test_assertions.get_weak_assert_violations(func, source.splitlines())
    assert result == []


def test_get_weak_assert_violations_assert_not_called_not_flagged() -> None:
    source = "def test_foo():\n    mock_require.assert_not_called()\n"
    func = _parse_func(source)
    result = check_test_assertions.get_weak_assert_violations(func, source.splitlines())
    assert result == []


def test_get_weak_assert_violations_call_args_access_exempts() -> None:
    source = (
        "def test_foo():\n"
        "    embed.add_field.assert_called_once()\n"
        "    call_kwargs = embed.add_field.call_args[1]\n"
        "    assert call_kwargs['name'] == 'Links'\n"
    )
    func = _parse_func(source)
    result = check_test_assertions.get_weak_assert_violations(func, source.splitlines())
    assert result == []


def test_get_weak_assert_violations_call_args_list_access_exempts() -> None:
    source = (
        "def test_foo():\n"
        "    embed.add_field.assert_called_once()\n"
        "    calls = embed.add_field.call_args_list\n"
        "    assert len(calls) == 1\n"
    )
    func = _parse_func(source)
    result = check_test_assertions.get_weak_assert_violations(func, source.splitlines())
    assert result == []


def test_get_weak_assert_violations_call_args_on_different_receiver_does_not_exempt() -> None:
    source = (
        "def test_foo():\n"
        "    embed.add_field.assert_called_once()\n"
        "    call_kwargs = embed.set_footer.call_args[1]\n"
        "    assert call_kwargs['text'] == 'Status: Scheduled'\n"
    )
    func = _parse_func(source)
    result = check_test_assertions.get_weak_assert_violations(func, source.splitlines())
    assert len(result) == 1


def test_get_weak_assert_violations_jedi_validates_no_arg_annotation_is_correct() -> None:
    source = (
        "def test_foo():\n"
        f"    with patch('services.bot.formatters.game_message.get_config') as mock_config:\n"
        f"        mock_config.assert_called_once_with()  {_MARKER}\n"
    )
    func = _parse_func(source)
    result = check_test_assertions.get_weak_assert_violations(func, source.splitlines())
    assert result == []


def test_get_weak_assert_violations_jedi_flags_wrong_no_arg_annotation() -> None:
    source = (
        "def test_foo():\n"
        "    with patch("
        "'services.bot.formatters.game_message.format_game_announcement') as mock_fmt:\n"
        f"        mock_fmt.assert_called_once_with()  {_MARKER}\n"
    )
    func = _parse_func(source)
    result = check_test_assertions.get_weak_assert_violations(func, source.splitlines())
    assert len(result) == 1
    assert "assert-no-args" in result[0][1]
    assert "parameter" in result[0][1]


# ---------------------------------------------------------------------------
# check_file — weak assertion integration
# ---------------------------------------------------------------------------


def test_check_file_weak_assert_called_once_reports_violation(tmp_path: Path) -> None:
    test_file = tmp_path / "test_example.py"
    test_file.write_text("def test_foo():\n    mock_require.assert_called_once()\n")
    violations = check_test_assertions.check_file(test_file, diff_only=False)
    assert len(violations) == 1
    assert "assert_called_once()" in violations[0][1]


def test_check_file_weak_assert_with_marker_is_clean(tmp_path: Path) -> None:
    test_file = tmp_path / "test_example.py"
    test_file.write_text(
        f"def test_foo():\n    mock_get_config.assert_called_once_with()  {_MARKER}\n"
    )
    violations = check_test_assertions.check_file(test_file, diff_only=False)
    assert violations == []


def test_check_file_no_arg_method_is_clean(tmp_path: Path) -> None:
    test_file = tmp_path / "test_example.py"
    test_file.write_text("def test_foo():\n    mock_db.flush.assert_called_once()\n")
    violations = check_test_assertions.check_file(test_file, diff_only=False)
    assert violations == []


# ---------------------------------------------------------------------------
# _load_no_arg_methods
# ---------------------------------------------------------------------------


def test_load_no_arg_methods_reads_from_pyproject_toml(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.check-test-assertions]\nno-arg-methods = ["send", "recv"]\n'
    )
    script_path = tmp_path / "scripts" / "check.py"
    script_path.parent.mkdir()
    with mock.patch.object(check_test_assertions, "__file__", str(script_path)):
        loaded = check_test_assertions._load_no_arg_methods()
    assert loaded == frozenset({"send", "recv"})


def test_load_no_arg_methods_falls_back_when_section_absent(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.other]\nkey = 1\n")
    script_path = tmp_path / "scripts" / "check.py"
    script_path.parent.mkdir()
    with mock.patch.object(check_test_assertions, "__file__", str(script_path)):
        loaded = check_test_assertions._load_no_arg_methods()
    assert "flush" in loaded
    assert "commit" in loaded


def test_load_no_arg_methods_falls_back_when_no_pyproject_toml(tmp_path: Path) -> None:
    script_path = tmp_path / "scripts" / "check.py"
    script_path.parent.mkdir()
    with mock.patch.object(check_test_assertions, "__file__", str(script_path)):
        loaded = check_test_assertions._load_no_arg_methods()
    assert loaded == frozenset({"flush", "commit", "rollback", "close"})


# ---------------------------------------------------------------------------
# _count_weak_assert_markers_in_staged_diff
# ---------------------------------------------------------------------------


def test_count_weak_assert_markers_counts_added_lines() -> None:
    diff = (
        "+++ b/tests/test_foo.py\n"
        f"+    mock_x.assert_called_once()  {_MARKER}\n"
        f"+    mock_y.assert_called_once()  {_MARKER}: reason\n"
        " context line\n"
        f"-    old_line  {_MARKER}\n"
    )
    mock_result = mock.Mock(stdout=diff)
    with mock.patch.object(check_test_assertions.subprocess, "run", return_value=mock_result):
        count = check_test_assertions._count_weak_assert_markers_in_staged_diff()
    assert count == 2


def test_count_weak_assert_markers_ignores_non_python_files() -> None:
    diff = (
        "+++ b/docs/developer/fix-guide.md\n"
        f"+mock_x.assert_called_once()  {_MARKER}\n"
        "+++ b/tests/test_foo.py\n"
        f"+    mock_z.assert_called_once()  {_MARKER}\n"
    )
    mock_result = mock.Mock(stdout=diff)
    with mock.patch.object(check_test_assertions.subprocess, "run", return_value=mock_result):
        count = check_test_assertions._count_weak_assert_markers_in_staged_diff()
    assert count == 1


def test_count_weak_assert_markers_empty_diff_returns_zero() -> None:
    mock_result = mock.Mock(stdout="")
    with mock.patch.object(check_test_assertions.subprocess, "run", return_value=mock_result):
        count = check_test_assertions._count_weak_assert_markers_in_staged_diff()
    assert count == 0


# ---------------------------------------------------------------------------
# _jedi_verifies_no_args_at_line
# ---------------------------------------------------------------------------


def test_get_weak_assert_violations_bare_assert_called_once_with_marker_is_violation() -> None:
    source = f"def test_foo():\n    mock_cfg.assert_called_once()  {_MARKER}\n    assert True\n"
    func = _parse_func(source)
    result = check_test_assertions.get_weak_assert_violations(func, source.splitlines())
    assert len(result) == 1
    assert "assert_called_once_with()" in result[0][1]


def test_jedi_verifies_no_args_at_line_true_for_no_arg_patch_target() -> None:
    source = (
        "def test_foo():\n"
        "    with patch('services.bot.formatters.game_message.get_config') as mock_cfg:\n"
        f"        mock_cfg.assert_called_once_with()  {_MARKER}\n"
    )
    assert check_test_assertions._jedi_verifies_no_args_at_line(source, 3) is True


def test_jedi_verifies_no_args_at_line_false_for_function_with_args() -> None:
    source = (
        "def test_foo():\n"
        "    with patch('services.bot.formatters.game_message.format_game_announcement')"
        " as mock_fmt:\n"
        f"        mock_fmt.assert_called_once_with()  {_MARKER}\n"
    )
    assert check_test_assertions._jedi_verifies_no_args_at_line(source, 3) is False


def test_jedi_verifies_no_args_at_line_false_when_no_patch_alias() -> None:
    source = (
        "def test_foo():\n"
        "    mock_cfg = MagicMock()\n"
        f"    mock_cfg.assert_called_once_with()  {_MARKER}\n"
    )
    assert check_test_assertions._jedi_verifies_no_args_at_line(source, 3) is False


def test_jedi_verifies_no_args_at_line_true_when_marker_inside_string_literal() -> None:
    source = (
        "def test_foo():\n"
        "    assert True\n"
        f'    source = "mock_x.assert_called_once_with()  {_MARKER}\\n"\n'
    )
    assert check_test_assertions._jedi_verifies_no_args_at_line(source, 3) is True


def test_count_weak_assert_markers_jedi_verified_not_counted() -> None:
    source = (
        "def test_foo():\n"
        "    with patch('services.bot.formatters.game_message.get_config') as mock_cfg:\n"
        f"        mock_cfg.assert_called_once_with()  {_MARKER}\n"
    )
    diff = (
        "+++ b/tests/test_foo.py\n"
        "@@ -0,0 +1,3 @@\n"
        "+def test_foo():\n"
        "+    with patch('services.bot.formatters.game_message.get_config') as mock_cfg:\n"
        f"+        mock_cfg.assert_called_once_with()  {_MARKER}\n"
    )
    mock_result = mock.Mock(stdout=diff)
    with (
        mock.patch.object(check_test_assertions.subprocess, "run", return_value=mock_result),
        mock.patch("pathlib.Path.read_text", return_value=source),
    ):
        count = check_test_assertions._count_weak_assert_markers_in_staged_diff()
    assert count == 0


def test_count_weak_assert_markers_unresolvable_patch_target_is_counted() -> None:
    source = (
        "def test_foo():\n"
        "    with patch('some.unresolvable.module.SomeClass') as mock_cls:\n"
        f"        mock_cls.assert_called_once_with()  {_MARKER}\n"
    )
    diff = (
        "+++ b/tests/test_foo.py\n"
        "@@ -0,0 +1,3 @@\n"
        "+def test_foo():\n"
        "+    with patch('some.unresolvable.module.SomeClass') as mock_cls:\n"
        f"+        mock_cls.assert_called_once_with()  {_MARKER}\n"
    )
    mock_result = mock.Mock(stdout=diff)
    with (
        mock.patch.object(check_test_assertions.subprocess, "run", return_value=mock_result),
        mock.patch("pathlib.Path.read_text", return_value=source),
    ):
        count = check_test_assertions._count_weak_assert_markers_in_staged_diff()
    assert count == 1


# ---------------------------------------------------------------------------
# main — APPROVED_WEAK_ASSERTIONS gate
# ---------------------------------------------------------------------------


def test_main_gate_blocks_when_marker_count_exceeds_approved(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "test_ok.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    assert True\n")

    with mock.patch.object(
        check_test_assertions, "get_staged_test_files", return_value=[test_file]
    ):
        with mock.patch.object(
            check_test_assertions, "_count_weak_assert_markers_in_staged_diff", return_value=3
        ):
            with mock.patch.dict("os.environ", {"APPROVED_WEAK_ASSERTIONS": "0"}, clear=False):
                with mock.patch.object(sys, "argv", ["check_test_assertions.py"]):
                    exit_code = check_test_assertions.main()
    assert exit_code == 1


def test_main_gate_passes_when_marker_count_equals_approved(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "test_ok.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    assert True\n")

    with mock.patch.object(
        check_test_assertions, "get_staged_test_files", return_value=[test_file]
    ):
        with mock.patch.object(
            check_test_assertions, "_count_weak_assert_markers_in_staged_diff", return_value=2
        ):
            with mock.patch.dict("os.environ", {"APPROVED_WEAK_ASSERTIONS": "2"}, clear=False):
                with mock.patch.object(sys, "argv", ["check_test_assertions.py"]):
                    exit_code = check_test_assertions.main()
    assert exit_code == 0


def test_main_gate_skipped_in_scan_all_mode(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "test_ok.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_ok():\n    assert True\n")

    with mock.patch.object(check_test_assertions, "get_all_test_files", return_value=[test_file]):
        with mock.patch.object(
            check_test_assertions, "_count_weak_assert_markers_in_staged_diff"
        ) as mock_count:
            with mock.patch.object(sys, "argv", ["check_test_assertions.py", "--all"]):
                exit_code = check_test_assertions.main()
    mock_count.assert_not_called()
    assert exit_code == 0


def test_main_explicit_files_scans_given_files(tmp_path: Path) -> None:
    test_file = tmp_path / "test_explicit.py"
    test_file.write_text("def test_ok():\n    assert True\n")

    with mock.patch.object(
        check_test_assertions, "_count_weak_assert_markers_in_staged_diff"
    ) as mock_count:
        with mock.patch.object(sys, "argv", ["check_test_assertions.py", str(test_file)]):
            exit_code = check_test_assertions.main()
    mock_count.assert_not_called()
    assert exit_code == 0


def test_main_explicit_files_reports_violations(tmp_path: Path) -> None:
    test_file = tmp_path / "test_bad.py"
    test_file.write_text("def test_missing():\n    pass\n")

    with mock.patch.object(sys, "argv", ["check_test_assertions.py", str(test_file)]):
        exit_code = check_test_assertions.main()
    assert exit_code == 1
