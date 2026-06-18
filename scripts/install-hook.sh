#!/usr/bin/env bash
# Throughline — install the plain-git post-commit breadcrumb hook.
#
# Wires the tool-agnostic `post-commit` hook into a target repo via
# `core.hooksPath` so it fires after every successful commit — no Claude Code
# dependency. Works with plain git, Cursor, Codex, or any tool that commits.
#
# Why core.hooksPath (Option A) over dropping into .git/hooks (Option B):
#   - The hook lives in a TRACKED .githooks/ dir, so it's versioned with the repo
#     and survives a fresh `git clone` (re-run this script once per clone to wire it).
#   - One source of truth for the hook instead of an untracked .git/hooks/ copy.
#   Caveat: core.hooksPath disables ALL hooks in .git/hooks/. If the repo relies
#   on any of those, move them into .githooks/ too.
#
# Usage: install-hook.sh [repo-path]   (defaults to the git repo root, else $PWD)
#
# Idempotent: safe to re-run. Verify after install with --verify (see bottom).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_SRC="$SCRIPT_DIR/hooks/post-commit"

[ -f "$HOOK_SRC" ] || { echo "✗ hook source not found: $HOOK_SRC" >&2; exit 1; }

# --- locate the target repo ---------------------------------------------------
target="${1:-}"
if [ -z "$target" ]; then
  target="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi
cd "$target" || { echo "✗ cannot cd into $target" >&2; exit 1; }

git rev-parse --git-dir >/dev/null 2>&1 || {
  echo "✗ $target is not a git repo — run \`git init\` first, then re-run this." >&2
  exit 1
}
echo "→ installing post-commit breadcrumb hook into: $target"

# --- copy hook into a tracked .githooks/ dir + point git at it ----------------
mkdir -p .githooks
cp "$HOOK_SRC" .githooks/post-commit
chmod +x .githooks/post-commit
git config core.hooksPath .githooks
echo "✓ .githooks/post-commit  (core.hooksPath → .githooks)"

# --- gitignore the hook's local state ----------------------------------------
ignore=".gitignore"
if ! { [ -f "$ignore" ] && grep -q 'knowledge/journal/.last-breadcrumb' "$ignore"; }; then
  printf '\n# Throughline breadcrumb hook state\nknowledge/journal/.last-breadcrumb\n' >> "$ignore"
  echo "✓ gitignored knowledge/journal/.last-breadcrumb"
fi

# --- ensure the journal dir exists (hook no-ops without it) -------------------
if [ ! -d knowledge/journal ]; then
  echo "• note: knowledge/journal/ does not exist yet — the hook stays inert"
  echo "        until it does (that dir is what marks a repo Throughline-enabled)."
  echo "        Run init.sh, or \`mkdir -p knowledge/journal\`, to activate it."
fi

cat <<'EOF'

Done. The hook fires after every successful commit (plain git — no Claude Code needed).

Make every fresh clone wire itself up automatically by adding this one line to
the repo's setup/bootstrap (package.json "prepare", a Makefile target, or README):

    git config core.hooksPath .githooks

(core.hooksPath is NOT auto-applied on clone for safety, so it must be set once
per machine/clone.)

Verify: make a trivial commit and confirm a `### HH:MM — <hash>` block was
appended to today's knowledge/journal/<date>*.md. Re-running the hook manually
(`.githooks/post-commit`) WITHOUT a new commit must NOT append a second time.
EOF
