---
type: Journal
date: 2026-07-13
session: subject-type-scaffolding
status: shipped
related: []
---

# Teach init.sh about subject types — journal/ vs. ledger/, not one shape for everyone

## Context
Throughline's scaffold has always been type-blind: `init.sh` unconditionally created `wiki/decisions/journal/research`, regardless of what the target repo's own `.knowledge` subject actually was. That was fine while Throughline only ever scaffolded software repos (a `project`-type subject, by dotKnowledge SPEC.md's own type table). It stopped being fine once dotKnowledge's SPEC.md §3 formally split the temporal-record folder by subject perspective this week: `journal/` (first-person, human voice) is `person`-bundle-only; `org`/`brand`/`project` bundles get `ledger/` (agent-authored activity log) instead. Left alone, Throughline would stamp a `journal/` folder onto a `client.knowledge` or `cosi.knowledge` capsule the same way it does onto a code repo — reintroducing the exact voice-contamination problem the sources/ledger/journal split was built to fix, the moment anyone reaches for Throughline instead of hand-building a capsule.

Bundled with a second, unrelated-but-adjacent fix: `resolve()` in `okf-export.py` treats a concept's file path as its id, so renaming a file silently breaks (dangles) every `[[wikilink]]` pointing at the old name. Investigated whether to patch this too, and concluded no — OKF's own spec currently defines concept id as path-minus-`.md`, and a real fix (a path-independent stable id) is a live, cross-implementation OKF question already reported upstream (knowledge-catalog#120, commented 2026-07-08) with this exact Throughline finding as the evidence. Inventing a parallel stable-id scheme here, ahead of that landing, would just create a second incompatible convention — the wrong move twice over given this week's whole throughline has been about NOT doing that. Left a code comment pointing at #120 instead of a fix.

## What changed
- Paths touched: `scripts/init.sh`, `scripts/hooks/post-commit`, `assets/journal-breadcrumb.sh`, `scripts/install-hook.sh`, `scripts/okf-export.py`.
- `init.sh` gained `--type person|org|brand|project`. `org`/`brand`/`project` scaffold `ledger/` instead of `journal/`; `person` (or the flag omitted entirely) keeps the original `journal/` behavior unchanged — additive, not a breaking change for anything already scaffolded. `sources/` is now scaffolded unconditionally for every type (it was missing outright before — dotKnowledge SPEC.md §3 makes it universal, not conditional).
- The post-commit hook, the Claude-Code PostToolUse hook (`journal-breadcrumb.sh`), and `install-hook.sh` all now detect which of `ledger/`/`journal/` actually exists on disk and target that one — no new marker file, the folder's presence is the signal, since `init.sh` only ever creates one or the other.
- `okf-export.py`'s `DIR_TYPE` fallback gained `ledger: Ledger` and `sources: Source` entries, so concepts in either folder get typed correctly on export instead of falling back to the generic `Reference` default.
- Added a code comment at `resolve()` pointing at knowledge-catalog#120 instead of building a stable-id fix.

## Decisions made
- **`--type` is additive, default behavior is frozen.** Existing Throughline installs (all of them currently scaffolded pre-this-change, all effectively `project`-type by original intent) keep getting `journal/` unless `--type org|brand|project` is explicitly passed. Renaming the *default* to `ledger/` would have been more spec-correct in the abstract, but breaks `.gitignore`/`.gitattributes` entries and hook behavior on every repo already scaffolded — not worth it for a folder-name purity gain.
- **Don't build a stable-id scheme to close the `resolve()` gap** — correctly deferred to the live upstream question at #120, per the reply already posted there 2026-07-08.

## What was tried and abandoned
Considered making `ledger/` the new default (matching that Throughline's actual historical use has always been `project`-type code repos, which should never have gotten `journal/` in the first place). Abandoned — real backward-compat cost (breaks gitignore paths + hook targeting on every already-scaffolded repo) for a naming-purity gain that doesn't change behavior for anyone, since the folder name was never wrong for what it was doing, just imprecisely named before this week's spec work existed.

## Open threads
- [ ] `--type` isn't persisted anywhere explicit (e.g., in `capsule.yaml` or a marker file) — it's inferred purely from which folder exists. Fine for now (single source of truth, no drift risk), but if Throughline ever needs to know the type *before* the folder exists (e.g., to pick a template), it'll need a real place to read it from.
- [ ] `resolve()`'s path-as-id limitation stays open pending knowledge-catalog#120 — revisit once that lands, adopt whatever stable-id convention the wider OKF ecosystem converges on rather than inventing Throughline's own.

## Related
- Touched: `inkxel/dotKnowledge` SPEC.md §2/§3 (this week's sources/ledger/journal split, the thing this whole session's change exists to conform to).
