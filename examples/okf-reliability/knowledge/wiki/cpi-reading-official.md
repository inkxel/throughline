---
type: Reference
title: CPI reading (May 2026, official BLS)
confidence: high
basis: authored
contradicts: "[[cpi-reading]]"
last_updated: 2026-06-20
---
# CPI reading (May 2026, official BLS)
The official BLS release for May 2026. This concept declares the dispute with the **legacy `contradicts:` key on purpose** — `okf-export.py --reliability` reads it and normalizes it to `contested_by` on write, exercising the back-compat path (#158). Both this concept and [[cpi-reading]] therefore emit a `contested_by:` edge.
