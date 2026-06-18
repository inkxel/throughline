# Knowledge Layer — skill notes

> Design notes and operating procedure for the knowledge-layer scaffolder. This is
> the *how it works / how to run it* doc, not the project README (which lives at the
> repo root). Use this whenever you want to set up the knowledge layer on a project —
> add ADRs / decision records / a project wiki / session-handoff continuity, or
> documentation that survives a session crash. The intent matters more than the exact
> words: if you want a repo to remember its own build history and decisions across
> sessions, this is the tool.

Scaffold a **code-side knowledge layer** into a project: the build-documentation system that gives a repo memory across sessions. This skill makes any new project match that convention.

## Why this exists (the problem it solves)

Build sessions surface rationale — *why* an architecture was chosen, *why* an approach was abandoned, *what's* still open — that gets parked verbally and then lost. For a solo or small/contracted team, that loss is the real risk: strong documentation is the survival strategy, the way a small operation keeps a system alive. A knowledge layer captures the *why* next to the source, append-only, so the next session (or the same person months later) reconstructs intent instead of re-litigating it.

## What gets created

```
knowledge/
  CLAUDE.md         orientation: the three rules + the formats (read first by any session)
  wiki/             curated reference — one article per subsystem/topic, append-only context logs
  journal/          per-session ADR-flavored entries, written continuously
  decisions/        atomic decision records (ADR format)
  wiki/roadmap.md   the parking lot
.claude/
  hooks/journal-breadcrumb.sh   auto-journals each git commit
  settings.json     wires the hook (PostToolUse, gated to git commit)
```

`wiki/` is the curated layer. `journal/` + `decisions/` are the firehose. The split is the whole point: write hot and often to the firehose, compile cold and deliberately to the wiki.

## The three rules (this is the system — internalize it)

1. **Journal continuously, wiki at the end.** The journal is append-only firehose — write to it *as you go*: after a larger move, a longer code run, **right after each `git commit`**, or before a risky operation. Batching journal writes to session-end loses information (you forget, you compress, or the session crashes). The commit-breadcrumb hook automates the cadence. The **wiki** only changes via an explicit end-of-session *compile pass* — that keeps it intentional and the prompt cache stable.
2. **Wiki updates need a real trigger — only three:** a new subsystem/capability was added; a documented decision is now contradicted; or the user explicitly said "document this." No "just in case" rewrites.
3. **Append-only, `[[wikilinks]]` everywhere.** Never edit prior entries — if something's wrong, append a correction linking the contradicting source. Cross-reference with `[[wikilinks]]` so the graph is navigable for humans (in any wiki-link-aware editor or plain file nav) and agents.

The full journal / decision / wiki frontmatter formats live in `references/formats.md` — read it when writing entries or when you need the exact templates to put in the project's `knowledge/CLAUDE.md`.

## How to run this skill

### 1. Scaffold the mechanical structure

Run the init script from the target repo (or pass the repo path). It's idempotent and merge-aware — safe to re-run, won't clobber an existing `knowledge/` or overwrite an existing `.claude/settings.json` (it merges the hook in).

```bash
bash ~/.claude/skills/knowledge-layer/scripts/init.sh [repo-path]
```

It creates the directories, installs the breadcrumb hook, merges the PostToolUse hook into `.claude/settings.json`, adds the hook's state file to `.gitignore`, and drops a **template** `knowledge/CLAUDE.md` with `{{PLACEHOLDER}}` fields if one doesn't exist already.

### 2. Adapt `knowledge/CLAUDE.md` to THIS project (don't leave the template raw)

The template is generic; a knowledge layer is only useful if its orientation file reflects the actual project. Open `knowledge/CLAUDE.md` and:

- Replace every `{{PLACEHOLDER}}` — project name, a one-line description of what the project is, the language/stack.
- Fill in the **"doc surfaces"** section honestly for this repo. Most projects have more than one place docs live; spell out how they differ so they don't get confused. Common surfaces: this `knowledge/` (build history), a `docs/` or `README` (the plan / how-to), and any external source of truth. If the project reads an external knowledge store at runtime (e.g. an app that queries a separate docs vault or knowledge base), note that it's unrelated to this build layer.
- Keep the three rules and the format templates verbatim (pull them from `references/formats.md`) — consistency across projects is the value; don't invent a per-project variant.

### 3. Seed it from the project's current state (so it doesn't start empty)

An empty knowledge layer has no gravity. Give it a starting mass:

- **Decision records** for the real decisions already baked into the project. Look at the architecture, the README, recent commits, and any "we chose X because Y" rationale. Write each as an ADR in `decisions/` (format in `references/formats.md`), including the *Dissent / Alternatives Considered* section so rejected paths aren't re-litigated.
- **A first journal entry** in `journal/YYYY-MM-DD-<slug>.md` capturing where the project stands right now and what's next — a backfill of recent history if the project already exists.
- **A few wiki articles** only for subsystems that genuinely exist and have content worth curating. Don't create empty shells — speculative `[[wikilinks]]` to not-yet-written articles are fine (they mark gaps), but don't manufacture filler.
- **Research artifacts** (findings, evaluations, option-analysis, benchmarks) go in `knowledge/research/<YYYY-MM>-<topic>.md` — never in the README.
- Add a pointer from the repo-root `CLAUDE.md` (or `README`) to `knowledge/CLAUDE.md` so fresh sessions discover it.

Get the date right — convert "today" to an absolute `YYYY-MM-DD` for filenames and frontmatter.

### 3b. Write the README from the standard template

Write the repo-root `README.md` from **`references/readme-template.md`** (the standard structure) so every project documents consistently. The README is **WHAT / WHY / DIRECTION / NAVIGATION only**. Keep OUT: research and findings (→ `knowledge/research/`), meeting origins, client names, internal-people names, and inlined decision rationale (→ link the ADR). The README states decisions and links the reasoning; it never reproduces research.

### 4. Activate the hook + tell the user

The breadcrumb hook won't fire until Claude Code re-reads settings. If `.claude/` was just created this session, the config watcher isn't watching it yet — tell the user to **open `/hooks` once (reloads config) or restart the session**. After that it's silent-automatic.

Then confirm it works: after the next `git commit`, a breadcrumb (`### HH:MM — hash / subject / files`) should appear in today's journal. If it doesn't, the watcher still hasn't picked up the config — `/hooks` or restart.

## The breadcrumb hook — what it does

On every `git commit` that advances `HEAD`, the hook appends a crash-proof breadcrumb (time, short hash, subject, changed files) to today's journal entry and injects a nudge reminding the agent to add the *why* while it's fresh. A `HEAD`-comparison guard means a blocked/failed commit (e.g. a gitleaks pre-commit reject) never breadcrumbs, and reruns never double-write. The commit is the natural "larger move" marker, so tying journaling to it gets the right cadence automatically — nobody has to remember.

It's deliberately a *breadcrumb + nudge*, not a blocking gate: it never interrupts flow, and even if a session dies mid-thought the skeleton trail is already on disk for the next session to flesh out.

## PREREQUISITES

The core scaffolder is intentionally light. Most of the system runs on stdlib + bash;
only the optional code-map feature reaches for heavier tooling, and every heavy path
degrades gracefully (guards and no-ops) so a missing dependency can never break a commit.

| Component | Requires | Notes |
|---|---|---|
| `okf-export.py` | **Python 3 only** — pure stdlib, **zero deps** | Runs anywhere `python3` exists. Verified clean on Python 3.14.5. |
| `init.sh` | **bash + jq** | `jq` drives the `.claude/settings.json` hook merge. Confirmed at `/usr/bin/jq`. |
| `codemap.py` *(deferred / beta)* | **uv + tree-sitter + tree-sitter-language-pack** | Invoked as `uv run --with tree-sitter --with tree-sitter-language-pack python3 codemap.py`. `uv` confirmed at `/opt/homebrew/bin/uv` (v0.11.19). Has a clean `ImportError` guard — if `tree-sitter-language-pack` is absent it exits with a helpful message and **never crashes the commit**. |
| `codemap-refresh.sh` hook | none hard | Silently **no-ops if `uv` is not on `PATH`** — never fails a commit. |

**Languages the code-map supports:** rust, typescript, tsx, javascript, php, python.
(Swift grammar is queued per the plan, not yet present.)

**OS support:** macOS and Linux (bash hooks + POSIX tooling). **Windows is explicitly
deferred** per the plan — it'll come later.

The practical takeaway: you need essentially nothing to run the knowledge layer itself
(`python3` + `bash` + `jq`, all standard on macOS/Linux). `uv` and the tree-sitter stack
are only for the optional code-map, and their absence is handled silently rather than as
an error.
