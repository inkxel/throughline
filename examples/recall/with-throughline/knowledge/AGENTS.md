# session-service — Knowledge Layer (AGENTS.md)

> **What session-service is.** A tiny HTTP service that issues, validates, and revokes user sessions, backed by a durable on-disk session cache.

This is the **canonical** agent-instructions file for this knowledge layer, per the cross-tool [AGENTS.md](https://agents.md) standard — any agent (Claude Code, Cursor, Codex, Aider, …) reads it. The sibling `knowledge/CLAUDE.md` is a thin pointer back here; keep the orientation in this file, not duplicated there. Claude Code discovers this layer when a session opens `examples/recall/with-throughline/knowledge/` (the `CLAUDE.md` pointer triggers progressive loading, which leads here). Read it before doing architectural work. The wiki below documents how session-service is built, why it's shaped that way, and what's still open.

---

## What this knowledge layer is

A mini wiki + per-session journal + decision records + roadmap, living inside the code repo at `knowledge/`. It exists because rationale surfaces in build sessions, gets parked verbally, then gets lost. This layer makes the build legible session-to-session — for the next agent and for the future you.

> **Note for the recall demo.** This repo is one half of `throughline/examples/recall/`. The single highest-value record here is the session-cache ADR — the *why* behind SQLite+WAL that is **completely invisible in the code itself** (the code shows the final answer with no trace of the two rejected alternatives). The `without-throughline/` sibling is the same code with no knowledge layer; that's the control. If you can answer "why SQLite, why not in-memory or a JSON file?" here but not there, the demo worked.

### The doc surfaces (don't confuse them)

- **`knowledge/`** (this layer) — *build history.* Decisions made while building, per-session journal, curated wiki of how it actually works.
- **`README.md`** (repo root) — *what it is and how to run it.* Read for the API surface and run instructions; `knowledge/` records *why it's shaped this way*.

## How it's organized

```
knowledge/
  AGENTS.md          this file (canonical) — orientation, the three rules, the formats
  CLAUDE.md          thin pointer to AGENTS.md (so Claude Code discovers the layer)
  wiki/              curated reference, one article per subsystem/topic — append-only context logs
  journal/           per-session ADR-style entries — YYYY-MM-DD-slug.md, written continuously
  decisions/         atomic decision records — YYYY-MM-DD-slug.md, ADR format
  research/          research, findings, evaluations, option-analysis — YYYY-MM-slug.md
  wiki/roadmap.md    parking lot — "at some point we should…"
```

`wiki/` is the curated layer. `journal/` and `decisions/` are the firehose. `research/` holds findings. `roadmap.md` is the parking lot.

## README & research conventions

- **The README is WHAT / WHY / DIRECTION / NAVIGATION only.** It's the canonical one-page outline — what this is, why it exists, where it's going, how to navigate. Write it from the standard structure in `~/.claude/skills/knowledge-layer/references/readme-template.md` so every repo is consistent.
- **Research never goes in the README.** Findings, evaluations, benchmarks, data-source comparisons, A/B/C option-analysis, budget estimates, vendor evals → `knowledge/research/<YYYY-MM>-<topic>.md`. The README states the *decision* that came out of it and links; it never reproduces the research. Test: *if it reads like findings, it's research; if it reads like direction, it's README.*
- **No meeting origins, no client/internal-people names in the README** — keep repos client-neutral; that context lives in your separate strategic/knowledge layer.

## Code-map — structural WHAT/HOW (consult before grepping)

`knowledge/wiki/_codemap.md` is an auto-generated structural index of this repo's source files — top-level symbols (functions, classes, structs, exports) and import edges, extracted by tree-sitter (deterministic, no LLM). `knowledge/_codemap.json` is the machine-readable companion.

**Before grepping for "where does X live" or "what calls Y," read `_codemap.md` first.** It maps the structure in one pass; grep only to confirm details or when the map is stale. The curated wiki and ADRs hold the *why*; the codemap holds the *what/how*.

Claim provenance tags (from `references/formats.md`):
- **`EXTRACTED`** — sourced directly from the code / AST (treat as ground truth)
- **`INFERRED`** — assembled from reading or extrapolation (verify before acting)

Regenerate the map any time:
```
uv run --with tree-sitter --with tree-sitter-language-pack \
    python3 ~/.claude/skills/knowledge-layer/scripts/codemap.py [repo-root]
```
The commit hook also regenerates it automatically on source-file commits.

---

## The three rules — no more

### Rule 1 — Journal *continuously*, wiki at the end

The journal is the firehose — write to it **as you go, not at session end.** Batching journal writes to the end loses information: you forget, you compress it away, or the session crashes and it's gone. The journal must survive a crash at any point.

**Checkpoint cadence — append to today's `journal/YYYY-MM-DD-slug.md` after any of these, while fresh:**
- a larger move lands (a feature works, a subsystem changes, a milestone closes)
- a longer code run completes (a big edit pass, a refactor, a tricky debug)
- **right after each `git commit`** — the commit is the natural "larger move" marker; journal the *why* the commit message doesn't capture (a breadcrumb hook automates the prompt)
- before any risky/irreversible operation (so intent is recorded even if it goes wrong)

A rough running entry beats a perfect one that never gets written. The entry is append-only — keep adding sections as the session progresses.

**Wiki, by contrast, is end-of-session only.** At session end an **explicit compile pass** promotes mature journal entries into wiki updates (per Rule 2). Without an explicit trigger the wiki stays untouched — that keeps it intentional and the prompt cache stable. *Journal hot and often, compile to wiki cold and deliberately.*

### Rule 2 — Wiki updates require a real trigger — only three
1. A new subsystem/capability got added → write a new article or new section.
2. A previously-documented decision is now contradicted → update the article + log the contradiction.
3. The user explicitly said "document this in the wiki."

No "just in case" updates. No proactive rewrites of articles that aren't broken.

### Rule 3 — Append-only, wiki-links everywhere
Wiki articles are append-only context logs with dated entries. Journal and decision entries are append-only. All cross-references use `[[wiki-links]]`. Never edit prior entries; if something is wrong, append a correction with a link to the contradicting source.

---

## Journal entry format — ADR-flavored

Each `journal/YYYY-MM-DD-slug.md`:

```markdown
---
type: Journal                      # OKF-required concept type (keep it)
date: YYYY-MM-DD
session: short-slug
status: in-progress | shipped | abandoned | superseded-by [[YYYY-MM-DD-slug]]
related: [[article-1]], [[article-2]]
---

# Session Title — What we worked on

## Context
Where we were when we started. What problem this session was responding to.

## What changed
- Paths touched: `src/...`
- Subsystems affected: [[article]]
- Behavior shipped: brief description

## Decisions made
- **Decision** — short statement. Rationale + link: [[decisions/YYYY-MM-DD-slug]]

## What was tried and abandoned
- Tried X — dropped because Y. Saves the next teammate from re-litigating.

## Open threads
- [ ] Next-session item with [[wiki-link]]

## Related
- Touched articles: [[article]]
```

## Decision record format — standard ADR

Each `decisions/YYYY-MM-DD-slug.md`:

```markdown
---
type: Decision                     # OKF-required concept type (keep it)
date: YYYY-MM-DD
status: accepted | proposed | deprecated | superseded-by [[YYYY-MM-DD-slug]]
deciders: <name or role>
related: [[article-1]]
---

# Decision: One-sentence statement (verb-led, decisive)

## Context
The forces at play. What we were deciding against. Why now.

## Decision
What we're doing.

## Consequences
- **Positive:** what gets easier
- **Negative:** what gets harder, what we're trading away
- **Neutral:** what changes that's neither good nor bad

## Dissent / Alternatives Considered
Options weighed *before* the decision and why each lost. If there were none, say
"None — only viable path given X" so absence is explicit.

## Sources
- [[journal/YYYY-MM-DD-slug]] — session where this surfaced
```

## Wiki article frontmatter convention

```yaml
---
name: short-kebab-slug
type: subsystem | topic | meta | roadmap
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
confidence: high | medium | low | speculative
related: [[other-article-1]], [[other-article-2]]
---
```

**`confidence:`** — **high** (in code / ratified in a decision / repeatedly confirmed) · **medium** (said once, one source, not contradicted) · **low** (inference / single source, provisional) · **speculative** (extrapolation, revisit before acting). Add it when an article is touched for a real reason, not in a bulk pass.

---

## Context log

### 2026-06-17 — Knowledge layer created
Scaffolded with Throughline. Seeded with one decision record ([[decisions/2026-05-12-session-cache-sqlite-wal]]) and a backfill journal entry ([[journal/2026-05-12-session-cache-durability]]) reconstructing the session-cache durability decision, plus a [[session-cache]] wiki article. The cache ADR is the load-bearing record: it preserves the two rejected alternatives (in-memory, JSON file) that left no trace in the code.
