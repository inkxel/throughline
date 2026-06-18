#!/usr/bin/env python3
"""
okf-export — emit an OKF-conformant Knowledge Bundle from a knowledge/ layer.

Authoring stays in the knowledge-layer convention ([[wikilinks]], rich
frontmatter). This produces a clean copy that conforms to Google's Open
Knowledge Format (OKF) v0.1 — every concept has a non-empty `type`, links are
bundle-relative markdown, and index.md / log.md are generated.

Pure stdlib. No deps.

    python3 okf-export.py <knowledge-dir> [-o <out-dir>]

OKF v0.1 conformance (§9, the only normative MUSTs):
  1. Every non-reserved .md file parses as a YAML-frontmatter block.
  2. Every frontmatter block has a non-empty `type` field.
  3. Reserved filenames (index.md, log.md) follow §6/§7 when present.
Everything else in the spec is SHOULD / soft guidance; consumers MUST tolerate
missing optional fields, unknown types/keys, broken links, and missing indexes.

Spec: github.com/GoogleCloudPlatform/knowledge-catalog → okf/SPEC.md
"""
import sys, os, re, argparse
from datetime import datetime, timezone

RESERVED = {"index.md", "log.md", "_codemap.md", "CLAUDE.md", "AGENTS.md", "README.md", "roadmap.md"}
# default concept `type` inferred from the top-level dir when frontmatter lacks one
DIR_TYPE = {"journal": "Journal", "decisions": "Decision", "research": "Research", "wiki": "Reference"}
WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
# frontmatter keys we re-emit as YAML block sequences (multi-value)
LIST_KEYS = ("tags", "sources", "related", "aliases")


# --------------------------------------------------------------------------- #
# Frontmatter parsing
# --------------------------------------------------------------------------- #

def split_frontmatter(text):
    """Split a UTF-8 markdown file into (frontmatter_text, body).

    Per OKF §4 the block is delimited by `---` *on its own line* at the very
    start of the file and a closing `---` *on its own line*. The reference
    parser (enrichment_agent/bundle/document.py) checks `lines[0].strip()` and
    a later line whose `.strip() == "---"`. We mirror that so we don't treat a
    stray `\\n---` inside body prose (e.g. a horizontal rule) as the close, and
    so a file with no frontmatter is returned verbatim as body.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return "", text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fm = "".join(lines[1:i])
            body = "".join(lines[i + 1:])
            if body.startswith("\n"):
                body = body[1:]
            return fm, body
    # Unterminated block: treat the whole thing as having no frontmatter rather
    # than crashing — conformance is enforced later by synthesizing a `type`.
    return "", text


def _strip_quotes(v):
    v = v.strip()
    if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
        return v[1:-1]
    return v


def _split_inline_list(v):
    """Split a `[a, b, c]` inline flow sequence into clean string items.

    Commas inside `[[wikilinks]]` must not split items, so we track bracket
    depth. Handles the real-world `related: [[a]], [[b]]` shape (which is not
    valid YAML flow but is what the knowledge-layer convention emits) as well
    as a genuine `tags: [a, b]` inline list.
    """
    s = v.strip()
    if s.startswith("[") and s.endswith("]") and not s.startswith("[["):
        s = s[1:-1]
    items, buf, depth = [], [], 0
    for ch in s:
        if ch == "[":
            depth += 1
            buf.append(ch)
        elif ch == "]":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth <= 0:
            items.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        items.append("".join(buf))
    return [_strip_quotes(x) for x in (i.strip() for i in items) if x.strip()]


def fm_parse(fm):
    """Minimal YAML-frontmatter parser (pure stdlib).

    Returns a dict mapping key -> str (scalar) or list[str] (sequence). Handles:
      - `key: value`                       scalar
      - `key: [a, b]`                      inline flow sequence
      - `key: [[a]], [[b]]`                wikilink-comma list (convention)
      - `key:` followed by `- item` lines  block sequence
    Only top-level keys are read (knowledge-layer frontmatter is flat). Unknown
    structures degrade to a scalar string, never an exception — robustness over
    completeness, matching OKF's permissive-consumption stance.
    """
    out = {}
    lines = fm.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_][\w.\-]*):\s?(.*)$", line)
        if not m:
            continue
        key, rest = m.group(1), m.group(2).strip()
        if rest == "" or rest == "|" or rest == ">":
            # possible block sequence: peek at following `- item` lines
            items = []
            while i < len(lines):
                nxt = lines[i]
                bm = re.match(r"^\s*-\s+(.*)$", nxt)
                if bm:
                    items.append(_strip_quotes(bm.group(1).strip()))
                    i += 1
                elif nxt.strip() == "":
                    i += 1  # tolerate blank lines inside a block
                else:
                    break
            out[key] = items if items else ""
        elif rest.startswith("[") or ("[[" in rest and "," in rest):
            out[key] = _split_inline_list(rest)
        else:
            out[key] = _strip_quotes(rest)
    return out


def fm_get(fm_dict, *keys):
    """First non-empty scalar value among keys. Lists are joined to a hint
    string only for scalar contexts (titles never come from list keys here)."""
    for k in keys:
        v = fm_dict.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, list) and v:
            return ", ".join(v)
    return None


def fm_list(fm_dict, key):
    """Always return a list[str] for a (possibly scalar) frontmatter key."""
    v = fm_dict.get(key)
    if isinstance(v, list):
        return [x for x in v if x]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def iso_timestamp(val):
    """Coerce a frontmatter date/timestamp to an ISO-8601 datetime, or None.

    Handles the messy real cases: a bare date (`2026-04-13`), an already-ISO
    datetime (returned as-is), and an annotated date (`2026-04-13 (backfill: …)`)
    — extract the leading date and drop the annotation rather than emit an
    unquotable string. Unparseable → None, so the caller stamps export time.
    """
    if not val:
        return None
    val = val.strip().strip('"').strip("'")
    if re.match(r"\d{4}-\d{2}-\d{2}T", val):
        return val
    m = re.match(r"(\d{4}-\d{2}-\d{2})", val)
    if m:
        return m.group(1) + "T00:00:00Z"
    return None


def first_h1(body):
    for line in body.splitlines():
        if line.startswith("# "):
            return strip_md(line[2:])
    return ""


def first_sentence(body):
    for line in body.splitlines():
        s = line.strip()
        if s and not s.startswith(("#", "---", ">", "|", "-", "*", "`")):
            return strip_md(s)
    return ""


def strip_md(s):
    s = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", lambda m: m.group(2) or m.group(1), s)
    s = re.sub(r"[`*_#]+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > 180:
        s = s[:180].rsplit(" ", 1)[0] + "…"
    return s


def yq(s):
    """YAML-safe double-quoted scalar."""
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def warn(msg):
    sys.stderr.write("okf-export: " + msg + "\n")


def collect(kdir):
    """Walk for concept files. Return list of dicts with src path + rel path."""
    concepts = []
    for root, dirs, files in os.walk(kdir):
        dirs[:] = [d for d in dirs if not d.startswith(".") and not d.endswith("-log")]
        for f in files:
            if not f.endswith(".md") or f in RESERVED or f.startswith("_"):
                continue
            src = os.path.join(root, f)
            rel = os.path.relpath(src, kdir)
            concepts.append({"src": src, "rel": rel})
    return concepts


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kdir", help="path to the knowledge/ directory")
    ap.add_argument("-o", "--out", default=None, help="output bundle dir (default: ./okf)")
    args = ap.parse_args()
    kdir = os.path.abspath(args.kdir)
    out = os.path.abspath(args.out or os.path.join(os.getcwd(), "okf"))

    concepts = collect(kdir)

    # basename (no .md) -> list of bundle-relative paths, for wikilink resolution.
    # OKF §2: concept ID is the file path minus `.md`. Bare-name [[wikilinks]]
    # are a knowledge-layer convenience, not an OKF concept; when a basename is
    # unique we resolve it, when it collides across partitions we warn loudly so
    # links are never *silently* misresolved to the wrong concept.
    by_base = {}
    for c in concepts:
        base = os.path.splitext(os.path.basename(c["rel"]))[0]
        by_base.setdefault(base, []).append("/" + c["rel"].replace(os.sep, "/"))
    collisions = {b: ps for b, ps in by_base.items() if len(ps) > 1}
    for b, ps in sorted(collisions.items()):
        warn(f"basename collision: bare wikilink [[{b}]] is ambiguous across "
             f"{len(ps)} files ({', '.join(ps)}); resolving to first by path order. "
             f"Use a path-style [[dir/{b}]] link to disambiguate.")

    def resolve(name):
        name = name.strip()
        if "/" in name:                      # path-style wikilink — exact concept id
            p = name if name.endswith(".md") else name + ".md"
            return "/" + p.lstrip("/")
        paths = by_base.get(name)
        if not paths:
            return "/" + name + ".md"        # broken link is OKF-legal (§5.3)
        return sorted(paths)[0]              # deterministic on collision (warned above)

    meta = []   # (relpath, type, title, description)
    log_rows = []  # (date, verb, title, relpath)
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    os.makedirs(out, exist_ok=True)

    for c in concepts:
        text = open(c["src"], encoding="utf-8").read()
        fm_text, body = split_frontmatter(text)
        fm = fm_parse(fm_text)

        ctype = fm_get(fm, "type")
        if not ctype:                        # conformance rule 2: type is REQUIRED
            top = c["rel"].split(os.sep)[0]
            ctype = DIR_TYPE.get(top, "Reference")
        # H1 beats `name:` — in this convention `name:` is often a slug (e.g.
        # "answer-engine-intel") while the H1 is the human heading.
        title = fm_get(fm, "title") or first_h1(body) or fm_get(fm, "name") or \
            os.path.splitext(os.path.basename(c["rel"]))[0].replace("-", " ").title()
        # OKF §9 mandates only `type`, but Google's reference validator
        # (enrichment_agent/bundle/document.py) requires type+title+description+
        # timestamp non-empty, and all 65 concepts in their sample bundles carry
        # all four. Emit all four always — description falls back to the title,
        # timestamp to export time (as their own write_concept does) — so the
        # bundle passes Google's own tooling, not just the spec letter.
        desc = strip_md(fm_get(fm, "description") or first_sentence(body)) or title
        ts = iso_timestamp(fm_get(fm, "timestamp", "last_updated", "date")) or now_iso

        # rebuild a minimal, conformant frontmatter (YAML-safe quoted values).
        new_fm = [f"type: {yq(ctype)}", f"title: {yq(title)}",
                  f"description: {yq(desc)}", f"timestamp: {yq(ts)}"]
        # multi-value keys -> proper YAML block sequences so the block always
        # parses as a YAML mapping (the one hard rule for list frontmatter, §4.1).
        # `related` items are [[wikilinks]] in the source; strip to bare names so
        # the emitted YAML is clean (the body links carry the real relationships).
        for key in LIST_KEYS:
            vals = fm_list(fm, key)
            if key == "related":
                vals = [WIKILINK.sub(lambda m: (m.group(2) or m.group(1)).strip(), v).strip()
                        for v in vals]
                vals = [v for v in vals if v]
            if vals:
                new_fm.append(f"{key}:")
                new_fm.extend(f"- {yq(v)}" for v in vals)
        conf = fm_get(fm, "confidence")
        if conf:
            new_fm.append(f"confidence: {yq(conf)}")   # extension key — our maintenance signal

        # convert wikilinks in the body -> bundle-relative markdown links (§5.1)
        nbody = WIKILINK.sub(lambda m: f"[{(m.group(2) or m.group(1)).strip()}]({resolve(m.group(1))})", body)
        # Sources -> Citations heading convention (§8)
        nbody = re.sub(r"^#+\s*Sources\s*$", "# Citations", nbody, flags=re.M)

        dst = os.path.join(out, c["rel"])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "w", encoding="utf-8").write("---\n" + "\n".join(new_fm) + "\n---\n\n" + nbody)

        meta.append((c["rel"], ctype, title, desc))
        # log: dated entries from journal/decision concepts
        d = fm_get(fm, "date")
        if d and re.match(r"\d{4}-\d{2}-\d{2}", d):
            verb = "Creation" if ctype in ("Journal", "Decision") else "Update"
            log_rows.append((d[:10], verb, title, "/" + c["rel"].replace(os.sep, "/")))

    # ---- index.md per sub-directory (§6) ----
    # Group entries by concept `type` (heading = type), matching the OKF
    # reference index generator (enrichment_agent/bundle/index.py). Each section
    # is a heading + bullet list of `* [Title](relative-url) - description`.
    by_dir = {}
    for rel, ctype, title, desc in meta:
        by_dir.setdefault(os.path.dirname(rel), []).append((ctype, rel, title, desc))

    # description for a subdirectory link in its parent index: the single child's
    # description when there's exactly one, else blank (reference behavior).
    dir_desc = {}
    for d, items in by_dir.items():
        if d and len(items) == 1 and items[0][3]:
            dir_desc[d] = items[0][3]

    def write_index_sections(path, concept_items, child_dirs):
        sections = []
        groups = {}
        for ctype, rel, title, desc in concept_items:
            groups.setdefault(ctype or "Concepts", []).append((rel, title, desc))
        for ctype in sorted(groups):
            lines = [f"# {ctype}", ""]
            for rel, title, desc in sorted(groups[ctype], key=lambda e: e[1].lower()):
                suffix = f" - {desc}" if desc else ""
                lines.append(f"* [{title}]({os.path.basename(rel)}){suffix}")
            sections.append("\n".join(lines))
        if child_dirs:
            lines = ["# Subdirectories", ""]
            for cd in sorted(child_dirs):
                ds = dir_desc.get(cd, "")
                suffix = f" - {ds}" if ds else ""
                lines.append(f"* [{os.path.basename(cd)}]({os.path.basename(cd)}/index.md){suffix}")
            sections.append("\n".join(lines))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write("\n\n".join(sections) + "\n")

    # immediate child directories of each directory (for # Subdirectories)
    all_dirs = {d for d in by_dir if d}
    children_of = {}
    for d in all_dirs:
        parent = os.path.dirname(d)
        children_of.setdefault(parent, []).append(d)

    index_count = 0
    for d, items in by_dir.items():
        if d == "":
            continue  # root handled below
        write_index_sections(os.path.join(out, d, "index.md"), items, children_of.get(d, []))
        index_count += 1

    # ---- bundle-root index.md (§6 + §11) ----
    # The root index is the ONLY place OKF permits frontmatter, solely to declare
    # okf_version (§11). Body lists root concepts (grouped by type) and top-level
    # subdirectories.
    root_concepts = by_dir.get("", [])
    top_dirs = children_of.get("", [])
    root_path = os.path.join(out, "index.md")
    # build body sections then prepend the okf_version frontmatter
    tmp = root_path + ".tmp"
    write_index_sections(tmp, root_concepts, top_dirs)
    body = open(tmp, encoding="utf-8").read()
    os.remove(tmp)
    open(root_path, "w", encoding="utf-8").write('---\nokf_version: "0.1"\n---\n\n' + body)
    index_count += 1

    # ---- log.md at bundle root (§7) ----
    # Flat list of date-grouped entries, NEWEST FIRST. ISO-8601 `## YYYY-MM-DD`
    # headings (hard rule). Verb-prose `* **Verb**: ...` bolding is convention.
    if log_rows:
        by_date = {}
        for date, verb, title, rel in log_rows:
            by_date.setdefault(date, []).append(f"* **{verb}**: [{title}]({rel}).")
        log = ["# Update Log", ""]
        for date in sorted(by_date, reverse=True):
            log.append(f"## {date}")
            log.extend(by_date[date])
            log.append("")
        open(os.path.join(out, "log.md"), "w", encoding="utf-8").write("\n".join(log).rstrip() + "\n")

    print(f"OKF bundle written to {out}")
    print(f"  {len(concepts)} concepts · {index_count} index.md · {'log.md' if log_rows else 'no log'}")
    if collisions:
        print(f"  ⚠ {len(collisions)} basename collision(s) — see warnings above")
    print(f"  conformance: every concept has a non-empty `type` ✓")


if __name__ == "__main__":
    main()
