# session-service

A tiny HTTP session service. The build history, decision records, and the
curated wiki live in the knowledge layer.

**Read [`knowledge/AGENTS.md`](./knowledge/AGENTS.md) before doing architectural
work** — it holds the three rules, the formats, and the *why* behind how this is
built (notably why the session cache is SQLite+WAL and not in-memory or a JSON
file — a rationale that is not recoverable from the code alone).
