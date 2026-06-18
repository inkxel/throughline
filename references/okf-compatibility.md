# OKF compatibility — the knowledge layer as an Open Knowledge Format bundle

> Maps this knowledge-layer convention to **Google's Open Knowledge Format (OKF) v0.1** (Apache-2.0, [GoogleCloudPlatform/knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog), spec: `okf/SPEC.md`). OKF formalizes the same Karpathy "LLM wiki" pattern this layer is built on — so we're ~90% conformant already, and the gap is the easy part. The *hard* part — the maintained-wiki machinery — is what this layer has and OKF only describes.

## Why this matters
OKF standardizes the **file format** for agent-readable knowledge. It explicitly does **not** provide the *enrichment + maintenance* system — the agent that reads a new source, integrates it, updates entity pages, and **flags contradictions**. This knowledge layer *is* that system (the journal→wiki compile pass, contradiction preservation, `confidence`/`last_compiled`, search-before-answer). So the positioning is: **"the OKF-native knowledge layer with the maintained wiki built in."** The format is the commodity; the maintenance discipline is the moat.

## OKF v0.1 in one screen
- **Bundle** = a directory tree of markdown files. **Concept** = one `.md` file. **Concept ID** = its path minus `.md`.
- **Conformance (the only hard rules, §9):**
  1. every non-reserved `.md` has a parseable YAML frontmatter block;
  2. every frontmatter has a **non-empty `type`**;
  3. `index.md` / `log.md` follow their format **when present**.
- Frontmatter: `type` (REQUIRED) · recommended `title`, `description`, `resource`, `timestamp` (ISO 8601), `tags` · extensions allowed (consumers preserve unknown keys).
- **Links = standard markdown**, bundle-relative `[t](/path.md)` recommended (NOT `[[wikilinks]]`). Broken links tolerated.
- Reserved files: **`index.md`** (no frontmatter except an optional bundle-root `okf_version`; body = sections of `* [Title](url) - desc`) and **`log.md`** (date-grouped `## YYYY-MM-DD` entries, newest first, `**Creation**`/`**Update**`/`**Deprecation**` prose).
- Conventional body headings: `# Schema`, `# Examples`, `# Citations`.

## Mapping: knowledge layer → OKF

| OKF concept | Knowledge layer today | Status |
|---|---|---|
| Bundle = dir of md | `knowledge/` (wiki/journal/decisions/research) | ✅ compatible — OKF lets producers organize freely |
| Concept = one md, has `type` | `wiki/*.md` carry `type` | ✅ wiki conformant · ⚠️ journal/decisions/research need `type` added |
| Concept ID = path | filename/path | ✅ |
| `description`, `timestamp` | lead sentence; `last_updated` (date) | ⚠️ add `description`; map `last_updated`→`timestamp` |
| `index.md` (progressive disclosure) | none (`CLAUDE.md` is orientation, not an index; `_codemap.md` is code, not concepts) | ➕ add a per-dir `index.md` generator |
| `log.md` (date-grouped history) | `journal/` + per-article `## Context log` + commit hook | ⚠️ content exists; add an OKF `log.md` *view* |
| links | `[[wikilinks]]` (resolve by basename) | ⚠️ divergent — see export below |
| `# Citations` | `sources:` frontmatter + inline links | ⚠️ map to a `# Citations` convention |
| (none) | **`confidence`, `last_compiled`, contradiction logs, the compile/extract pass** | ⭐ the differentiator — beyond the spec |

## The work (staged)

**1. Conformance (required, trivial):** add a non-empty `type` to journal / decisions / research frontmatter (`type: Journal` · `type: Decision` · `type: Research`). Wiki already has it. *This alone makes a `knowledge/` dir an OKF-conformant bundle.*

**2. Good-citizen enhancements (soft):**
- Add recommended frontmatter: `description` (one-line) and `timestamp` (ISO 8601; or keep `last_updated` and map it on export).
- Generate a per-directory **`index.md`** (progressive disclosure) from frontmatter `description`s — a sibling of the `_codemap.md` generator. Distinct from `CLAUDE.md` (which stays the agent-orientation file).
- Maintain a **`log.md`** at the bundle root — the commit-breadcrumb hook already emits dated entries; point it at `log.md` in OKF form.
- Map `sources:` → a `# Citations` section convention.
- Declare `okf_version: "0.1"` in the bundle-root `index.md` frontmatter.

**3. Links — keep wikilinks, add an OKF export (the clean answer):** `[[wikilinks]]` are load-bearing for human nav (any wiki-link-aware editor) and basename resolution, so we **don't** rip them out. Instead ship an **`okf-export`** that produces a spec-conformant bundle: convert `[[name]]` → `[Title](/path.md)` (resolve by basename → bundle-relative path), generate `index.md`/`log.md`, normalize frontmatter (`type` guaranteed, `last_updated`→`timestamp`, `sources`→Citations). Authoring stays in our convention; the *exported* bundle is conformant. (A `--strict` mode could author OKF-native links directly for projects that want it.)

## The contribution-back angle (the part that's *yours*)
OKF v0.1 has no convention for the maintenance signals this layer pioneered. None of the open issues address them. Propose them upstream (CLA-gated PRs/issues on `knowledge-catalog`):
- a **freshness/confidence convention** (`confidence`, `last_compiled` / staleness) — relevant to issue #78 (frontmatter in log/index files);
- a **contradiction convention** — how an enrichment agent records "new source contradicts an existing claim" (our `_contradictions.md` + preserve-both-views pattern). This is the maintained-wiki behavior OKF *describes* but doesn't spec.
Lead the contribution as "an independent, running implementation + the maintenance conventions the spec is missing" (cf. issue #86's announce-your-implementation pattern).

## Status
Conformance change, the export, and the index/log generators are staged toward an OKF-conformant release. This doc is the spec map; it travels with the OSS repo.
