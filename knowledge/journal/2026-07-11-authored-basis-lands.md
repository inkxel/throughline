---
type: Journal
date: 2026-07-11
session: authored-basis-lands
status: shipped
related: []
---

# Land `authored` in the basis enum — closing the gap hq-austin.md was built to name

## Context
On 2026-06-29, testing the OKF reliability object (#151/#159) against Throughline's own authored-corpus content, the `basis` enum had no honest value for a human-authored fact — a curated wiki article or an ADR isn't `live-source`, `computed`, `forecast`, or `inferred`. That gap became `hq-austin.md`, a fixture built specifically to fail the schema floor on purpose rather than paper over it. The finding went to #159 the same day; `authored` was agreed with `@Dynamicfeedai` and `@K4uP` by 2026-06-30 (ordering: `live-source > authored > partner-attested > vendor-doc > forecast > computed > inferred`), but stayed unlanded in the hosted schema for two weeks. On 2026-07-11, `@K4uP` posted a ready-to-apply schema delta plus three conformance vectors on #159, noting a fifth production system (Lexenne/`remember`, #182) had independently re-derived the same missing value.

## What changed
- Paths touched: `scripts/okf-export.py` (`BASIS_ENUM`), `examples/okf-reliability/knowledge/wiki/hq-austin.md`
- Subsystems affected: the `--reliability` export mode
- Behavior shipped: `authored` added to `BASIS_ENUM`; `hq-austin.md` now emits `basis: authored` instead of no `basis` at all — the fixture that was built to fail now passes, honestly.

## Decisions made
- **Adopt `authored` at the agreed slot** — `live-source > authored > partner-attested > vendor-doc > forecast > computed > inferred`. Rationale: matches the 2026-06-29/30 cross-shape agreement on #159 and K4uP's 2026-07-11 delta verbatim; no independent judgment call, a mechanical adoption of consensus.

## Validation
Fetched the live hosted schema (`https://dynamicfeed.ai/schemas/okf-reliability-v1.json`), patched it locally with K4uP's diff, and checked both the real exported `hq-austin.md` reliability object and K4uP's three posted vectors (V1/V2/V3) against both schemas using Python's `jsonschema` (draft 2020-12) — a different validator than the `ajv` runs already reported upstream, so this is independent corroboration, not a repeat. All four cases matched their expected pass/fail exactly: Throughline's real export and V1 both reject on the hosted schema and pass on the patched one; V2 (the `#182` `asserted` spelling) and V3 (`verified:true` at `sources:1`) both correctly reject on both, confirming the closed union and honesty rule 2 still hold with the new value in place.

## What was tried and abandoned
Nothing abandoned this session — straight adoption of an already-settled cross-shape agreement.

## Open threads
- [ ] The `okf-reliability-conformance` branch (this work included) has been open since 2026-07-01 and never merged to `main` — worth doing regardless of upstream timing.
- [ ] Today's `#158` thread (typed cross-concept edges) converged on `contested_by` as the name for the symmetric dispute edge, distinct from the asymmetric `supersedes`. Throughline currently emits `supersedes`/`contradicts` as flat lists with no attribution/resolution structure — porting FOUNDRY's now-proven append-only affirmation-event pattern (who/when/why, three reader-distinguishable states) onto these edges would bring Throughline's typed-edge story in line with where that thread just landed, and give it a real implementation to cite.
- [ ] No committed conformance-vector validator exists in this repo — the 2026-06-29 and 2026-07-11 cross-checks were both one-off scripts. Worth committing a small `scripts/` validator so re-running against a future schema delta doesn't require rebuilding the harness each time.

## Related
- Touched articles: none yet — `wiki/` doesn't exist in this repo's `knowledge/` layer yet.
