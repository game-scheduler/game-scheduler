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


"""
Pre-commit hook that scans staged diff lines for lint suppression patterns.

Phase A: Permanently blocked patterns (bare/blanket suppressions) — fail immediately.
Phase B: Counted patterns (specific suppressions) — fail if count exceeds APPROVED_OVERRIDES.
"""

import argparse
import os
import re
import shutil
import subprocess  # noqa: S404 - Used safely with hardcoded args and shell=False
import sys
from pathlib import Path

BLOCKED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"#\s*noqa(?!\s*:)"),
    re.compile(r"#\s*ruff:\s*noqa"),
    re.compile(r"#\s*type:\s*ignore(?!\[)"),
    re.compile(r"#lizard\s+forgive\s+global"),
    re.compile(r"//\s*@ts-ignore"),
    re.compile(r"//\s*eslint-disable(?!-next-line)"),
    re.compile(r"/\*\s*eslint-disable"),
]

COUNTED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"#\s*noqa:\s*\w+"),
    re.compile(r"#\s*type:\s*ignore\["),
    re.compile(r"#lizard\s+forgives"),
    re.compile(r"//\s*@ts-expect-error"),
    re.compile(r"//\s*eslint-disable-next-line\s+\S+"),
]

_INSTRUCTIONS_REF = ".github/instructions/quality-check-overrides.instructions.md"

_SCANNED_EXTENSIONS = frozenset({".py", ".ts", ".tsx", ".js", ".jsx"})

_EXCLUDED_PATH_PREFIXES = ("tests/",)


def _get_added_lines(compare_branch: str | None = None) -> list[tuple[str, int, str]]:
    """Return (filename, lineno, text) for every added line in the staged diff."""
    git = shutil.which("git")
    if git is None:
        return []
    if compare_branch is not None:
        cmd = [git, "diff", f"{compare_branch}...HEAD", "--unified=0"]
    else:
        cmd = [git, "diff", "--cached", "--unified=0"]
    result = subprocess.run(  # noqa: S603 - Hardcoded args, shell=False, no user input
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    added: list[tuple[str, int, str]] = []
    current_file = ""
    current_line = 0

    for raw in result.stdout.splitlines():
        if raw.startswith("+++ b/"):
            current_file = raw[6:]
            current_line = 0
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            current_line = int(m.group(1)) if m else 0
        elif raw.startswith("+++"):
            pass
        elif raw.startswith("+"):
            if Path(current_file).suffix in _SCANNED_EXTENSIONS and not any(
                current_file.startswith(prefix) for prefix in _EXCLUDED_PATH_PREFIXES
            ):
                added.append((current_file, current_line, raw[1:]))
            current_line += 1

    return added


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compare-branch", dest="compare_branch", default=None)
    parser.add_argument("--ci", action="store_true", default=False)
    args = parser.parse_args()

    added_lines = _get_added_lines(compare_branch=args.compare_branch)

    violations: list[tuple[str, int, str]] = [
        (filename, lineno, text.strip())
        for filename, lineno, text in added_lines
        if any(p.search(text) for p in BLOCKED_PATTERNS)
    ]

    if violations:
        print("ERROR: Bare/blanket quality check suppression detected in staged changes.")
        for filename, lineno, text in violations:
            print(f"  {filename}:{lineno}: {text}")
        print("This suppresses checks entirely and is never permitted.")
        print(f"See {_INSTRUCTIONS_REF} for policy details.")
        sys.exit(1)

    count = sum(1 for _, _, text in added_lines if any(p.search(text) for p in COUNTED_PATTERNS))
    approved = int(os.environ.get("APPROVED_OVERRIDES", "0"))

    if args.ci:
        print(f"SUPPRESSION_COUNT={count}")
        return

    if count > approved:
        print(f"ERROR: {count} quality check suppression(s) added in staged changes.")
        print("These require explicit user approval before committing.")
        print(f"See {_INSTRUCTIONS_REF} for policy details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
