# session-service

A tiny HTTP session service. Issues, validates, and revokes sessions, backed by
a durable on-disk session cache.

## Run

```bash
npm install
npm start          # listens on :8787
```

## API

| Method | Path             | Body              | Result                       |
| ------ | ---------------- | ----------------- | ---------------------------- |
| POST   | `/sessions`      | `{ "userId": … }` | `201` + new session record   |
| GET    | `/sessions/:id`  | —                 | `200` record / `404` expired |
| DELETE | `/sessions/:id`  | —                 | `204`                        |

## Layout

```
src/
  server.js     HTTP surface
  sessions.js   SessionManager — issue / validate / revoke
  cache.js      SessionCache — durable key/value store (SQLite)
```

Expired sessions are reaped on a 5-minute interval; the cache also lazily drops
a session on read once it's past its TTL.

## Why it's shaped this way

The build history, decision records, and the curated wiki live in
[`knowledge/`](./knowledge/AGENTS.md) — including why the session cache is
SQLite+WAL rather than in-memory or a JSON file (a rationale that doesn't survive
in the code itself).
