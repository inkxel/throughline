---
type: Decision
date: 2026-05-12
status: accepted
deciders: backend
related: [[session-cache]]
---

# Decision: Move the session cache from in-memory to SQLite with WAL

## Context

The session cache started life as a plain in-memory `Map` inside the process.
It was fast and trivial, but every restart wiped it: in dev that meant every
`node --watch` reload logged us out and dropped every open session, so the
inner loop was "change a line, lose all your sessions, re-auth, repeat." It made
testing anything that spanned a restart genuinely miserable, and it hid a real
production risk — a crash or deploy would silently sign every user out.

We wanted durability across restarts without standing up a separate service
(no Redis, no Postgres) for what is still a single-process toy. The session
record is tiny and the access pattern is simple key/value with a TTL.

## Decision

Back the session cache with **SQLite, in WAL (write-ahead logging) mode**, one
row per session (`id`, `payload`, `expires_at`). `journal_mode = WAL` plus
`synchronous = NORMAL`. Durability is now free — sessions survive restarts,
crashes, and `--watch` reloads — with no extra process to run.

## Consequences

- **Positive:** sessions persist across restarts; the dev loop stops fighting
  us; a crash no longer signs everyone out. No new infrastructure — it's an
  embedded file.
- **Positive:** WAL lets readers and the writer proceed concurrently without the
  reader-blocks-writer stalls of the default rollback journal — important once
  the validate path (a read) and the lastSeen update (a write) interleave under
  load.
- **Negative:** there's now an on-disk file (`data/sessions.db` + `-wal`/`-shm`
  sidecars) to gitignore and to clean up in tests. A hard `kill -9` mid-write
  can leave a `-wal` file that SQLite recovers on next open — fine, but worth
  knowing.
- **Neutral:** the cache's public API (`get` / `set` / `delete` / `sweepExpired`)
  is unchanged. Only the backend moved; nothing upstream of `SessionCache` knows.

## Dissent / Alternatives Considered

- **Keep the in-memory `Map`.** The status quo. Rejected: it loses everything on
  restart, which is the whole problem. Non-starter the moment durability matters.
- **A JSON file written on every change** (serialize the whole map to
  `sessions.json`). Tried this first — it *seemed* like the simplest possible
  durable store. It corrupted under concurrent writes: two near-simultaneous
  `set`s would both read-modify-write the same file and the second clobbered or
  truncated the first, leaving invalid JSON that failed to parse on next boot
  (so we'd lose the *entire* cache, worse than the in-memory version). We'd have
  had to hand-roll locking and atomic temp-file-rename — at which point we'd be
  badly reimplementing what SQLite already does correctly. Abandoned.
- **Redis / Postgres.** Real durable stores, but each is a separate service to
  run, configure, and depend on — overkill for a single-process service whose
  whole point is to stay small. Deferred; revisit only if this needs to scale
  horizontally across processes.

## Sources
- [[journal/2026-05-12-session-cache-durability]] — session where this surfaced
