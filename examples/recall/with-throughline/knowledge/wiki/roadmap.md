---
title: Roadmap
type: Reference
---

# Roadmap

The "not now, but don't forget" pile — ideas and improvements parked until the time is right.

- **Smarter eviction.** Current policy is lazy-on-read + a 5-minute sweep. Fine at this scale; revisit if the working set grows. See [[session-cache]].
- **Multi-process story.** If session-service ever runs as more than one process, the embedded-SQLite choice needs a rethink (Redis/Postgres were deferred, not dismissed — see [[decisions/2026-05-12-session-cache-sqlite-wal]]).
