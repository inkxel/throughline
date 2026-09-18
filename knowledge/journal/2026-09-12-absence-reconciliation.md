---
date: 2026-09-12
session: absence-reconciliation fix for never_landed.py
status: shipped
related: [[docs/never-landed]]
---

# `never_landed.py` — reconciled removals stop reading as bugs

The checker had a real gap: a target the log claimed as created, deliberately
removed later, and recorded as such by the producer, was indistinguishable
from a genuine producer bug — both just read as "missing from the store."
open-knowledge-format#11 (where the deletion-semantics work from
knowledge-catalog#207 moved) has the real-world shape for fixing this,
contributed by @andrewcrenshaw (producer, `remember-okf-sample-bundle`) and
confirmed by @leesharks000 (consumer side): a manifest's `absences` map,
keyed by id, with `presence: "removed"` records, plus a sibling
`absenceReconciliation` key proving the absence pass actually ran.

## Change — `scripts/never_landed.py`
- New `known_absences(path)`: reads that manifest shape, returns
  `(removed_ids, ran)`.
- New `_norm_key()`: normalises an id to its final path segment, slugified —
  the shipped bundle keys `entries` by bare id and `absences` by full URI;
  without normalising both sides the same way, a present absence record
  reads as missing.
- `check_log()` takes `absences_path`. For a claim missing from the known
  store: reconciled removal (`presence: "removed"`, pass confirmed ran) is
  excluded outright; if the manifest has no `absenceReconciliation` marker at
  all, the finding is downgraded to a new `unknown` bucket instead of either
  `never_landed` or silently clean — an unreconciled absence map proves
  nothing about what it doesn't contain. Nothing changes when `--absences`
  isn't passed.
- CLI: new `--absences MANIFEST.json`. Output and exit code now also report
  `unknown_count`/`unknown`.

## Verification
`--selftest` extended with the removed/unknown/never_landed three-way split,
including a case exercising the bare-id-vs-URI key mismatch. Full run:

```
OK selftest — claim/reference split, alias + frontmatter-id resolution,
min-dating, one-group patterns, empty-vs-unmatched log, absence
reconciliation (removed/unknown/never_landed)
```

No local `cases.json` fixture exists to re-run the 111-case conformance
harness against; this is the `--selftest` evidence for the draft GitHub
comment in [[okf-reengagement-plan]].

## Docs
`docs/never-landed.md` — new section on the absences gap, usage example,
and a `Related` link to open-knowledge-format#11.
