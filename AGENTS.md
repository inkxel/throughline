# AGENTS.md — Throughline

> Canonical agent-instructions file for this repo, per the cross-tool [AGENTS.md](https://agents.md) standard (the open convention adopted across 20+ coding agents). Any agent — Claude Code, Cursor, Codex, Aider, others — reads this first. `CLAUDE.md` is a thin pointer to this file; keep the instructions here, not duplicated there.

## What this repo is

**Throughline**, a knowledge-layer scaffolder: a tool that drops a code-side knowledge layer into any project — a curated wiki, an append-only per-session journal, ADR decision records, a roadmap parking lot, and a commit-triggered hook that auto-journals every git commit. It gives a repo session-to-session memory so the *why* behind a build survives crashes, context resets, and months of gaps. The whole layer exports to an OKF (Google's Open Knowledge Format) bundle that passes Google's reference validator.

Running `scripts/init.sh [repo-path]` scaffolds that structure into a target repo. The `assets/` hold the files it installs (the `knowledge/CLAUDE.md` template, the breadcrumb + codemap hooks); `references/` hold the formats, the README template, and the OKF-compatibility map; `scripts/` hold the init script, the tree-sitter codemap generator, and the OKF exporter.

## How to use the knowledge layer — the three rules

A scaffolded project gets a `knowledge/` directory with its own `knowledge/CLAUDE.md` (and `knowledge/AGENTS.md` pointer) carrying these same rules. Internalize them — they *are* the system.

### Rule 1 — Journal continuously, wiki at the end
The journal is the firehose: append to today's `knowledge/journal/YYYY-MM-DD-slug.md` **as you go, not at session end** — after a larger move lands, after a long code run, **right after each `git commit`**, or before any risky/irreversible operation. Batching to session-end loses information (you forget, you compress, or the session crashes). A rough running entry beats a perfect one that never gets written; entries are append-only. The **wiki** changes only via an explicit end-of-session compile pass — journal hot and often, compile to wiki cold and deliberately.

### Rule 2 — Wiki updates require a real trigger — only three
1. A new subsystem/capability got added → new article or new section.
2. A previously-documented decision is now contradicted → update the article + log the contradiction.
3. The user explicitly said "document this in the wiki."

No "just in case" updates. No proactive rewrites of articles that aren't broken. This keeps the wiki intentional and the prompt cache stable.

### Rule 3 — Append-only, `[[wikilinks]]` everywhere
Wiki, journal, and decision entries are append-only context logs with dated entries. **Never edit a prior entry** — if something is wrong, append a correction that links the contradicting source. All cross-references use `[[wikilinks]]` so the graph is navigable for humans (in any wiki-link-aware editor or plain file nav) and for agents.

## Where things live

```
knowledge/
  CLAUDE.md / AGENTS.md   orientation — the three rules + the formats (read first)
  wiki/                   curated reference, one article per subsystem/topic (append-only context logs)
  wiki/_codemap.md        auto-generated tree-sitter structural index — consult BEFORE grepping
  wiki/roadmap.md         the parking lot — "at some point we should…"
  journal/                per-session ADR-flavored entries, YYYY-MM-DD-slug.md, written continuously
  decisions/              atomic decision records, YYYY-MM-DD-slug.md, ADR format
  research/               findings, evaluations, option-analysis, YYYY-MM-slug.md
.claude/
  hooks/journal-breadcrumb.sh   auto-journals each git commit (breadcrumb + nudge)
  hooks/codemap-refresh.sh      regenerates the structural map on source commits
  settings.json                 wires both hooks (PostToolUse, gated to git commit)
```

`wiki/` is the curated layer; `journal/` + `decisions/` are the firehose; `research/` holds findings; `roadmap.md` is the parking lot. The split is the whole point.

### Read the codemap before grepping
`knowledge/wiki/_codemap.md` is a deterministic (no-LLM) tree-sitter index of every source file's top-level symbols and import edges. Before grepping for "where does X live" or "what calls Y," read it first; grep only to confirm details or when the map is stale. The wiki and ADRs hold the *why*; the codemap holds the *what/how*.

## README & research conventions

- **The README is WHAT / WHY / DIRECTION / NAVIGATION only.** Write it from `references/readme-template.md` so every repo is consistent.
- **Research never goes in the README.** Findings, evaluations, benchmarks, option-analysis → `knowledge/research/<YYYY-MM>-<topic>.md`. The README states the *decision* and links; it never reproduces the research. Test: *if it reads like findings, it's research; if it reads like direction, it's README.*
- **No meeting origins, no client/internal-people names in the README** — keep repos client-neutral.

## Working in THIS repo (the scaffolder tool)

- `scripts/init.sh` is **idempotent and merge-aware** — safe to re-run; never clobbers an existing `knowledge/` and merges (not overwrites) the hooks into `.claude/settings.json`. Preserve those properties when editing it.
- The canonical formats live in `assets/knowledge-AGENTS.md.tmpl` (the orientation file the scaffolder drops as `knowledge/AGENTS.md`) and `references/formats.md` (worked examples). If you change a rule or a frontmatter shape, change it in **both** so scaffolded projects and the worked examples stay in sync. `assets/knowledge-CLAUDE.md.pointer.tmpl` is the thin pointer dropped as `knowledge/CLAUDE.md` — it should stay pointer-only.
- Keep the AGENTS.md-canonical / CLAUDE.md-pointer split everywhere this repo emits docs: the scaffolder writes both into a target project, with CLAUDE.md as the thin pointer.
- Get the date right — convert "today" to an absolute `YYYY-MM-DD` for filenames and frontmatter; never guess the day-of-week.

## OKF compatibility

This layer is built on the same "LLM wiki" pattern as Google's Open Knowledge Format (OKF v0.1). `references/okf-compatibility.md` maps the convention to the spec and `scripts/okf-export.py` produces a conformant bundle. `AGENTS.md`, `CLAUDE.md`, `README.md`, `index.md`, `log.md`, `roadmap.md`, and `_codemap.md` are reserved filenames in the exporter — don't repurpose them.
