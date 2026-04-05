#!/bin/bash
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

# Wrapper around act that handles git worktree setups.
#
# When the repo uses a bare+worktree layout, act's --bind only mounts the
# worktree directory. The worktree's .git file references the bare repo at
# ../.bare, so git commands inside the container fail with "not a git
# repository". This script detects that case and adds an extra bind mount for
# the bare directory so git works correctly inside the act container.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

GIT_COMMON_DIR="$(git rev-parse --git-common-dir)"
GIT_COMMON_DIR="$(cd "$GIT_COMMON_DIR" && pwd)"

EXTRA_OPTS=()
if [[ "$GIT_COMMON_DIR" != "$REPO_ROOT/.git" ]]; then
    # Bare/worktree layout: mount the bare repo at the same absolute path
    EXTRA_OPTS+=(--container-options "-v ${GIT_COMMON_DIR}:${GIT_COMMON_DIR}:ro")
fi

act "${EXTRA_OPTS[@]}" "$@"
ACT_EXIT=$?

# act containers run as root and write root-owned files into the bind-mounted
# workspace. Fix ownership so local tools (pre-commit, ruff, mypy, uv) work.
sudo chown -R "$(id -u):$(id -g)" "$REPO_ROOT" 2>/dev/null || true

exit $ACT_EXIT
