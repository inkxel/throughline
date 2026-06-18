---
name: session-cache
type: subsystem
created: 2026-06-17
last_updated: 2026-06-17
confidence: high
related: [[roadmap]]
---

# Session cache — durable key/value store for sessions

`src/cache.js` exports `SessionCache` `[EXTRACTED]` — a persistent key/value
store keyed by session id, holding the serialized payload and an expiry
timestamp. `src/sessions.js`'s `SessionManager` sits on top of it and never
touches the backend directly `[EXTRACTED]`.

## How it works
- One SQLite table, `sessions (id PRIMARY KEY, payload TEXT, expires_at INTEGER)`,
  with an index on `expires_at` `[EXTRACTED]`.
- Opens in **WAL mode** (`journal_mode = WAL`, `synchronous = NORMAL`) `[EXTRACTED]`.
- Reads drop a row lazily once it's past TTL; a 5-minute `sweepExpired` interval
  in `server.js` reaps the rest `[EXTRACTED]`.
- Public API: `get` / `set` / `delete` / `sweepExpired` / `close`. Storage backend
  is fully hidden behind it `[EXTRACTED]`.

## Why SQLite + WAL (the part the code doesn't tell you)
The backend was an in-memory `Map` first, then briefly a JSON file. Both were
rejected — the `Map` lost everything on restart (miserable dev loop, silent
prod sign-outs), and the JSON file corrupted under concurrent writes. SQLite+WAL
gave durability with no extra service. **This rationale is `INFERRED` from the
build history, not visible in the code** — the shipped `cache.js` shows only the
final SQLite answer. Full record: [[decisions/2026-05-12-session-cache-sqlite-wal]].

## Context log

### 2026-06-17 — Article created
Documents the cache subsystem and, critically, the un-inferable *why* behind the
SQLite+WAL choice. Sourced from the backfill decision record and journal entry
for the 2026-05-12 durability change. [[journal/2026-05-12-session-cache-durability]]
