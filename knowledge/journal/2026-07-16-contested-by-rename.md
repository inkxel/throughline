---
date: 2026-07-16
session: contested-by rename
status: shipped
related: [[2026-07-11-authored-basis-lands]]
---

# `contradicts` → `contested_by` (emit rename, read back-compat)

#158 converged on `contested_by` as the name for the symmetric dispute edge (distinct from the asymmetric `supersedes`). Renamed the emitted key accordingly while keeping the legacy `contradicts:` key readable.

## Change — `scripts/okf-export.py`
- The `--reliability` typed-edge loop now maps output-key → accepted source-keys: `supersedes` ← (`supersedes`); `contested_by` ← (`contested_by`, `contradicts`). Reads both, dedups, and always **emits `contested_by`** — the legacy `contradicts:` key is normalized on write.
- Updated the `--reliability` help string to `supersedes`/`contested_by` (+ the back-compat note).
- No corpus to migrate — no source doc carried the key yet.

## Example — `examples/okf-reliability/`
Added a dispute pair exercising both paths: `cpi-reading.md` declares the new `contested_by:` key; new `cpi-reading-official.md` declares the legacy `contradicts:` key. `okf-export.py --reliability` emits `contested_by:` for both; no stray `contradicts:` key survives. Verified against `/tmp` export.

Owed to Andrew (he's putting Tucker's name on his commit).
