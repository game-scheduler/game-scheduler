#!/usr/bin/env bash
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


set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
prompts_dir="$root_dir/.copilot-tracking/planning/prompts"

usage() {
  cat <<'USAGE'
Usage:
  scripts/show-implement-prompt.sh [prompt-name-or-path]

Examples:
  scripts/show-implement-prompt.sh
  scripts/show-implement-prompt.sh implement-game-archive-feature
  scripts/show-implement-prompt.sh .copilot-tracking/planning/prompts/implement-game-archive-feature.prompt.md
USAGE
}

if [[ ! -d "$prompts_dir" ]]; then
  echo "Prompts directory not found: $prompts_dir" >&2
  exit 1
fi

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z ${1:-} ]]; then
  echo "Available implementation prompts:" >&2
  ls -1 "$prompts_dir" | sed 's/\.prompt\.md$//' | sed 's/^/  - /'
  exit 0
fi

input="$1"
if [[ -f "$input" ]]; then
  cat "$input"
  exit 0
fi

candidate="$prompts_dir/${input%.prompt.md}.prompt.md"
if [[ -f "$candidate" ]]; then
  cat "$candidate"
  exit 0
fi

echo "Prompt not found: $input" >&2
usage
exit 1
