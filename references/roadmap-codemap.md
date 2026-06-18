# Roadmap / decision-in-waiting: borrowing from graphify — add a code-structure map layer

**Status:** implemented (items 1–5 built 2026-06-06)
**Date:** 2026-06-06
**Scope:** All five ranked items from the "What to build" list are complete. The scoped-out list is unchanged.

> This repo is a *tool*, not itself a knowledge layer instance, so it has no
> `decisions/` dir or `roadmap.md` of its own — its conventions live in `SKILL.md`,
> `README.md`, this `references/` folder, and the `assets/` template. This note is the
> repo's roadmap-plus-ADR for one planned evolution, filed where the skill's deeper
> design material already lives (`SKILL.md` points here for "the nuances that make the
> system work").

---

## Context — the gap this closes

The knowledge layer captures the **WHY** of a build: curated wiki, append-only journal,
ADR decision records, a roadmap parking lot. It deliberately does *not* capture the
**WHAT/HOW** of the code's *current structure* — which modules exist, which symbols
matter, what calls/imports what. Today an agent that wants "what's wired" has to **grep**,
which is expensive and lossy on a large repo, and re-derives the same map every session.

[graphify](https://github.com/safishamsi/graphify) (`pip install graphifyy`) solves exactly
the structural-map problem: it turns a repo into a queryable knowledge **graph** via a
local, free, deterministic **tree-sitter AST pass** (functions / classes / imports /
call-graph — no LLM), refreshed by a git hook, queried as a subgraph. Full evaluation:
(see this roadmap note's Sources).

The two tools are **complementary, not competing** — graphify is the structural WHAT/HOW;
the knowledge layer is the curated WHY (graphify is explicitly weak on "why," which is
precisely our journal + ADRs). The directive here is **not** to install graphify alongside
every project. It's to **borrow the pieces that earn their keep into the knowledge layer
itself**, and keep it lean.

## Decision (proposed)

Add an auto-generated **code-structure map** as a first-class part of the scaffolded
knowledge layer, pairing the structural WHAT/HOW with the curated WHY — built from
tree-sitter, scoped to each repo's actual stacks, and refreshed by the existing commit
hook. Build only the high-leverage pieces below; **explicitly do not** rebuild graphify's
full engine.

---

## What to build — RANKED by value / effort

### 1. A lean code-map artifact — the #1 borrow

Emit an auto-generated, always-current structural map into the knowledge layer:
**`knowledge/wiki/_codemap.md`** (leading underscore = generated, not hand-curated — same
convention for generated, non-curated files — leading underscore = generated). One section per module → its key
symbols (functions/classes/exports) → its call/import edges. The project's agent reads
*this* to learn "what's wired" instead of grepping — and it sits right next to the curated
"why" so the two are one hop apart.

- **Engine:** tree-sitter (a library; per-language grammars exist). Scope to the stacks
  actually in the target repo (e.g. Rust + TS for a Tauri app, PHP + JS for a server app,
  TS for a Node service). Do **not** ship graphify's 28-language engine; detect the repo's languages and
  load only those grammars.
- **Output shape:** Markdown (matches the wiki), with a stable, diff-friendly ordering
  (sort modules/symbols deterministically so the file only changes when the code does).
- **Header stamp:** mark it generated + dated + "do not hand-edit; regenerate" so no one
  treats it as curated source. Add a `confidence:`-style provenance note (see #4).
- **Effort:** moderate — the real work is wiring tree-sitter + a small emitter per stack.
  Everything below rides on this.

### 2. Extend the commit hook to refresh the code-map

The breadcrumb hook (`assets/journal-breadcrumb.sh`) already fires on every `git commit`
that advances `HEAD`. Add a step that regenerates `_codemap.md` (graphify's post-commit AST
rebuild — local, free, deterministic). The hook *already* has the HEAD-advance guard and
the silent-fail-never-block discipline, so this is a natural, low-risk add.

- Keep it cheap: regenerate only on commits that touched source files (the hook already
  computes the changed-file list); skip doc-only commits.
- Keep it non-blocking: same `exit 0`-on-any-problem contract — a map refresh must never
  block a commit.
- **Effort:** low — it's an add to an existing, proven hook.

### 3. "Consult the map before grepping" protocol line in the scaffolded CLAUDE.md

Add one rule to `assets/knowledge-CLAUDE.md.tmpl` (and to a freshly-scaffolded
`knowledge/CLAUDE.md`): *before grepping for where something lives, read
`wiki/_codemap.md`; grep only to confirm or when the map is stale.* Mirrors a
search-before-answer rule and turns the artifact into actual token savings.

- **Effort:** near-zero — one line in the template.

### 4. Edge / claim confidence tags — EXTRACTED vs INFERRED

The layer already carries article-level `confidence:`. Borrow graphify's *edge*-level
confidence: tag how-it-works claims in the wiki/ADRs as **`EXTRACTED`** (read directly from
code / the AST map) vs **`INFERRED`** (a human/agent read or extrapolation). A claim sourced
from `_codemap.md` is `EXTRACTED`; a claim about *intent* is `INFERRED`. Lets the layer say
not just "how confident" but "how this was known."

- **Effort:** low — a convention note in `references/formats.md` + a token in the codemap
  emitter; no engine work.

### 5. Union merge-driver on the generated map file

`_codemap.md` is generated, so two branches will produce conflicting versions on merge.
Apply graphify's technique: a git **union merge-driver** on the generated map (and any
future generated index) so merges never conflict — each side's lines union and the next
commit's hook regenerates a clean file anyway.

- Wire via `.gitattributes` (`knowledge/wiki/_codemap.md merge=union`) added by `init.sh`,
  plus a one-line setup note (the union driver is built into git).
- **Effort:** low — git config technique, no code.

---

## Explicitly SCOPED OUT — do not build

These are where graphify's real cost lives and where rebuilding is wasteful. The everyday
tool stays lean. If a big-repo graph is ever genuinely needed, **run graphify ad hoc**
(`graphifyy ... --obsidian`) against that one repo instead of carrying the weight in every
scaffold.

- **The full multi-language AST engine** (28 languages). Scope to each repo's real stacks.
- **The media pass** (faster-whisper audio/video transcription into the graph).
- **Leiden community detection** on the code graph.
- **HTML / Neo4j / GraphML visualization and exports.**
- **An MCP query server / embeddings / vector index** over the map. The Markdown artifact
  read directly (#1) is the retrieval layer; no separate query service for the everyday case.

---

## Why this shape (Dissent / Alternatives Considered)

- **Install graphify alongside each project** — rejected. Carries the full engine + media +
  viz cost into every repo and creates a second, parallel knowledge store to keep in sync.
  The directive is to borrow, not bolt on.
- **Vector/embedding index over the code instead of a Markdown map** — rejected for the
  everyday tool. Code is *structured*; a deterministic tree-sitter map beats embeddings on
  precision and cost for "what calls what," and stays a plain, diffable, git-friendly file
  that needs no runtime service. (Same structure-over-search logic graphify validates.)
- **Generate the map but keep it outside `knowledge/`** — rejected. The whole value is the
  WHAT/HOW sitting one hop from the WHY; co-locating in `wiki/` is the point.

## Suggested build order

#1 (the artifact + scoped tree-sitter emitter) is the foundation; everything else rides on
it. Then #2 (hook refresh) and #3 (protocol line) together make it self-maintaining and
actually used. #4 and #5 are cheap polish to land alongside or just after.

## Sources

- graphify — https://github.com/safishamsi/graphify (PyPI `graphifyy`).
- This repo's existing convention: `SKILL.md`, `references/formats.md`,
  `assets/journal-breadcrumb.sh` (the hook this extends),
  `assets/knowledge-CLAUDE.md.tmpl` (the file #3 edits).
