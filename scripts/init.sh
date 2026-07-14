#!/usr/bin/env bash
# Throughline — scaffold the mechanical structure into a target repo.
# Idempotent and merge-aware: safe to re-run; never clobbles an existing
# knowledge/ or overwrites an existing .claude/settings.json (merges the hook).
#
# By DEFAULT this installs the tool-agnostic plain-git `post-commit` breadcrumb
# hook (via core.hooksPath) — it fires after every successful commit with NO
# Claude Code dependency (works with plain git, Cursor, Codex, anything).
#
# The Claude-Code PostToolUse hook is OPTIONAL — pass --claude-code to also wire
# it in. Use it only when the project is driven through Claude Code and you want
# the in-agent additionalContext nudge on top of the printed terminal reminder.
#
# --type controls the bundle's temporal-record shape (dotKnowledge SPEC.md §3):
# a `person` subject gets journal/ (first-person, human voice); org/brand/project
# get ledger/ instead (agent-authored activity log — a person's the only subject
# with a first-person voice to journal). Omit --type to keep the original,
# unconditional journal/ behavior (default, backward-compatible for existing
# installs — this flag is additive, it never changes a repo that's already
# scaffolded).
#
# --with-stm adds stm/ (SPEC.md §3) — an optional, person-only, append-only,
# epistemically-inert capture surface for pre-verbal material (sparks,
# half-formed instincts) distinct from journal/'s dated first-person record.
# Errors on org/brand/project — stm/ has no single owner in a multi-person
# bundle. Opt-in and additive, same backward-compatibility discipline as --type:
# omitting it never changes a repo that's already scaffolded.
#
# Usage:
#   init.sh [repo-path]                          # default: plain-git post-commit hook, journal/
#   init.sh [repo-path] --type person             # explicit person bundle — journal/ (same as default)
#   init.sh [repo-path] --type org|brand|project   # canonical bundle — ledger/ instead of journal/
#   init.sh [repo-path] --with-stm                 # also scaffold stm/ (person-only)
#   init.sh [repo-path] --claude-code              # also wire the Claude Code PostToolUse hook
#
# (--repo-path may also be given positionally; the flag order is free.)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS="$(dirname "$SCRIPT_DIR")/assets"

# --- parse args (free order: one optional repo-path + optional flags) --------
target=""
WITH_CLAUDE_CODE=0
WITH_STM=0
SUBJECT_TYPE=""
prev=""
for arg in "$@"; do
  case "$prev" in
    --type) SUBJECT_TYPE="$arg"; prev=""; continue ;;
  esac
  case "$arg" in
    --claude-code) WITH_CLAUDE_CODE=1 ;;
    --with-stm) WITH_STM=1 ;;
    --type) prev="--type" ;;
    -h|--help)
      sed -n '2,29p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    -*) echo "✗ unknown flag: $arg" >&2; exit 1 ;;
    *)  target="$arg" ;;
  esac
done
case "$SUBJECT_TYPE" in
  ""|person|org|brand|project) ;;
  *) echo "✗ --type must be one of: person, org, brand, project (got: $SUBJECT_TYPE)" >&2; exit 1 ;;
esac
if [ "$WITH_STM" = "1" ] && { [ "$SUBJECT_TYPE" = "org" ] || [ "$SUBJECT_TYPE" = "brand" ] || [ "$SUBJECT_TYPE" = "project" ]; }; then
  echo "✗ --with-stm is person-only (SPEC.md §3) — stm/ has no single owner in a multi-person $SUBJECT_TYPE bundle" >&2
  exit 1
fi

# --- locate the target repo ---------------------------------------------------
if [ -z "$target" ]; then
  target="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi
cd "$target" || { echo "✗ cannot cd into $target" >&2; exit 1; }
echo "→ scaffolding knowledge layer into: $target"

# --- directories --------------------------------------------------------------
# sources/ is universal (raw intake, any subject type, SPEC.md §3).
mkdir -p knowledge/wiki knowledge/decisions knowledge/research knowledge/sources
if [ "$SUBJECT_TYPE" = "org" ] || [ "$SUBJECT_TYPE" = "brand" ] || [ "$SUBJECT_TYPE" = "project" ]; then
  TEMPORAL_DIR="ledger"
else
  TEMPORAL_DIR="journal"   # default (no --type) or --type person
fi
mkdir -p "knowledge/$TEMPORAL_DIR"
echo "✓ knowledge/{wiki,decisions,research,sources,$TEMPORAL_DIR}"

if [ "$WITH_STM" = "1" ]; then
  mkdir -p knowledge/stm
  echo "✓ knowledge/stm (person-only, append-only, epistemically inert — SPEC.md §3; no schema beyond append-only-ness, never time-boxed)"
fi

# --- roadmap stub (parking-lot for deferred ideas) ---------------------------
if [ -f knowledge/wiki/roadmap.md ]; then
  echo "• knowledge/wiki/roadmap.md already exists — left untouched"
else
  cat > knowledge/wiki/roadmap.md <<'ROADMAP'
---
title: Roadmap
type: Reference
---

# Roadmap

The "not now, but don't forget" pile — ideas and improvements parked until the time is right.
ROADMAP
  echo "✓ knowledge/wiki/roadmap.md"
fi

# =============================================================================
# DEFAULT: plain-git post-commit breadcrumb hook (no Claude Code dependency)
# =============================================================================
# Installed via core.hooksPath so the hook is tracked in-repo (.githooks/) and
# fires after every successful commit, whatever tool made the commit.
if git rev-parse --git-dir >/dev/null 2>&1; then
  bash "$SCRIPT_DIR/install-hook.sh" "$target"
else
  echo "• not a git repo yet — skipping post-commit hook install."
  echo "  Run \`git init\` here, then: bash $SCRIPT_DIR/install-hook.sh $target"
fi

# =============================================================================
# OPTIONAL: Claude Code PostToolUse hooks (--claude-code)
# =============================================================================
# Adds the in-agent additionalContext nudge + background codemap refresh on top
# of the plain-git hook. Only useful when the project is driven via Claude Code.
if [ "$WITH_CLAUDE_CODE" -eq 1 ]; then
  echo "→ --claude-code: wiring Claude Code PostToolUse hooks"
  mkdir -p .claude/hooks

  cp "$ASSETS/journal-breadcrumb.sh" .claude/hooks/journal-breadcrumb.sh
  chmod +x .claude/hooks/journal-breadcrumb.sh
  echo "✓ .claude/hooks/journal-breadcrumb.sh"

  cp "$ASSETS/codemap-refresh.sh" .claude/hooks/codemap-refresh.sh
  chmod +x .claude/hooks/codemap-refresh.sh
  echo "✓ .claude/hooks/codemap-refresh.sh"

  # Breadcrumb hook — emits the nudge agent note
  CRUMB_BLOCK='{"matcher":"Bash","hooks":[{"type":"command","if":"Bash(git commit*)","command":"\"$CLAUDE_PROJECT_DIR/.claude/hooks/journal-breadcrumb.sh\"","timeout":15,"statusMessage":"Journaling commit…"}]}'
  # Codemap refresh hook — regenerates the structural map in the background (no agent note)
  CODEMAP_BLOCK='{"matcher":"Bash","hooks":[{"type":"command","if":"Bash(git commit*)","command":"\"$CLAUDE_PROJECT_DIR/.claude/hooks/codemap-refresh.sh\"","timeout":35,"statusMessage":"Refreshing code map…"}]}'
  settings=".claude/settings.json"

  merge_hook() {
    local settings="$1" block="$2"
    if [ -f "$settings" ]; then
      local tmp
      tmp="$(mktemp)"
      jq --argjson h "$block" '
        .hooks //= {} |
        .hooks.PostToolUse //= [] |
        if any(.hooks.PostToolUse[]?; (.hooks // [])[]?.command == ($h.hooks[0].command))
        then .
        else .hooks.PostToolUse += [$h] end
      ' "$settings" > "$tmp" && mv "$tmp" "$settings"
    else
      jq -n --argjson h "$block" \
        '{"$schema":"https://json.schemastore.org/claude-code-settings.json","hooks":{"PostToolUse":[$h]}}' \
        > "$settings"
    fi
  }

  merge_hook "$settings" "$CRUMB_BLOCK"
  merge_hook "$settings" "$CODEMAP_BLOCK"
  echo "✓ merged Claude Code hooks into $settings"
  echo "  ⚠ both hooks key off git commit — to avoid a DOUBLE breadcrumb, the"
  echo "    plain-git and Claude-Code hooks share the same .last-breadcrumb state"
  echo "    file, so whichever runs first wins and the other no-ops. Good as-is."
fi

# --- gitignore the hook's local state ----------------------------------------
ignore=".gitignore"
if ! { [ -f "$ignore" ] && grep -q "knowledge/$TEMPORAL_DIR/.last-breadcrumb" "$ignore"; }; then
  printf '\n# Throughline breadcrumb hook state\nknowledge/%s/.last-breadcrumb\n' "$TEMPORAL_DIR" >> "$ignore"
  echo "✓ gitignored knowledge/$TEMPORAL_DIR/.last-breadcrumb"
fi

# --- union merge-driver for generated codemap files --------------------------
# Generated files must never throw merge conflicts — git's built-in union driver
# lets each branch's lines union, and the next commit's hook regenerates a clean file.
git config merge.union.name "union merge driver" 2>/dev/null || true
git config merge.union.driver "true" 2>/dev/null || true

attrs=".gitattributes"
if ! { [ -f "$attrs" ] && grep -q 'knowledge/wiki/_codemap.md' "$attrs"; }; then
  {
    printf '\n# Throughline generated files — union merge to avoid conflicts\n'
    printf 'knowledge/wiki/_codemap.md merge=union\n'
    printf 'knowledge/_codemap.json merge=union\n'
  } >> "$attrs"
  echo "✓ .gitattributes union merge-driver for _codemap.md + _codemap.json"
fi

# --- gitignore the generated codemap files -----------------------------------
# They are always regeneratable so we commit them if the project wants, but
# the project may opt out; ensure at minimum the .last-codemap state is ignored.
# (Projects may commit the codemap itself — it diffs cleanly; up to the project.)
if ! { [ -f "$ignore" ] && grep -q "knowledge/$TEMPORAL_DIR/.last-codemap" "$ignore"; }; then
  printf '# Throughline codemap hook state\nknowledge/%s/.last-codemap\n' "$TEMPORAL_DIR" >> "$ignore"
  echo "✓ gitignored knowledge/$TEMPORAL_DIR/.last-codemap"
fi

# --- template knowledge/AGENTS.md (canonical) + knowledge/CLAUDE.md (pointer) --
# AGENTS.md is the cross-tool standard (agents.md) and carries the real
# orientation — the three rules + the formats. knowledge/CLAUDE.md is a THIN
# pointer to it so Claude Code discovers the layer via progressive CLAUDE.md
# loading. Both are written; neither clobbers an existing file.
if [ -f knowledge/AGENTS.md ]; then
  echo "• knowledge/AGENTS.md already exists — left untouched"
else
  cp "$ASSETS/knowledge-AGENTS.md.tmpl" knowledge/AGENTS.md
  echo "✓ knowledge/AGENTS.md (TEMPLATE — fill in the {{PLACEHOLDERS}})"
fi

if [ -f knowledge/CLAUDE.md ]; then
  echo "• knowledge/CLAUDE.md already exists — left untouched"
else
  cp "$ASSETS/knowledge-CLAUDE.md.pointer.tmpl" knowledge/CLAUDE.md
  echo "✓ knowledge/CLAUDE.md (POINTER → AGENTS.md — set {{PROJECT_NAME}})"
fi

cat <<EOF

Mechanical scaffold complete. Next (the agent does these):
  1. Fill the {{PLACEHOLDERS}} in knowledge/AGENTS.md with real project context
     (that file is canonical). Set {{PROJECT_NAME}} in the knowledge/CLAUDE.md
     pointer too. Keep CLAUDE.md thin — never duplicate orientation into it.
  2. Write the repo-root README.md from references/readme-template.md (the
     standard structure). READMEs are WHAT/WHY/DIRECTION only — never research,
     findings, evaluations, or meeting origins. Research goes in knowledge/research/.
  3. Seed decisions/ + a backfill knowledge/$TEMPORAL_DIR/ entry from the project's current state.
  4. Point the repo-root docs at knowledge/AGENTS.md: write a repo-root AGENTS.md
     (canonical) + a thin repo-root CLAUDE.md pointer, and link them from README.
  5. Run the code-map generator to build the initial structural index:
       uv run --with tree-sitter --with tree-sitter-language-pack \\
           python3 ~/.claude/skills/knowledge-layer/scripts/codemap.py [repo-root]

The plain-git post-commit breadcrumb hook is ALREADY ACTIVE — make a commit and
a \`### HH:MM — <hash>\` block lands in today's knowledge/$TEMPORAL_DIR/<date>*.md. No
Claude Code, no /hooks, no restart needed.

If you ALSO ran with --claude-code, the in-agent PostToolUse hooks won't fire
until Claude Code re-reads config: open /hooks once, or restart the session.
EOF
