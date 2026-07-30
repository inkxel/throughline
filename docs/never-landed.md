# never-landed — checking existence claims against the store

A dangling reference has three possible histories, and most knowledge formats can only express two of them.

```
removed        it existed, and was deliberately taken away
never written  it genuinely never existed          ← the tolerated default
never landed   something RECORDED a write that did not happen
```

The third one reads downstream as the second. A consumer sees a link with nothing behind it and correctly concludes "not written yet" — because that's what the spec says a dangling reference means. Nothing is wrong from the outside, which is exactly the problem.

## The rule

> **A reference asserts nothing about its target. A log entry saying a concept was created asserts that it exists, and an assertion is checkable.**

That separation is the whole idea. Body links stay tolerant — a pointer isn't a promise, and checking them produces noise proportional to how richly a corpus cross-links. But a maintained log that records *"created [[x]]"* is making a claim at a point where the producer already knows enough to verify it. Checking only those keeps output small enough to actually read: bare mentions never fire, so below-threshold material stays quiet.

Only the third history is a producer bug, and only the third is free to detect, because the producer already wrote down what it claimed to do.

## Why it went unnoticed for eight and a half months

The corpus this came from is small enough to read parts of most weeks. One concept was logged as created on 2025-11-06 and the gap wasn't caught until 2026-07-24. A maintained index recorded what an extraction agent *claimed* it wrote, and nothing ever compared those entries to disk.

Running the check for the first time: **939 write-claims, 65 with nothing behind them.**

## Usage

```bash
# real corpus
never_landed.py --log knowledge/_index/timeline.md \
                --store wiki/ --store decisions/

# a producer whose claim verb precedes the id, and whose stable ids
# live in frontmatter rather than in filenames
never_landed.py --log bundle/log.md --store bundle/facts \
                --claim-pattern '\*\*Lesson created\*\*: lesson (\S+)' \
                --id-key id

# conformance
never_landed.py --fixture cases.json
never_landed.py --selftest
```

Stdlib only, no dependencies. Non-zero exit on findings or on a parse failure.

### Two pattern shapes

`--claim-pattern` takes **one or two** capture groups, and the difference is which thing carries the assertion.

**Two groups — `(target)(note)`.** The note is tested for a claim word, so a single pattern can match both claims and bare references and let the note decide. This is the default, and it suits logs that write `[[thing]] (created)`.

**One group — `(target)`.** The pattern itself *is* the assertion; anything it matches is a claim. Necessary when the claim verb precedes the identifier — `**Lesson created**: lesson <id>` — because no single regex can then place a claim word in a second group. The two-group contract is unsatisfiable against that prose, and the honest failure is a zero parse rather than a bad match.

### Resolving targets

A claim resolves against three things: **filename stems**, declared frontmatter **aliases**, and a frontmatter **stable-id key** (`--id-key`, default `id`).

That last one isn't optional for cross-producer use. Where stable ids live in frontmatter while filenames are summary slugs, stems resolve nothing and *every* claim reads as never-landed. Aliases matter for the same reason in the other direction — skip them and every rename in a corpus's history fires.

## Results

**Against the corpus it was written for** — 939 claims checked against 780 known targets, 65 never landed, oldest 2025-11-05.

**Against the [Deletion Semantics Conformance Fixture v2.1](https://www.alexanarch.org/datasets/deletion-conformance-fixture/)** (111 cases, 17 classes, CC0), which encodes the `validity / presence / edges` axes settled in [knowledge-catalog#207](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/207):

```
111 cases
  true positives : 1
  false positives: 0
  missed         : 0
  must-not-mark  : 1 case, passed
```

The precision number is the one that matters. One case in that fixture expects `never_landed`; the other 110 must not be marked, and 109 of them are identifier/DOI cases where the record asserts that an identifier *resolves*, not that a body sits at a path the producer controls. A checker that fires on those is unusable.

**The 111th is a deliberate trap, and it's the useful test.** `registry_update_not_landed` is the inverse failure: the content landed, the registry update didn't. Its expected block carries `must_not_mark_never_landed: true`. Any checker that fires on "content and record disagree" fails it — `never_landed` names one direction only, and the presence axis is not made to carry transaction atomicity.

The fixture's conformance harness deliberately does not read `case_class` or the `expected` block when deciding. It uses only what a consumer would actually have: what the record asserted, and what is there now.

**Against a second producer — [remember-okf-sample-bundle](https://github.com/andrewcrenshaw/remember-okf-sample-bundle)** (CC0, SHA-256 manifest, planted cases), the first time this ran on a corpus it wasn't written for:

```
2 claims checked against 3 known targets — 1 never landed
  2026-07-24  okf-conformance-never-landed-999
```

It catches the planted case and resolves the real one, whose filename (`okf-v0-2-conformance-fixture-lesson-e-001.md`) shares almost nothing with its id (`okf-conformance-fixture-001`).

**Both of those took a code change, and the failure modes are the interesting part** — reported by [@andrewcrenshaw](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/207) after pointing this at his emitter. His log's claim verb precedes the id, so the two-group contract couldn't be satisfied by any regex; and his stable ids live in frontmatter while filenames are slugs, so nothing resolved. Neither was a flaw in the rule — both were the corpus-specific half, measured against a second producer for the first time.

Point `--id-key` at a key that doesn't exist and the real concept goes missing too, which is that false-positive mode reproduced on demand.

## What is and isn't portable

**Portable:** the claim/reference split, checking assertions where they're made, and dating a finding from the *minimum* claim date rather than the first one encountered — logs are not reliably chronological once backfill blocks land out of order.

**Not portable:** the regexes and the resolution scheme. `CLAIM_RE` and `CLAIM_WORD` are tuned to one corpus's prose; how a producer names and stores its identifiers is its own. Override with `--claim-pattern` and `--id-key`. Two producers was enough to show both need to be parameters rather than assumptions.

Because of that, a zero result is treated as an alarm rather than a pass, and a missing log errors rather than reporting no findings. **"Found nothing" and "looked nowhere" must never produce the same output**; that equivalence is what let the original defect sit for eight months.

**With one refinement, contributed by @andrewcrenshaw:** an unconditional throw on zero claims false-alarms on a genuinely empty corpus. A new bundle that has written nothing is clean, not broken. So the error fires only when the log contains creation entries the pattern *should* have matched and didn't — empty log, clean; entries present and unparsed, alarm.

Getting that right has a sharp edge worth knowing about. The first implementation scanned every line for a claim word, which matched **"# Directory Update Log"** — a document title containing "Updat." That made every empty log with a conventional heading look like a pattern failure, i.e. precisely the false alarm the refinement exists to prevent. Only entry lines count now; headings are furniture. The selftest catches it.

**One false positive worth knowing about:** a renamed concept with a declared alias reads as a missing write unless aliases are resolved. `known_targets()` reads both block and inline `aliases:` frontmatter. Skip that and every rename in the corpus's history fires.

## Related

- [knowledge-catalog#207](https://github.com/GoogleCloudPlatform/knowledge-catalog/issues/207) — deletion semantics; where the third history was proposed and the presence axis settled as sparse (`removed` | `never_landed`, no marker for the default)
- The `presence` axis is sparse by design: a producer can't know that no unrecorded prior state existed, so naming a default is an assertion it isn't entitled to make.
