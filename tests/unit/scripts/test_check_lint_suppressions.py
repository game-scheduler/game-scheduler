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


"""Unit tests for scripts/check_lint_suppressions.py."""

import importlib.util
import io
import os
import sys
from pathlib import Path
from types import ModuleType
from unittest import mock

import pytest

_SCRIPT_PATH = Path(__file__).parent.parent.parent.parent / "scripts" / "check_lint_suppressions.py"
_spec = importlib.util.spec_from_file_location("check_lint_suppressions", _SCRIPT_PATH)
_mod: ModuleType = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

check_lint_suppressions = _mod


def _make_added_diff(filename: str, *added_lines: str, start_line: int = 1) -> str:
    """Build a minimal staged diff with only added lines."""
    count = len(added_lines)
    hunk = f"@@ -0,0 +{start_line},{count} @@"
    body = "\n".join(f"+{line}" for line in added_lines)
    return f"+++ b/{filename}\n{hunk}\n{body}\n"


def _run_main(diff: str, approved_overrides: str | None = None) -> tuple[int, str]:
    """Run main() with a mocked diff and return (exit_code, stdout)."""
    mock_result = mock.Mock(stdout=diff)

    if approved_overrides is not None:
        env_patch = {"APPROVED_OVERRIDES": approved_overrides}
        clear = False
    else:
        env_patch = {k: v for k, v in os.environ.items() if k != "APPROVED_OVERRIDES"}
        clear = True

    stdout_buf = io.StringIO()
    with mock.patch.object(check_lint_suppressions.subprocess, "run", return_value=mock_result):
        with mock.patch.dict(os.environ, env_patch, clear=clear):
            with mock.patch.object(sys, "argv", ["check_lint_suppressions.py"]):
                with mock.patch("sys.stdout", stdout_buf):
                    try:
                        check_lint_suppressions.main()
                        return 0, stdout_buf.getvalue()
                    except SystemExit as exc:
                        code = exc.code if isinstance(exc.code, int) else 1
                        return code, stdout_buf.getvalue()


def test_clean_diff_exits_zero():
    diff = _make_added_diff("clean.py", "x = 1")
    code, _ = _run_main(diff)
    assert code == 0


@pytest.mark.parametrize(
    ("line", "label"),
    [
        ("x = 1  # noqa", "bare noqa"),
        ("# ruff: noqa", "ruff file noqa"),
        ("x: int = value  # type: ignore", "bare type ignore"),
        ("#lizard forgive global", "lizard forgive global"),
        ("// @ts-ignore", "ts-ignore"),
        ("// eslint-disable", "eslint-disable bare"),
        ("/* eslint-disable */", "eslint-disable block"),
    ],
)
def test_blocked_pattern_exits_nonzero(line, label):
    diff = _make_added_diff("file.py", line)
    code, out = _run_main(diff)
    assert code != 0, f"Expected nonzero exit for {label}"
    assert "file.py:1:" in out, f"Expected file:line in output for {label}"


@pytest.mark.parametrize(
    ("line", "label"),
    [
        ("x = 1  # noqa", "bare noqa"),
        ("# ruff: noqa", "ruff file noqa"),
        ("x: int = value  # type: ignore", "bare type ignore"),
        ("#lizard forgive global", "lizard forgive global"),
        ("// @ts-ignore", "ts-ignore"),
        ("// eslint-disable", "eslint-disable bare"),
        ("/* eslint-disable */", "eslint-disable block"),
    ],
)
def test_blocked_pattern_output_references_instructions(line, label):
    diff = _make_added_diff("file.py", line)
    _, out = _run_main(diff)
    instructions = "quality-check-overrides.instructions.md"
    assert instructions in out, f"Expected instructions ref for {label}"


@pytest.mark.parametrize(
    ("line", "label"),
    [
        ("x = 1  # noqa: E501", "specific noqa code"),
        ("x = y  # type: ignore[attr-defined]", "specific type ignore"),
        ("#lizard forgives", "lizard forgives bare"),
        ("// @ts-expect-error", "ts-expect-error"),
        ("// eslint-disable-next-line no-console", "eslint-disable-next-line specific"),
    ],
)
def test_counted_pattern_fails_without_approval(line, label):
    diff = _make_added_diff("file.py", line)
    code, out = _run_main(diff, approved_overrides=None)
    assert code != 0, f"Expected nonzero exit for {label} with no approval"
    assert "quality-check-overrides.instructions.md" in out


@pytest.mark.parametrize(
    ("line", "label"),
    [
        ("x = 1  # noqa: E501", "specific noqa code"),
        ("x = y  # type: ignore[attr-defined]", "specific type ignore"),
        ("#lizard forgives", "lizard forgives bare"),
        ("// @ts-expect-error", "ts-expect-error"),
        ("// eslint-disable-next-line no-console", "eslint-disable-next-line specific"),
    ],
)
def test_counted_pattern_passes_with_approval(line, label):
    diff = _make_added_diff("file.py", line)
    code, _ = _run_main(diff, approved_overrides="1")
    assert code == 0, f"Expected zero exit for {label} with APPROVED_OVERRIDES=1"


def test_approved_overrides_1_does_not_permit_bare_noqa():
    diff = _make_added_diff("file.py", "x = 1  # noqa")
    code, out = _run_main(diff, approved_overrides="1")
    assert code != 0
    assert "file.py:1:" in out


def test_removal_lines_are_not_scanned():
    diff = "+++ b/file.py\n@@ -1,1 +0,0 @@\n-x = 1  # noqa\n"
    code, _ = _run_main(diff)
    assert code == 0


def test_plus_plus_plus_header_not_scanned():
    diff = "+++ b/file.py\n@@ -0,0 +1,1 @@\n+x = 1\n"
    code, _ = _run_main(diff)
    assert code == 0


def test_mixed_bare_and_counted_fails_on_bare():
    diff = _make_added_diff(
        "file.py",
        "x = 1  # noqa",
        "y = 2  # noqa: E501",
    )
    code, out = _run_main(diff, approved_overrides="1")
    assert code != 0
    assert "file.py:1:" in out


# ---------------------------------------------------------------------------
# Task 1.4 edge case tests (REFACTOR phase — no xfail)
# ---------------------------------------------------------------------------


def test_approved_overrides_2_allows_two_counted():
    diff = _make_added_diff(
        "file.py",
        "x = 1  # noqa: E501",
        "y = 2  # noqa: E501",
    )
    code, _ = _run_main(diff, approved_overrides="2")
    assert code == 0


def test_approved_overrides_2_blocks_three_counted():
    diff = _make_added_diff(
        "file.py",
        "x = 1  # noqa: E501",
        "y = 2  # noqa: E501",
        "z = 3  # noqa: E501",
    )
    code, out = _run_main(diff, approved_overrides="2")
    assert code != 0
    assert "quality-check-overrides.instructions.md" in out


def test_lizard_forgives_with_metric_is_counted():
    diff = _make_added_diff("file.py", "#lizard forgives(length)")
    code, _ = _run_main(diff, approved_overrides="1")
    assert code == 0


def test_line_matching_blocked_and_counted_is_treated_as_blocked():
    # A line with both a bare noqa (blocked) and a specific noqa (counted).
    # The blocked phase runs first and exits, so the counted phase is never reached.
    diff = _make_added_diff("file.py", "x = 1  # noqa  # noqa: E501")
    code, out = _run_main(diff, approved_overrides="1")
    assert code != 0
    assert "Bare/blanket" in out
    assert "file.py:1:" in out


# ---------------------------------------------------------------------------
# Task 1.3 tests: --compare-branch and --ci  (must fail before Task 1.4)
# ---------------------------------------------------------------------------


def _run_main_with_args(diff: str, argv: list[str]) -> tuple[int, str]:
    """Run main() with explicit sys.argv and a mocked diff; return (exit_code, stdout)."""
    mock_result = mock.Mock(stdout=diff)
    captured = io.StringIO()
    with mock.patch.object(check_lint_suppressions.subprocess, "run", return_value=mock_result):
        with mock.patch.object(sys, "argv", ["check_lint_suppressions.py", *argv]):
            with mock.patch("sys.stdout", captured):
                try:
                    check_lint_suppressions.main()
                    return 0, captured.getvalue()
                except SystemExit as exc:
                    code = exc.code if isinstance(exc.code, int) else 1
                    return code, captured.getvalue()


def test_get_added_lines_with_compare_branch_uses_three_dot_diff():
    """_get_added_lines(compare_branch=...) invokes git diff <branch>...HEAD, not --cached."""
    diff = _make_added_diff("services/api/main.py", "x = 1")
    mock_result = mock.Mock(stdout=diff)

    with mock.patch.object(
        check_lint_suppressions.subprocess, "run", return_value=mock_result
    ) as mock_run:
        check_lint_suppressions._get_added_lines(compare_branch="origin/main")

    args = mock_run.call_args[0][0]
    assert "origin/main...HEAD" in args
    assert "--cached" not in args
    assert "--unified=0" in args


def test_get_added_lines_without_compare_branch_uses_cached():
    """_get_added_lines() without compare_branch uses --cached (pre-commit behaviour)."""
    diff = _make_added_diff("services/api/main.py", "x = 1")
    mock_result = mock.Mock(stdout=diff)

    with mock.patch.object(
        check_lint_suppressions.subprocess, "run", return_value=mock_result
    ) as mock_run:
        check_lint_suppressions._get_added_lines()

    args = mock_run.call_args[0][0]
    assert "--cached" in args
    assert "--unified=0" in args


def test_ci_flag_counted_pattern_exits_zero_and_outputs_count():
    """With --ci and a COUNTED suppression, exits 0 and prints SUPPRESSION_COUNT=1 to stdout."""
    diff = _make_added_diff("services/api/main.py", "x = 1  # noqa: E501")
    exit_code, stdout = _run_main_with_args(diff, ["--ci"])
    assert exit_code == 0
    assert "SUPPRESSION_COUNT=1" in stdout


def test_ci_flag_zero_suppressions_outputs_zero_count():
    """With --ci and no suppressions, exits 0 and prints SUPPRESSION_COUNT=0."""
    diff = _make_added_diff("services/api/main.py", "x = 1")
    exit_code, stdout = _run_main_with_args(diff, ["--ci"])
    assert exit_code == 0
    assert "SUPPRESSION_COUNT=0" in stdout


def test_ci_flag_counted_multiple_suppressions_accurate_count():
    """With --ci and multiple COUNTED suppressions, SUPPRESSION_COUNT reflects all of them."""
    diff = _make_added_diff(
        "services/api/main.py",
        "x = 1  # noqa: E501",
        "y = 2  # noqa: W503",
        "z: int = 3  # type: ignore[assignment]",
    )
    exit_code, stdout = _run_main_with_args(diff, ["--ci"])
    assert exit_code == 0
    assert "SUPPRESSION_COUNT=3" in stdout


def test_no_ci_flag_counted_pattern_exits_nonzero():
    """Without --ci, a COUNTED suppression causes non-zero exit (pre-commit behaviour unchanged)."""
    diff = _make_added_diff("services/api/main.py", "x = 1  # noqa: E501")
    exit_code, _stdout = _run_main_with_args(diff, [])
    assert exit_code != 0


def test_blocked_pattern_exits_one_with_ci_flag():
    """BLOCKED bare suppression exits 1 even when --ci is passed."""
    diff = _make_added_diff("services/api/main.py", "x = 1  # noqa")
    exit_code, _stdout = _run_main_with_args(diff, ["--ci"])
    assert exit_code == 1


def test_ts_ignore_blocked_exits_one_with_ci():
    """TypeScript @ts-ignore (BLOCKED) exits 1 even with --ci."""
    diff = _make_added_diff("frontend/src/foo.ts", "  // @ts-ignore")
    exit_code, _stdout = _run_main_with_args(diff, ["--ci"])
    assert exit_code == 1


def test_compare_branch_arg_forwarded_to_diff():
    """--compare-branch <ref> causes git diff to use <ref>...HEAD instead of --cached."""
    diff = _make_added_diff("services/api/main.py", "x = 1")
    mock_result = mock.Mock(stdout=diff)

    with mock.patch.object(
        check_lint_suppressions.subprocess, "run", return_value=mock_result
    ) as mock_run:
        with mock.patch.object(
            sys, "argv", ["check_lint_suppressions.py", "--compare-branch", "origin/main"]
        ):
            with mock.patch("sys.stdout", io.StringIO()):
                try:
                    check_lint_suppressions.main()
                except SystemExit:
                    pass

    args = mock_run.call_args[0][0]
    assert "origin/main...HEAD" in args
    assert "--cached" not in args


def test_compare_branch_and_ci_together():
    """--compare-branch and --ci can be combined: branch diff source with CI exit behaviour."""
    diff = _make_added_diff("services/api/main.py", "x = 1  # noqa: E501")
    mock_result = mock.Mock(stdout=diff)

    with mock.patch.object(
        check_lint_suppressions.subprocess, "run", return_value=mock_result
    ) as mock_run:
        captured = io.StringIO()
        with mock.patch.object(
            sys, "argv", ["check_lint_suppressions.py", "--compare-branch", "origin/main", "--ci"]
        ):
            with mock.patch("sys.stdout", captured):
                try:
                    check_lint_suppressions.main()
                    exit_code = 0
                except SystemExit as exc:
                    exit_code = exc.code if isinstance(exc.code, int) else 1

    args = mock_run.call_args[0][0]
    assert "origin/main...HEAD" in args
    assert exit_code == 0
    assert "SUPPRESSION_COUNT=1" in captured.getvalue()
