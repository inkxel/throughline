# Throughline

**An OKF-native memory layer for code repos — so the *why* behind your project survives across AI coding sessions.** Drop it in and your repo starts keeping its own build history: what you decided, what you tried, what you abandoned, and why. One command exports the whole thing as a knowledge bundle in **Google's Open Knowledge Format** — validated against Google's own reference tooling, not just asserted.

> **Status:** v1. Plain markdown, a commit-triggered auto-journal, and an OKF export that passes Google's reference validator on every concept. No database, no service, no account.

---

## Why this exists

Coding agents are brilliant and amnesiac. Every session starts cold. The code survives — that's what git is for — but the *reasoning* evaporates the moment the context window closes. Why did you reach for SQLite over Postgres? Why is that retry loop there? What did you already rule out so nobody re-litigates it next week?

For a big team, tribal knowledge papers over the gap. For a solo builder or a small crew, there is no tribe. The lost rationale **is** the risk. You ship something clever on Tuesday, and by Friday neither you nor the agent can reconstruct why it's shaped the way it is — so you rebuild it, or worse, you break it.

The wager is simple: the cheapest place to capture a decision is the moment you make it, and the cheapest moment is the commit. So this hangs the memory layer off the one ritual you already do.

## What you get

A scaffold and a hook. That's the whole product.

The scaffold is a `knowledge/` folder with five places for memory to live. The `journal/` is append-only, one entry per session — the running log of what happened. `decisions/` holds ADRs, one file per real call, with the context and the consequences. The `wiki/` is the curated, durable view — the stuff that stays true. `research/` is for findings, evaluations, the option weigh-ups that fed a decision. And a roadmap parking lot lives in the wiki — the "not now, but don't forget" pile.

The auto-journal is a commit-triggered hook. Every time a commit advances HEAD, it drops a breadcrumb into today's journal — time, hash, subject, files touched — then nudges the agent to write the *why* while it's still warm, not at session end when it's already gone.

The OKF export turns the whole thing into a spec-conformant bundle in **Google's Open Knowledge Format** with one command. It's not just a docs folder — it speaks the emerging standard. More on that below.

No database. No service. No account. Markdown and a shell hook.

## Install

One line:

```bash
curl -fsSL https://raw.githubusercontent.com/inkxel/throughline/main/install.sh | bash
```

Then scaffold a repo:

```bash
throughline init        # from inside any git repo
```

It's idempotent and merge-aware — safe to re-run and never clobbers an existing `knowledge/`. The default hook is a plain git `post-commit`, so it works with any tool: Cursor, Codex, plain-git humans. Inside Claude Code, pass `--claude-code` for the richer PostToolUse hook on top.

## The three rules

The whole discipline fits on a napkin. The scaffold enforces the structure — you (and the agent) hold these:

1. **Journal at the commit, not the session end.** The commit is the marker for a real move. When the hook breadcrumbs, write the why *then* — rationale, dead ends, open threads. Deferred memory is lost memory.
2. **A decision worth arguing about gets an ADR.** If you'd be annoyed to re-explain it in a month, it's a decision record. Context, the call, the consequences. One file.
3. **The wiki is derived, never authoritative.** Journal and decisions are the source of truth. The wiki is the compiled, cleaned-up view. When they disagree, the raw source wins — and you preserve the contradiction instead of silently smoothing it over.

## Worked example — recall actually working

The point isn't the folder. The point is that an agent can later recover a *why*
it otherwise has no way to know. So here's that, as a controlled before/after.

Same small service, two copies. Same `src/`, byte-for-byte. One copy carries a
Throughline `knowledge/` layer; the other doesn't. The session cache runs on
SQLite in WAL mode, and the code says *that* — `journal_mode = WAL` — and nothing
about *why*. Then ask both copies the obvious review question:

> *"Why does this use SQLite with WAL for the session cache instead of just
> keeping it in memory?"*

**Without the layer**, the agent reads every file, searches for any trace of the
reasoning, and answers honestly: it can't find one.

> I cannot determine the reasoning from the code itself. There's no comment, no
> ADR, no commit history that says why SQLite-with-WAL over an in-memory cache —
> the only hit is the bare `pragma` line. So I will not invent one.

Right call — it refused to make something up. But the answer the reviewer needed
left with the session that made the decision.

**With the layer**, same code, same question. The agent confirms the pragmas, then
reads the reasoning out of `knowledge/` and cites where it came from.

> Durability across restarts, without standing up a separate service. The
> in-memory `Map` was the original design — rejected because `node --watch` wiped
> every session on each save ("change a line, lose all your sessions"). A JSON file
> was tried first and abandoned — it corrupted under concurrent writes. SQLite +
> WAL gave durability for free, no extra service. *(Source:
> `knowledge/decisions/2026-05-12-session-cache-sqlite-wal.md`, the journal, and
> the wiki.)*

Identical bytes of code. One side reconstructs the two dead ends — the `Map`, the
JSON file that corrupted — so nobody re-litigates them. The other side can't, so
someone "simplifies" it back to a JSON file in six months and walks into the same
corruption bug. That recovered paragraph is the thing you can never reconstruct
from the code, and it's exactly what evaporates when a session closes.

The full demo — both real blind-test answers verbatim, plus a `grep` that proves
the *why* genuinely isn't in the code — lives in
[`examples/recall/`](examples/recall/). Run it against your own agent.

### How the *why* got there

It's captured at the commit, not dredged up later. Do what you'd do anyway:

```bash
$ git add -A && git commit -m "swap the in-memory cache for SQLite"
```

The hook fires on a HEAD advance and drops a breadcrumb into today's journal, then
nudges the agent:

> 📓 Committed a1b9f3c (swap the in-memory cache for SQLite). A breadcrumb was
> auto-appended. Add the WHY now while it's fresh — rationale, what was
> tried/abandoned, open threads — don't defer to session end.

So the agent fills it in right there, while the context is still warm — which is
the only moment that paragraph is cheap to write. Failed commits never breadcrumb;
the hook only fires when HEAD actually moves. No noise.

## The OKF-native angle

This is the part that makes it more than a tidy folder convention. Run the export and it emits a bundle in **OKF — Google's Open Knowledge Format** (v0.1, [GoogleCloudPlatform/knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog)), the standard Google just published for agent-readable knowledge — the formalized version of the "LLM wiki" pattern this whole layer is built on.

```bash
python3 scripts/okf-export.py knowledge/ -o okf/
```

It converts `[[wikilinks]]` to bundle-relative markdown links, normalizes the frontmatter so every concept carries the required fields, generates the per-directory `index.md` files and a date-grouped `log.md`, and declares `okf_version`. Pure stdlib — no dependencies. Every concept it emits passes Google's own reference validator (`OKFDocument.validate()`) — that's a real bar, not a self-graded one. You author in the comfortable convention, and the export speaks the standard.

Here's the bet. The file format is the easy part — Google specced that. The hard part is the system that *maintains* the knowledge: the journal-to-wiki compile pass, the freshness and confidence signals, the discipline of preserving a contradiction instead of silently smoothing it. OKF describes the format; it doesn't give you any of that. Throughline is that system, and it happens to export clean into the standard. So you get both — a knowledge folder that earns its keep day to day, **and** a bundle that speaks the protocol the rest of the field is moving toward.

The spec map lives at [`references/okf-compatibility.md`](references/okf-compatibility.md) and travels with the repo.

## Repo layout

```
README.md                          ← you are here
LICENSE                            ← Apache-2.0
AGENTS.md / CLAUDE.md              ← how an agent should use this repo (pointer)
install.sh                         ← the curl|bash one-liner target
scripts/
  init.sh                          ← scaffolds knowledge/ + installs the hook
  install-hook.sh                  ← sets up the git post-commit hook
  okf-export.py                    ← emits a spec-conformant OKF bundle (stdlib)
  hooks/post-commit                ← the tool-agnostic auto-journal hook (default)
assets/
  journal-breadcrumb.sh            ← optional Claude Code PostToolUse hook
  knowledge-AGENTS.md.tmpl         ← the orientation file dropped into knowledge/
  knowledge-CLAUDE.md.pointer.tmpl ← the thin per-project pointer
references/
  formats.md                       ← worked examples: ADR, journal entry, wiki article
  readme-template.md               ← the README standard projects scaffold from
  okf-compatibility.md             ← OKF spec map (the standards bridge)
```

## Also in the box (beta)

There's an optional **code-map** subsystem — a tree-sitter structural index of the repo that regenerates on commit, so an agent can orient on the code's shape without reading every file. It's wired but kept off the headline path: it pulls in `tree-sitter` and is still settling. Treat it as opt-in. Notes in `references/roadmap-codemap.md`.

## License

Apache-2.0. Take it, fork it, ship it. Apache over MIT on purpose — it carries a patent grant and matches OKF's own license, which keeps the door open to feeding work back upstream.
