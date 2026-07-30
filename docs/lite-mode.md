# `--lite` — the whole knowledge layer in one file

**Status:** spec, not built. 2026-07-27.

## The problem

Throughline's scaffold is five places for memory to live: `wiki/`, `decisions/`, `research/`, `sources/`, and `journal/` (or `ledger/`). That's correct for a project with real surface area. On a small repo — a script, a plugin, a spike, a side project — it's a seven-folder ceremony around what amounts to a page of prose, and the honest outcome is that nobody sets it up at all.

That's most repos. The long tail is where the memory layer would help most and where the scaffold is most obviously too much.

## The shape

`throughline init --lite` produces exactly one file: **`KNOWLEDGE.md`** at repo root.

Everything the full scaffold spreads across folders becomes a section. The three rules are unchanged — journal is append-only, decisions get records, the wiki is derived and never authoritative. Only the filesystem shape changes.

```markdown
# <project> — Knowledge

<!-- throughline: lite/1 · subject: <name> · type: project -->

Anyone (human or agent) picking this repo up cold should read this file first.

## Wiki

### Session cache
<!-- concept · confidence: medium · updated: 2026-07-27 -->
The durable, curated view. Derived from decisions and journal — when they
disagree, the raw entry wins and the contradiction gets preserved, not smoothed.

## Decisions

### 2026-05-12 — SQLite in WAL mode for the session cache
<!-- decision · status: accepted -->
**Context.** …
**Decision.** …
**Consequences.** …

## Research

### 2026-05-10 — Cache backend weigh-up
<!-- research -->
…

## Roadmap
Not now, but don't forget.
- [ ] …

## Journal
<!-- append-only · newest at the bottom · nothing below this heading gets rewritten -->

### 2026-05-12
- `14:02` · `a3f9c21` · "fix cache invalidation" · `src/cache.py`
  **why:** …
```

## Why the journal goes last, and why that's the whole trick

The objection to collapsing a knowledge layer is that appends become read-modify-write. In a folder, a journal entry is `>>`; in one file it's a rewrite of the whole document.

That objection only bites if the append lands in the middle. **Put the journal at the bottom and the hot path stays an append** — the post-commit hook writes to EOF and never touches a byte above it. Wiki and decision edits are genuine rewrites, but those are human-paced and rare. The high-frequency writer keeps its cheap path.

This is the load-bearing design choice. Everything else is convention.

## Section contract

- `##` headings are areas. Fixed set: **Wiki · Decisions · Research · Roadmap · Journal**. Absent sections are legal; the file grows into them.
- `###` headings are concepts, one per entry.
- Metadata rides in an HTML comment directly under the heading. Invisible in rendered markdown, trivially parseable, no frontmatter clutter mid-document.
- `[[wikilinks]]` still work — they resolve to `###` headings in the same file. The link graph survives intact; it just becomes intra-document.
- `sources/` has no section. Raw material — transcripts, exports, dumps — stays on disk as files. It was never the knowledge layer, it's what the layer is derived from.

## Export is unchanged, which is the point

OKF conformance requires one concept per file with real frontmatter (v0.2 §11). A single markdown file **cannot be** an OKF bundle.

It doesn't need to be. `throughline export` already exists to turn a comfortable authoring convention into a conformant bundle — lite just makes the authoring side smaller. The exporter explodes `###` sections into per-concept files, lifts each HTML-comment block into real frontmatter, generates the `index.md` files and the date-grouped `log.md`, and clears the same bar it clears today: every concept passes Google's reference validator.

The project's existing bet — *author in the comfortable convention, export speaks the standard* — is what makes lite mode possible without a second exporter. One code path, two authoring shapes.

## Graduating

Lite is a starting point, not a ceiling.

- `throughline` warns once past **50 KB**: *"KNOWLEDGE.md is 52 KB — consider `throughline split`."* One line, no nagging, never blocks.
- `throughline split` migrates the file into the full scaffold: each `###` becomes a file in its section's folder, the journal splits by date, metadata comments become frontmatter, `[[wikilinks]]` keep resolving because they were always basename-based. Reversible in principle, though nobody will.

**Why 50 KB.** Around 12K tokens — an agent can hold the whole layer at once, which is precisely the advantage of a single file. Past that you're paying to load nine irrelevant sections to answer one question, and the diffs get noisy. The number is a prompt to think, not a hard gate.

## When lite is wrong

- **More than one writer.** Two agents, or an agent and a person, working concurrently will conflict on every write. Folders isolate; one file doesn't. This is the real ceiling, and it arrives long before 50 KB.
- **Anything with a compliance or provenance story.** Per-file history and per-file frontmatter are worth the ceremony.
- **A project already past the threshold.** Don't collapse a working layer to prove a point.

## Naming — `KNOWLEDGE.md`, not `.knowledge.md`

A dotfile is the intuitive choice and it's wrong here.

Agents globbing `**/*.md` **miss dotfiles by default** in most implementations — you'd be hiding the file from the exact readers it exists for. GitHub renders dotfiles in the tree anyway, so the tidiness is mostly imagined. And it invites `.gitignore` collisions.

`KNOWLEDGE.md` sits next to `README.md`, `CLAUDE.md`, `AGENTS.md` — the established convention for "this file is infrastructure, read it first." Sorts to the top, every tool finds it, no configuration.

## Build order

1. `init --lite` emits the skeleton with the fixed section set.
2. Teach the post-commit hook to append under `## Journal` at EOF when `KNOWLEDGE.md` exists and no `knowledge/` tree does. Same silent-exit-0 behaviour on any problem — journaling never blocks a commit.
3. `export` learns to explode a lite file into concepts before the existing OKF path runs. Validator bar unchanged.
4. `split`, plus the 50 KB warning.

1 and 2 alone are shippable and useful. 3 is what makes it a Throughline feature rather than a file-naming convention.

## Open

- Does `--lite` compose with `--type person|org|brand|project`, or is it project-only? Person bundles carry `stm/`, which has no obvious single-file home.
- Should `split` be automatic at some hard ceiling, or always a human call? Leaning human — silent restructuring of someone's knowledge layer is the kind of surprise that loses trust.
