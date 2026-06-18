# Knowledge Layer — formats & worked examples

The canonical templates live in the project's `knowledge/CLAUDE.md` (dropped by `init.sh`). This file adds **worked examples** and the **nuances** that make the system work in practice. Read it when seeding a freshly-scaffolded layer or when you need a concrete model to copy.

## Table of contents
1. Worked decision record (ADR)
2. Worked journal entry
3. Worked wiki article
4. The `confidence:` field — how to set it
5. Compile-pass handoff (optional, advanced)
6. Seeding a fresh layer — what good seed content looks like

---

## 1. Worked decision record

`decisions/2026-05-29-storage-file-not-keychain.md`:

```markdown
---
type: Decision
date: 2026-05-29
status: accepted
deciders: <name or role>
related: [[architecture]]
---

# Decision: Store the API key in a 0600 app-config file during dev, not the OS keychain

## Context
The keychain re-prompted for the login password on every relaunch because the
unsigned dev binary changes identity each rebuild. The prompt loop is unwinnable
for a dev build.

## Decision
Store the key as a 0600 file in the app config dir, env-var override available.
The keychain returns at release once the app is code-signed.

## Consequences
- **Positive:** zero prompts; key persists across rebuilds.
- **Negative:** plaintext on disk (owner-only). Acceptable for a revocable dev key.
- **Neutral:** same command surface — only the storage backend changed.

## Dissent / Alternatives Considered
- **Keep keychain + ad-hoc sign the dev binary** — fragile; signature still changes
  per rebuild, so prompts persist. Not worth it for dev.

## Sources
- [[journal/2026-05-29-foundation]] — session where this surfaced
```

The **Dissent / Alternatives Considered** section is what makes an ADR earn its keep — it records the road not taken so a future session doesn't re-litigate a settled choice. If there were genuinely no alternatives, write "None — only viable path given X" so the absence is explicit rather than ambiguous.

---

## 2. Worked journal entry

`journal/2026-05-29-foundation.md`:

```markdown
---
type: Journal
date: 2026-05-29
session: foundation
status: shipped
related: [[architecture]], [[vault-retrieval]]
---

# Foundation — scaffold, model wiring, vault grounding

## Context
First dev sessions. Repo was pre-seeded with docs only — no code.

## What changed
- Paths touched: `src-tauri/src/lib.rs`, `src/App.tsx`
- Subsystems: [[architecture]], [[vault-retrieval]]
- Behavior shipped: streaming chat + vault retrieval with source chips.

## Decisions made
- **File-based key storage** — [[decisions/2026-05-29-storage-file-not-keychain]]

## What was tried and abandoned
- **OS keychain for the dev key** — re-prompted every relaunch; dropped for a file.

## Open threads
- [ ] Command bar (global hotkey + second window) is next.

## Related
- Touched articles: [[architecture]], [[vault-retrieval]]
```

Journal entries are **written continuously**, not at session end — keep appending sections as the session goes. The commit-breadcrumb hook seeds `### HH:MM — hash` lines automatically; integrate them into the prose or leave them as a trailing commit log.

---

## 3. Worked wiki article

`wiki/architecture.md`:

```markdown
---
name: architecture
type: subsystem
created: 2026-05-31
last_updated: 2026-05-31
confidence: high
related: [[vault-retrieval]], [[build-status]]
---

# Architecture — how the app is built

[Prose describing the subsystem, how the pieces compose, the hard constraints.]

## Context log

### 2026-05-31 — Article created
Documents the current state. [[journal/2026-05-29-foundation]]
```

Wiki articles are **append-only context logs** — never rewrite the body; add a dated entry under `## Context log` when something changes, and bump `last_updated`.

---

## 4. The `confidence:` field

- **high** — observed in code, ratified in a decision record, or repeatedly confirmed across sessions
- **medium** — stated once, documented in one source, not yet contradicted
- **low** — assembled from inference or a single source; treat as provisional
- **speculative** — a read or extrapolation; flag for revisit before acting on it

Set it when an article is touched for a real reason (per Rule 2), not in a bulk pass. It lets contradiction-tracking do nuanced work — a contradicted "high" claim matters more than a contradicted "speculative" one.

### Claim-level provenance tags (EXTRACTED vs INFERRED)

Beyond article-level `confidence:`, individual how-it-works claims inside wiki articles and ADRs can carry a provenance tag to indicate *how the claim was known* — not just how confident we are:

- **`EXTRACTED`** — the claim comes directly from source code or the AST map (`knowledge/wiki/_codemap.md`). It's ground truth for the current state of the code. Example: "`vault.rs` exports `build_context`, `search_digest`, `read_note` `[EXTRACTED]`."
- **`INFERRED`** — the claim was assembled by reading, extrapolation, or reasoning about intent. Should be verified before being acted on. Example: "The agent loop is designed to be stateless between turns `[INFERRED]`."

Use these inline, sparingly — only when the distinction between "I read it in the code" and "I reasoned about the code" matters for the reader. Claims sourced from `_codemap.md` are automatically `EXTRACTED`. Claims in ADRs about *intent or rationale* are always `INFERRED` (decision records capture human reasoning, not code facts).

---

## 5. Compile-pass handoff (optional, advanced)

When the end-of-session compile pass (Rule 1) promotes journal content into the wiki, record what graduated and why — so "what moved to the wiki" is a checkable trail, not a vibe. Add this to the session's journal entry:

```markdown
## Compile pass — YYYY-MM-DD
- **Trigger fired (Rule 2):** [1: new subsystem | 2: contradicted decision | 3: explicit]
- **Articles touched:** [[article-1]]
- **What was promoted:** one line per article
- **What was NOT promoted (and why):** journal content that stayed in the firehose
- **Open follow-ups:** items needing another session before they're wiki-worthy
```

The compile pass is allowed to be a no-op — most sessions won't fire a Rule 2 trigger. The point is that *when* a wiki write happens, the decision to write was explicit.

---

## 6. Seeding a fresh layer — what good seed content looks like

An empty knowledge layer has no gravity; nobody reads or maintains it. Give it a starting mass drawn from the project's *actual* current state:

- **Decision records for decisions already baked in.** Read the architecture, README, config, and recent `git log`. Anywhere there's a "we chose X" — especially with a rejected alternative — write an ADR. These are the highest-value seed: they're the rationale most likely to be lost.
- **One backfill journal entry** summarizing where the project stands today and what's next. If the repo has history, reconstruct the arc briefly.
- **Wiki articles only for real subsystems** with content worth curating. Don't manufacture empty shells. A `build-status.md` (milestone tracker) and a `glossary.md` are usually worth it; a `roadmap.md` parking lot too. Speculative `[[wikilinks]]` to not-yet-written articles are *good* — they mark gaps, not errors.
- **A pointer from the repo-root `CLAUDE.md`/`README`** to `knowledge/CLAUDE.md`, so fresh sessions discover the layer.

Use absolute `YYYY-MM-DD` dates (convert "today") for all filenames and frontmatter.
