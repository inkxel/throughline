# Recall demo — watch an agent recover a *why* it has no way to know

Same code. Same question. One repo has a memory, the other doesn't. That's the
whole experiment, and the result is the pitch.

`session-service` is a small HTTP service that issues, validates, and revokes
sessions. Its session cache (`src/cache.js`) runs on **SQLite in WAL mode** — the
code opens the database and sets `journal_mode = WAL`, `synchronous = NORMAL`
(lines 15–17), and that's all it says. No comment about why SQLite. No dead code
hinting at what came before. The destination is in the code; the road to it isn't.

So we asked an agent the obvious code-review question, against each side:

> *"Why does this project use SQLite (with WAL) for the session cache instead of
> just keeping the cache in memory?"*

Two real blind-test runs. Verbatim below — nothing trimmed for effect.

```
recall/
  with-throughline/      ← same code + a Throughline knowledge layer
  without-throughline/   ← the same code, no knowledge layer (the control)
```

The `src/` directories are **byte-for-byte identical** (`diff -r` them — empty).
The only difference is the `knowledge/` folder in `with-throughline/`.

---

## The two answers, side by side

### ❌ Without the layer (control)

The agent read every file in `without-throughline/`, searched for any trace of
the reasoning, and landed honestly on: *it isn't here.*

> **Short answer: I cannot determine the reasoning from the code itself. The repo
> does not tell me *why*.**
>
> I read every file. The code *establishes* that the cache is durable and on-disk
> — `better-sqlite3`, `journal_mode = WAL`, a `sessions(id, payload, expires_at)`
> table that persists across restarts. WAL + `synchronous = NORMAL` is a known
> config that allows concurrent readers alongside a writer.
>
> But none of that explains the actual decision. There is **no comment, no commit
> history, no ADR, no design note, and no variable naming** that states why
> SQLite-with-WAL was chosen over an in-memory cache. I searched for exactly that
> (`in-memory`, `restart`, `durable`, `corrupt`, `concurrent`, `json file`,
> `crash`, `wal`, `why`) and the only hit is the bare `pragma` line — no rationale
> attached. **So I will not invent one.**
>
> The honest answer is: the code shows the destination (durable SQLite + WAL), and
> the *why behind it* — what was tried and rejected — is not preserved anywhere in
> that code.

Right call. Disciplined, even — it refused to make something up. But the answer
the reviewer actually needed walked out the door when the session that made the
decision closed.

### ✅ With the layer

Same code, same question. This time the agent confirms the pragmas in the code,
then pulls the reasoning straight out of the knowledge layer — and cites where
every piece came from.

> **Why SQLite (with WAL) instead of an in-memory cache?**
>
> Short version: **durability across restarts, without standing up a separate
> service.** The code in `src/cache.js` only shows the final answer (it opens
> SQLite with `journal_mode = WAL` and `synchronous = NORMAL`, lines 15–17). The
> *reasoning* lives in this repo's knowledge layer.
>
> **1. The in-memory `Map` was the original design — rejected because it lost
> everything on restart.** With `node --watch` reloading on every save, each edit
> logged everyone out: "change a line, lose all your sessions, re-auth, repeat."
> Same risk in prod — any crash or deploy would silently sign every user out.
>
> **2. A JSON file was tried first and abandoned — it corrupted under concurrent
> writes.** Two near-simultaneous `set`s each did a read-modify-write of the whole
> file; the second clobbered the first, leaving unparseable JSON that wiped the
> *entire* cache on next boot. Fixing it properly meant hand-rolling locking +
> atomic rename — "badly reimplementing what SQLite already does correctly."
>
> **3. SQLite + WAL gave durability for free, with no separate service.** Redis or
> Postgres are real durable stores, but each is "a separate service to run,
> configure, and depend on — overkill for a single-process service whose whole
> point is to stay small."
>
> **Why specifically WAL:** it "lets readers and the writer proceed concurrently
> without the reader-blocks-writer stalls of the default rollback journal —
> important once the validate path (a read) and the lastSeen update (a write)
> interleave under load."
>
> **Sourcing:** the code confirms *that* SQLite+WAL is used but never says why. The
> *why* comes entirely from three documents in the knowledge layer:
> `knowledge/decisions/2026-05-12-session-cache-sqlite-wal.md` (the ADR),
> `knowledge/journal/2026-05-12-session-cache-durability.md` (the build journal),
> and `knowledge/wiki/session-cache.md` (the compiled summary, which points back
> to the other two).

Notice it didn't get *less* honest with the layer — it got more precise. It still
flags that the rationale isn't derivable from the shipped code. It just has
somewhere real to read it from now.

---

## That's the gap

Identical code. One side reconstructs the two dead ends — the in-memory `Map`, the
JSON file that corrupted — and the reviewer never re-litigates them. The other side
can't, so someone "simplifies" `cache.js` back to a JSON file six months from now
and walks straight into the same corruption bug.

The rejected alternatives are the load-bearing knowledge, and they're exactly what
evaporates when a session closes. Throughline keeps them next to the code.

## Run it yourself — this isn't staged

The answers above are real blind-test runs, but don't take my word for it. First,
prove the *why* genuinely isn't in the code:

```bash
grep -rin -e in-memory -e restart -e durab -e corrupt -e concurrent \
          -e 'json file' -e Redis -e Postgres -e why \
    with-throughline/src without-throughline/src
# → no matches (the only WAL hit is the pragma line, with no comment)
```

Then ask the question against each side yourself:

- **`without-throughline/`** — point your agent at it, ask why SQLite over
  in-memory. Read all the code you like. The answer isn't there.
- **`with-throughline/`** — same question, same code. The answer is one file away:
  - `knowledge/decisions/2026-05-12-session-cache-sqlite-wal.md` (the ADR, with the
    **Dissent / Alternatives Considered** section holding both rejected options)
  - `knowledge/journal/2026-05-12-session-cache-durability.md` (the build session)
  - `knowledge/wiki/session-cache.md` (the curated view)

Answerable on one side, unanswerable on the other, with the same bytes of code.
That's the entire thing.

## How this was built

`with-throughline/` was scaffolded with the real CLI, then the seed was
hand-authored to record the actual past decision:

```bash
throughline init with-throughline/
# then: author knowledge/decisions/…, knowledge/journal/…, knowledge/wiki/…
```

It's its own small git repo so the scaffolder's `post-commit` hook scopes to it.
No commits are made here — the demo is about the recorded *why*, not the log.
