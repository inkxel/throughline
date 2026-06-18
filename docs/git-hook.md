# Git post-commit breadcrumb hook

> The tool-agnostic, plain-git version of the journal breadcrumb hook. It fires
> after every successful commit — whatever made the commit (plain `git`, Cursor,
> Codex, an IDE, a script) — and needs **no Claude Code**. This is now the
> **default** install path for the knowledge layer. The Claude Code PostToolUse
> hook (`assets/journal-breadcrumb.sh`) is the optional add-on, not the baseline.

## What it does

On every commit that **advances `HEAD`**, the hook appends a crash-proof
breadcrumb to today's journal entry:

```
### 14:32 — a1b9f3c
Wire union merge-driver for generated codemap
files: scripts/init.sh, docs/git-hook.md
```

It then prints a reminder to **stderr** (so it surfaces in the terminal without
polluting stdout) nudging you to write the *why* — rationale, what was tried and
abandoned, open threads — while it's fresh, instead of deferring to session end.
The commit is the natural "larger move" marker, so tying the journal cadence to
it means nobody has to remember to write breadcrumbs.

The breadcrumb lands in the newest `knowledge/journal/<today>*.md`. If no session
entry exists yet, the hook creates `knowledge/journal/<today>-session.md` with
frontmatter and a header.

### Why a separate plain-git hook (vs. the Claude Code one)

| | plain-git `post-commit` | Claude Code PostToolUse |
|---|---|---|
| Fires on | every successful commit, any tool | only commits made via Claude Code's Bash tool |
| Dependency | git + coreutils only (no `jq`) | Claude Code session + `jq` |
| Nudge surface | printed to terminal (stderr) | injected into the agent as `additionalContext` |
| Install | `core.hooksPath` (tracked, survives clone) | merged into `.claude/settings.json` |

The plain-git hook is the survival baseline: it journals even when you commit
outside Claude Code. The Claude Code hook adds the *in-agent* nudge on top — only
worth it when the project is driven through Claude Code.

## How the journal and git interact

The breadcrumb the hook writes is an **uncommitted working-tree change**. It lands in `knowledge/journal/<date>*.md` *after* the commit completes, so it rides along in your **next** commit — a one-commit lag. This is intentional.

We deliberately do NOT run `git commit --amend` inside the hook. Amending rewrites the commit SHA, which breaks signed commits and anything already pushed to a remote. A hook that silently rewrites history is worse than a one-entry lag.

If you'd rather keep the journal entirely local and out of version control, add `knowledge/journal/` to `.gitignore`. The hook will still write breadcrumbs on your machine; they just won't travel with the repo.

## Guarantees

- **Never double-writes.** A `HEAD`-comparison guard (state file
  `knowledge/journal/.last-breadcrumb`) means re-running the hook, amending, or a
  no-op commit won't append a second breadcrumb.
- **Never blocks a commit.** `post-commit` only runs *after* git has already
  committed successfully, and the hook exits 0 on any non-fatal problem. A
  blocked or failed commit never reaches it.
- **Inert until opted in.** The hook no-ops unless `knowledge/journal/` exists —
  that directory is what marks a repo as "knowledge-layer enabled."

## Install

### Default — via `init.sh`

`init.sh` installs this hook automatically (it calls `install-hook.sh`):

```bash
bash scripts/init.sh [repo-path]
```

To *also* wire the optional Claude Code PostToolUse hooks on top:

```bash
bash scripts/init.sh [repo-path] --claude-code
```

### Standalone — `install-hook.sh`

If you only want the git hook on an existing repo:

```bash
bash scripts/install-hook.sh [repo-path]
```

This uses **`core.hooksPath`** (Option A): it copies `scripts/hooks/post-commit`
into a tracked `.githooks/` directory and points git at it. The hook is then
versioned with the repo and survives a fresh `git clone`.

> **`core.hooksPath` is not auto-applied on clone** (git's safety default). So
> each fresh clone must run `git config core.hooksPath .githooks` once. Wire that
> into the repo's bootstrap — a `package.json` `"prepare"` script, a `Makefile`
> target, or a README setup step — so clones self-configure.
>
> **Caveat:** setting `core.hooksPath` disables every hook in `.git/hooks/`. If
> the repo relies on any of those, move them into `.githooks/` too.

### Alternative — drop into `.git/hooks` (Option B)

Simplest for a single machine, but **not tracked** by git so it won't travel
with the repo:

```bash
cp scripts/hooks/post-commit .git/hooks/post-commit
chmod +x .git/hooks/post-commit
```

## Dependencies

Standard git + coreutils only: `date`, `sed`, `awk`, `ls`, `head`, `cat`. No
`jq` (that was Claude-Code-only, for emitting the `additionalContext` JSON).

## Verify

```bash
# 1. Make a trivial commit, then confirm a breadcrumb landed:
git commit --allow-empty -m "test breadcrumb"
ls -t knowledge/journal/$(date +%F)*.md | head -1   # newest today entry — should contain a "### HH:MM — <hash>" block

# 2. Re-run the hook WITHOUT a new commit — it must NOT append a second time:
.githooks/post-commit        # (or .git/hooks/post-commit under Option B)
# the journal file's breadcrumb count is unchanged → the HEAD guard works
```

If a commit produces no breadcrumb, check that `knowledge/journal/` exists and
that the hook is wired: `git config --get core.hooksPath` should print
`.githooks` (Option A), or `.git/hooks/post-commit` should exist and be
executable (Option B).
