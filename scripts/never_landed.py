#!/usr/bin/env python3
"""
never-landed — check existence claims against the store that should contain them.

The rule this implements, which is the portable part:

    A reference asserts nothing about its target. A log entry saying a concept
    was created asserts that it exists, and an assertion is checkable.

Dangling references are tolerated by most knowledge formats, correctly — a body
link is a pointer, not a promise. But a maintained log that records "created
[[x]]" IS making a claim, at a point where it can be verified. Nothing checks
those claims, so a write that never landed reads downstream as a concept that
was simply never written. Same surface, different history.

Three histories a missing target can have:

    removed        — it existed and was deliberately taken away
    never written  — it genuinely never existed (the tolerated default)
    never landed   — something RECORDED a write that did not happen  ← this check

Only the third is a producer bug, and only the third is checkable for free,
because the producer already wrote down what it claimed to do.

The regexes below are NOT the contribution — they are tuned to one corpus's
prose and will need replacing for yours (see --claim-pattern). The contribution
is the separation: check assertions where they are made, leave bare references
alone. Checking only assertions is also what keeps the output small enough to
read; bare mentions never fire, so below-threshold noise stays quiet.

Usage:
    never_landed.py --log LOG.md --store DIR [--store DIR ...] [--json]
    never_landed.py --fixture cases.json          # conformance run
    never_landed.py --selftest

Stdlib only. MIT.
"""

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

# --- the corpus-specific half -------------------------------------------------
# A claim is a link to a target followed by a parenthetical note about it.
CLAIM_RE = re.compile(
    r"\[\[([^\]\|#\n]+?)(?:#[^\]\|]*)?(?:\|[^\]\n]*)?\]\]\s*[(\[]([^)\]\n]*)[)\]]")
# Which notes assert existence. Everything else is a bare reference.
CLAIM_WORD = re.compile(r"creat|updat|wrote|added", re.I)
# Notes that use a claim word to say the OPPOSITE. Without this, "not yet
# created" and "creation pending" read as claims and the check inverts.
NOT_A_CLAIM = re.compile(
    r"\bnot\s+(?:yet\s+)?(?:re)?created\b|creation\s+(?:due|pending|needed)"
    r"|^\s*referenced", re.I)
ENTRY_DATE = re.compile(r"^#{1,6}\s+(\d{4}-\d{2}-\d{2})")


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def known_targets(stores, id_key="id"):
    """Every identifier a claim may legitimately resolve to.

    Three sources, and you need all three:
      - filename stems
      - declared frontmatter aliases — a renamed concept is NOT a missing
        write, and skipping this false-positives on every rename
      - a frontmatter stable-id key (default `id`)

    That last one is not optional for cross-producer use. Producers whose
    stable ids live in frontmatter while filenames are summary slugs resolve
    nothing against stems alone — every claim reads as never-landed. Reported
    by andrewcrenshaw against the remember/0.2 emitter, knowledge-catalog#207.
    """
    known = set()
    id_re = re.compile(rf"^{re.escape(id_key)}:\s*(.+?)\s*$", re.M)
    for root in stores:
        root = Path(root)
        if not root.is_dir():
            continue
        for p in root.rglob("*.md"):
            known.add(p.stem)
            head = p.read_text(errors="replace")[:2000]
            for v in id_re.findall(head):
                known.add(v.strip().strip("\"'"))
            blk = re.search(r"^aliases:\s*\n((?:\s*-\s*.+\n)+)", head, re.M)
            if blk:
                known |= {slugify(v) for v in
                          re.findall(r"^\s*-\s*(.+?)\s*$", blk.group(1), re.M)}
            inline = re.search(r"^aliases:\s*\[(.*?)\]\s*$", head, re.M)
            if inline:
                known |= {slugify(v.strip().strip("\"'"))
                          for v in inline.group(1).split(",")}
    known.discard("")
    return known


def check_log(log_path, stores, claim_re=CLAIM_RE, id_key="id"):
    """Every write the log claims, checked against the store. Always returns a
    denominator — 'found nothing' must never be indistinguishable from
    'looked nowhere', which is the failure mode that let the original defect
    sit undetected for eight months.

    Two pattern shapes are supported, because one regex contract can't
    express every producer's log prose:

      two groups (target, note) — the note is tested for a claim word, so
        the same pattern can match both claims and bare references and let
        the note decide. This is the default.
      one group (target)        — the pattern itself IS the claim assertion;
        anything it matches is a claim. Needed when the claim verb sits
        *before* the identifier ("**Lesson created**: lesson <id>"), where no
        single regex can put a claim word into a second group.

    The one-group shape was reported by andrewcrenshaw against the
    remember/0.2 emitter (knowledge-catalog#207): their log's verb precedes
    the id and the id carries no claim word, so the two-group contract was
    unsatisfiable and the pattern parsed nothing.
    """
    log_path = Path(log_path)
    if not log_path.is_file():
        return {"claims_checked": None, "error": f"log not found: {log_path}",
                "never_landed": [], "never_landed_count": 0}
    known = known_targets(stores, id_key)
    one_group = claim_re.groups == 1
    claims, missing, date = 0, {}, "?"
    body_has_claim_word = False
    for line in log_path.read_text(errors="replace").splitlines():
        h = ENTRY_DATE.match(line)
        if h:
            date = h.group(1)
            continue
        # Only ENTRY lines count toward "this log has claims in it". Headings are
        # document furniture — "# Directory Update Log" contains "Updat" and would
        # otherwise make every empty log look like a pattern failure, which is the
        # exact false alarm this guard exists to avoid.
        if not line.lstrip().startswith("#") and CLAIM_WORD.search(line):
            body_has_claim_word = True
        for hit in claim_re.findall(line):
            if one_group:
                target, note = hit, "(implicit — matched claim pattern)"
            else:
                target, note = hit
                if not CLAIM_WORD.search(note) or NOT_A_CLAIM.search(note):
                    continue                  # a reference, not a claim
            target = target.strip()
            claims += 1
            if target in known:
                continue
            m = missing.setdefault(target, {"target": target, "first_claimed": date,
                                            "claims": 0, "note": note.strip()[:80]})
            m["claims"] += 1
            # Logs are not reliably chronological — backfill blocks land out of
            # order, so take the min rather than the first one seen.
            if date < m["first_claimed"]:
                m["first_claimed"] = date
    out = {"claims_checked": claims,
           "targets_known": len(known),
           "never_landed_count": len(missing),
           "never_landed": sorted(missing.values(), key=lambda x: x["first_claimed"])}
    # A zero parse is an alarm ONLY when the log contains entries the pattern
    # should have matched. An unconditional throw false-alarms on a genuinely
    # empty corpus — a new bundle with an empty log is clean, not broken.
    # Refinement contributed by andrewcrenshaw, knowledge-catalog#207.
    if claims == 0 and body_has_claim_word:
        out["error"] = ("0 claims parsed, but the log contains creation entries — "
                        "claim pattern does not match this log's prose")
    return out


# --- conformance --------------------------------------------------------------
def case_verdict(case):
    """Decide from a fixture case's own evidence whether to emit never_landed.

    Deliberately does NOT look at case_class or at the expected block — that
    would be reading the answer key. The decision uses only what a consumer
    would actually have: what the record asserted, and what is there now.

    Two conditions, both required:
      1. the record asserts a BODY AT A NAMED LOCATION (checkable where made)
      2. that location is empty

    Condition 1 is what excludes identifier/DOI cases: a DOI record asserts
    that an identifier resolves, not that a body sits at a path the producer
    controls. It is also what excludes the inverse failure — content landed,
    registry update did not — because there the missing thing is the record,
    not the target. never_landed names one direction only.
    """
    subject = (case.get("axis_subject") or {}).get("kind", "")
    kind = case.get("identifier_kind", "")
    recorded = case.get("recorded") or {}
    declares_body = (
        kind == "declared_path"
        or subject == "registry_assertion"
        or "declared_state" in recorded
    )
    if not declares_body:
        return None
    observed = " ".join(str(v) for k, v in case.items()
                        if k.startswith("observed")).lower()
    absent = any(w in observed for w in ("absent", "missing", "not present", "no body"))
    return "never_landed" if absent else None


def run_fixture(path):
    data = json.loads(Path(path).read_text())
    cases = data.get("cases", [])
    tp = fp = fn = 0
    failures = []
    for c in cases:
        got = case_verdict(c)
        want = (c.get("expected") or {}).get("emit_presence")
        want = want if want == "never_landed" else None
        if got == want == "never_landed":
            tp += 1
        elif got == "never_landed" and want is None:
            fp += 1
            failures.append(("false positive", c.get("case_class"), c.get("identifier")))
        elif got is None and want == "never_landed":
            fn += 1
            failures.append(("missed", c.get("case_class"), c.get("identifier")))
    # The explicit trap: content landed, registry update did not. A checker that
    # fires on any content/record divergence fails here.
    trap = [c for c in cases
            if (c.get("expected") or {}).get("must_not_mark_never_landed")]
    trap_ok = all(case_verdict(c) is None for c in trap)
    return {"fixture": data.get("name"), "version": data.get("version"),
            "cases": len(cases), "true_positives": tp,
            "false_positives": fp, "missed": fn,
            "must_not_mark_cases": len(trap), "must_not_mark_passed": trap_ok,
            "failures": failures}


# --- selftest -----------------------------------------------------------------
def selftest():
    log = ("### 2026-01-01 — entry\n"
           "- [[ghost]] (updated), [[newcomer]] [1st], [[plain]], "
           "[[gap]] (referenced — known gap, not recreated)\n"
           "### 2025-06-01 — older backfill block\n"
           "- [[ghost]] (concept created — 2nd appearance), [[real]] (created)\n")
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        store = d / "concepts"
        store.mkdir()
        (store / "real.md").write_text("---\naliases: [renamed-thing]\n---\nbody\n")
        (store / "aliased.md").write_text("---\naliases:\n  - old-name\n---\nbody\n")
        logf = d / "log.md"
        logf.write_text(log)
        r = check_log(logf, [store])
        assert r["claims_checked"] == 3, r          # [1st]/bare/negated not counted
        assert [x["target"] for x in r["never_landed"]] == ["ghost"], r
        assert r["never_landed"][0]["first_claimed"] == "2025-06-01", r  # min, not first-seen
        assert r["never_landed"][0]["claims"] == 2, r
        known = known_targets([store])
        assert "renamed-thing" in known and "old-name" in known, known

        # a log whose prose the pattern does not match must ERROR, not pass clean
        bad = d / "bad.md"
        bad.write_text("### 2026-01-01\n- created concept foo\n")
        assert check_log(bad, [store])["claims_checked"] == 0
        assert "error" in check_log(bad, [store])

        # ...but a genuinely empty log is CLEAN, not an alarm. Unconditional
        # throwing false-alarms on a new bundle that has simply written nothing.
        empty = d / "empty.md"
        empty.write_text("# Directory Update Log\n\n## 2026-01-01\n")
        e = check_log(empty, [store])
        assert e["claims_checked"] == 0 and "error" not in e, e

        # missing log is an error, not zero findings
        assert "error" in check_log(d / "nope.md", [store])

        # --- one-group pattern + frontmatter id resolution ------------------
        # A producer whose claim verb PRECEDES the id, and whose stable ids
        # live in frontmatter while filenames are summary slugs.
        store2 = d / "facts"
        store2.mkdir()
        (store2 / "some-long-summary-slug.md").write_text(
            "---\nid: real-001\nsummary: a concept\n---\nbody\n")
        log2 = d / "log2.md"
        log2.write_text("# Directory Update Log\n\n## 2026-07-24\n\n"
                        "* **Lesson created**: lesson real-001 `__row__`\n"
                        "* **Lesson created**: lesson ghost-999 `__row__`\n")
        one = re.compile(r"\*\*Lesson created\*\*: lesson (\S+)")
        # stems alone cannot resolve a frontmatter id — both would look missing
        assert check_log(log2, [store2], one, id_key="nope")["never_landed_count"] == 2
        r2 = check_log(log2, [store2], one)
        assert r2["claims_checked"] == 2, r2
        assert [x["target"] for x in r2["never_landed"]] == ["ghost-999"], r2
        assert r2["never_landed"][0]["first_claimed"] == "2026-07-24", r2
    print("OK selftest — claim/reference split, alias + frontmatter-id resolution, "
          "min-dating, one-group patterns, empty-vs-unmatched log")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", help="log/timeline file containing write-claims")
    ap.add_argument("--store", action="append", default=[],
                    help="directory of concept files (repeatable)")
    ap.add_argument("--claim-pattern",
                    help="override the claim regex. 2 groups = (target)(note), "
                         "note tested for a claim word. 1 group = (target), the "
                         "pattern itself asserts the claim — use when the claim "
                         "verb precedes the identifier")
    ap.add_argument("--id-key", default="id",
                    help="frontmatter key holding a concept's stable id "
                         "(default: id). Needed when filenames are summary "
                         "slugs rather than identifiers")
    ap.add_argument("--fixture", help="run against a conformance cases.json")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        selftest()
        return 0

    if a.fixture:
        r = run_fixture(a.fixture)
        print(json.dumps(r, indent=2) if a.json else
              f"{r['fixture']} v{r['version']} — {r['cases']} cases\n"
              f"  true positives : {r['true_positives']}\n"
              f"  false positives: {r['false_positives']}\n"
              f"  missed         : {r['missed']}\n"
              f"  must-not-mark  : {r['must_not_mark_cases']} case(s), "
              f"{'passed' if r['must_not_mark_passed'] else 'FAILED'}")
        for f in r["failures"]:
            print("  !", *f)
        return 1 if (r["false_positives"] or r["missed"]
                     or not r["must_not_mark_passed"]) else 0

    if not a.log or not a.store:
        ap.error("--log and at least one --store are required")
    claim_re = re.compile(a.claim_pattern) if a.claim_pattern else CLAIM_RE
    if claim_re.groups not in (1, 2):
        ap.error(f"--claim-pattern needs 1 or 2 capture groups, got {claim_re.groups}")
    r = check_log(a.log, a.store, claim_re, a.id_key)
    if a.json:
        print(json.dumps(r, indent=2))
    else:
        if r.get("error"):
            print(f"ERROR: {r['error']}", file=sys.stderr)
        print(f"{r['claims_checked']} claims checked against "
              f"{r['targets_known']} known targets — "
              f"{r['never_landed_count']} never landed")
        for x in r["never_landed"]:
            print(f"  {x['first_claimed']}  {x['target']}  "
                  f"({x['claims']}x) — {x['note']}")
    return 1 if r.get("error") or r["never_landed_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
