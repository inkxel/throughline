---
type: Journal
date: 2026-05-12
session: session-cache-durability
status: shipped
related: [[session-cache]]
---

# Session cache — making it survive a restart

## Context
The session cache was an in-memory `Map`. Every restart blew it away. In dev,
`node --watch` reloads on every save, so each edit signed us out and dropped all
open sessions — the inner loop was unworkable. Same shape in prod: any crash or
deploy would silently sign every user out. Goal for the session: give the cache
durability without dragging in a separate service.

## What changed
- Paths touched: `src/cache.js` (in-memory `Map` → SQLite-backed store), plus
  `package.json` (added `better-sqlite3`), and `.gitignore` (`data/`, `*.db*`).
- Subsystems affected: [[session-cache]]
- Behavior shipped: sessions now persist across restarts, crashes, and watch
  reloads. The cache's public API (`get`/`set`/`delete`/`sweepExpired`) is
  unchanged — only the backend moved.

## Decisions made
- **SQLite in WAL mode for the session cache** — durability for free, no new
  service to run. Rationale + the two rejected alternatives:
  [[decisions/2026-05-12-session-cache-sqlite-wal]]

## What was tried and abandoned
- **In-memory `Map`** — the starting point. Loses everything on restart; that's
  the entire problem we were solving. Gone.
- **JSON file rewritten on every change** — tried it FIRST as the simplest
  durable option. It corrupted under concurrent writes: two overlapping `set`s
  each did a read-modify-write of the whole file and the second clobbered the
  first, leaving unparseable JSON that wiped the *whole* cache on next boot.
  Fixing it meant hand-rolling locking + atomic temp-file rename — i.e. poorly
  reinventing SQLite. Dropped it and reached for SQLite instead.

Neither of these dead ends is visible in the code that shipped — `cache.js` just
shows the SQLite+WAL answer. That's exactly why this entry exists.

## Open threads
- [ ] Eviction is still naive — we only drop a row lazily on read past TTL plus a
  5-minute `sweepExpired` interval. Fine now; revisit if the working set grows.
- [ ] If this ever needs to span multiple processes, the embedded-SQLite choice
  is back on the table (see the Redis/Postgres note in the ADR).

## Related
- Touched articles: [[session-cache]]
