# Throughline — Knowledge Layer (AGENTS.md)

> **What Throughline is.** A knowledge-layer scaffolder: a tool that drops a code-side knowledge layer — curated wiki, append-only journal, ADR decision records, roadmap, commit-triggered auto-journal hook — into any project, then exports the whole thing as a bundle in Google's Open Knowledge Format (OKF).

This is the **canonical** agent-instructions file for this knowledge layer, per the cross-tool [AGENTS.md](https://agents.md) standard — any agent (Claude Code, Cursor, Codex, Aider, …) reads it. The sibling `knowledge/CLAUDE.md` is a thin pointer back here; keep the orientation in this file, not duplicated there. Claude Code discovers this layer when a session opens this repo's `knowledge/` directory (the `CLAUDE.md` pointer triggers progressive loading, which leads here). Read it before doing architectural work on Throughline's own build history — this is separate from the root `AGENTS.md`/`CLAUDE.md`, which cover how to work *on the tool itself* (`scripts/init.sh` idempotency, keeping `assets/` and `references/` in sync, the OKF exporter's reserved filenames).

**Self-referential, on purpose.** Throughline is the repo that *originates* this exact convention — `assets/knowledge-AGENTS.md.tmpl` is the template this very file was filled in from, and `assets/knowledge-CLAUDE.md.pointer.tmpl` is what the sibling `knowledge/CLAUDE.md` was filled in from. So this file is Throughline dogfooding its own scaffold on itself: the tool that writes `knowledge/AGENTS.md` into other people's repos didn't yet have one in its own `knowledge/` directory (which so far only held `research/`) until this session. That's not a special case to hide — it's the most direct proof the convention works: if it can't survive being pointed at its own author, it isn't ready to hand to anyone else.

## What this knowledge layer is

A mini wiki + per-session journal + decision records + roadmap, living inside this repo at `knowledge/`. It exists because rationale surfaces in build sessions on the *scaffolder itself* (why the OKF exporter's `--reliability` mode is shaped the way it is, why a feature stayed off the headline path, what the AI-labs OKF video convergence analysis concluded) — that gets parked verbally and lost otherwise. This layer makes Throughline's own build legible session-to-session, same as it does for any project it's scaffolded into.

### The doc surfaces (don't confuse them)
- **`knowledge/`** (this layer) — *build history of Throughline itself*: decisions made while building the scaffolder and exporter, per-session journal, curated wiki of how this repo's own tooling is organized and why.
- **`README.md`** — the pitch and how-to for *using* Throughline on another project (install, `throughline init`, the three rules, the OKF-native angle). Read for *what this tool does and how to get it*; `knowledge/` records *what we did while building it*.
- **`AGENTS.md` / `CLAUDE.md`** (repo root) — agent-authoring conventions for anyone working *on this tool's own code* (`scripts/`, the exporter, the hooks) — keeping `init.sh` idempotent, keeping `assets/knowledge-AGENTS.md.tmpl` and `references/formats.md` in sync, the OKF reserved-filename list. Distinct from this file, which is this repo's own build-memory layer, not authoring rules for its source.
- **`assets/knowledge-AGENTS.md.tmpl` + `assets/knowledge-CLAUDE.md.pointer.tmpl`** — the canonical templates this repo *distributes*. This file and its sibling `knowledge/CLAUDE.md` are filled-in instances of those exact templates, applied to Throughline itself.
- **`references/formats.md` + `references/okf-compatibility.md` + `references/readme-template.md`** — worked examples and spec maps that travel with the scaffolder; not part of this repo-level `knowledge/` layer, but read them for format detail beyond what's inlined below.

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

`wiki/` is the curated layer. `journal/` and `decisions/` are the firehose. `research/` holds findings (this repo already has two: the AI-labs OKF convergence analysis and the OKF community-signals note). `roadmap.md` is the parking lot. Only `research/` exists in this repo's `knowledge/` today — `wiki/`, `journal/`, and `decisions/` get added the first time a real entry needs one, per Rule 1 below; an empty folder isn't scaffolded just to match the diagram.

## README & research conventions

- **The README is WHAT / WHY / DIRECTION / NAVIGATION only.** Write it from `references/readme-template.md` so every repo this tool touches — including this one — is consistent.
- **Research never goes in the README.** Findings, evaluations, benchmarks, option-analysis → `knowledge/research/<YYYY-MM>-<topic>.md`. The README states the *decision* and links; it never reproduces the research. Test: *if it reads like findings, it's research; if it reads like direction, it's README.*
- **No meeting origins, no client/internal-people names in the README** — keep the repo client-neutral.

## Claim provenance tags (optional, use sparingly)

Beyond article-level `confidence:`, an individual claim inside a wiki article or ADR can carry a provenance tag for *how it was known*, not just how confident you are:
- **`EXTRACTED`** — sourced directly from the code or a validated export (you read it, it's ground truth for the current state)
- **`INFERRED`** — assembled from reading or extrapolation (verify before acting)

Use these inline, only when the distinction matters for the reader. Throughline's own optional `codemap` subsystem (tree-sitter, still beta — see `references/roadmap-codemap.md`) is a separate, code-level version of the same idea: a deterministic structural index rather than an LLM-assembled one.

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
deciders: <names>
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

### 2026-07-01 — AGENTS.md + CLAUDE.md added
This repo's own `knowledge/` folder only had `research/` (two notes: the OKF AI-labs convergence analysis and an OKF community-signals note in progress) — no orientation file, and no `journal/`, `decisions/`, or `wiki/` yet. Added `AGENTS.md` (canonical) + `CLAUDE.md` (thin pointer), filled in from this repo's own `assets/knowledge-AGENTS.md.tmpl` / `assets/knowledge-CLAUDE.md.pointer.tmpl` — Throughline dogfooding its own scaffold on itself. `journal/`, `decisions/`, and `wiki/` will be added the first time a real entry needs one, per Rule 1. No existing research notes were changed.
