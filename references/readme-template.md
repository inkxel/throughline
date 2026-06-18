# README template

The repo-root `README.md` is the **canonical one-page outline**: what this is, why it exists, where it's going, and how to navigate. It's the first thing a person or an agent reads. Keep it consistent across every project so both know what to expect.

## What a README IS
- **WHAT** the project is (one sharp lead sentence, then the shape of it)
- **WHY** it exists (the problem, the wager)
- **DIRECTION** — principles, the approach, the phased roadmap
- **NAVIGATION** — where everything else lives (`knowledge/`, `docs/`, `knowledge/research/`)

## What a README is NOT — keep these OUT
- **Research, findings, evaluations, benchmarks, option-analysis.** → `knowledge/research/`. The README states the *decision* that came out of the research and links to it; it never reproduces the research.
- **Meeting origins / who-said-what / "issued out of the X QBR."** Irrelevant in a README — lead with the problem.
- **Client names, internal people names, client-specific markets.** Keep repos client-neutral; that framing lives in your separate strategic/knowledge layer, not the repo.
- **Build history / session logs / decision rationale.** → `knowledge/` (journal, decisions). Link ADRs; don't inline them.

## Standard section order

```markdown
# <Project Name> (<ABBR>)

**<One-line what-it-is, bold lead.>** <2–3 sentences on the shape and the value.>

> **Scope:** agency-wide vs. specific; name the first deployment as "deployment #1, not the identity."
> **Status:** phase + one line; "build mechanics, decisions, history live in `knowledge/`."

---

## Why this exists
<The problem and the wager. No meeting origins.>

## What it does
<Numbered capabilities / the loop. Sub-sections for distinct axes/modules.>

## Architecture
<High-level shape — the pieces and how they compose. Link wiki for detail.>

## Direction & principles
<Bulleted principles — the load-bearing beliefs that shape the build.>

## Approach / key decisions
<Concise statements of the decisions taken (e.g. "use X for Y"). Link the ADRs and
 knowledge/research/ for the reasoning — never reproduce the analysis here.>

## Roadmap (phases)
<Phase 0..N, one line each. Sequencing rationale in a closing line.>

## Repo layout
<Tree: README, docs/, knowledge/ (+ knowledge/research/).>

## Context
<Where strategic/cross-functional context lives (your separate strategic/knowledge layer);
 reaffirm build mechanics live in knowledge/.>
```

## The research split (load-bearing)
When a README section starts turning into research — a data-source comparison, a benchmark table, an A/B/C option weigh-up, a budget estimate, a vendor evaluation — **stop and move it to `knowledge/research/<YYYY-MM>-<topic>.md`.** Leave behind only the one-line decision + a link. The test: *if it reads like findings, it's research; if it reads like direction, it's README.*
