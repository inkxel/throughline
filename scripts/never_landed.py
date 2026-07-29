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


def known_targets(stores):
    """Every slug a claim may legitimately resolve to. Includes declared
    frontmatter aliases — a concept renamed with an alias is NOT a missing
    write, and skipping this produces false positives on every rename."""
    known = set()
    for root in stores:
        root = Path(root)
        if not root.is_dir():
            continue
        for p in root.rglob("*.md"):
            known.add(p.stem)
            head = p.read_text(errors="replace")[:2000]
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


def check_log(log_path, stores, claim_re=CLAIM_RE):
    """Every write the log claims, checked against the store. Always returns a
    denominator — 'found nothing' must never be indistinguishable from
    'looked nowhere', which is the failure mode that let the original defect
    sit undetected for eight months."""
    log_path = Path(log_path)
    if not log_path.is_file():
        return {"claims_checked": None, "error": f"log not found: {log_path}",
                "never_landed": [], "never_landed_count": 0}
    known = known_targets(stores)
    claims, missing, date = 0, {}, "?"
    for line in log_path.read_text(errors="replace").splitlines():
        h = ENTRY_DATE.match(line)
        if h:
            date = h.group(1)
            continue
        for target, note in claim_re.findall(line):
            target = target.strip()
            if not CLAIM_WORD.search(note) or NOT_A_CLAIM.search(note):
                continue                      # a reference, not a claim
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
    if claims == 0:
        out["error"] = "0 claims parsed — claim pattern does not match this log"
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

        # missing log is an error, not zero findings
        assert "error" in check_log(d / "nope.md", [store])
    print("OK selftest — claim/reference split, alias resolution, min-dating, "
          "empty-parse alarm")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", help="log/timeline file containing write-claims")
    ap.add_argument("--store", action="append", default=[],
                    help="directory of concept files (repeatable)")
    ap.add_argument("--claim-pattern",
                    help="override the claim regex: 2 groups, (target)(note)")
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
    r = check_log(a.log, a.store, claim_re)
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
