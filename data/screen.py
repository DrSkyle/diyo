#!/usr/bin/env python3
"""Pre-screen invented Nepali rows before a human reads them.

Not a substitute for a native reviewer. It catches the mechanical failures so review time
goes to meaning.

    ./.venv/bin/python data/screen.py data/raw/diyo-health-v1.jsonl
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

DEV = re.compile(r"[\u0900-\u097f]")
LATIN = re.compile(r"[A-Za-z]")
MARKDOWN = re.compile(r"(^\s*[-*•]\s)|(^\s*\d+\.\s)|(\|)|(^#{1,6}\s)", re.M)
DOSE = re.compile(
    r"(\d+\s*(mg|ml|मिलिग्राम|मिली\s*लिटर|ml/l|gm|ग्राम))|"
    r"(दिनको\s*\d+\s*(चक्की|पटक|ml))", re.I)
REFUSAL = ["थाहा छैन", "जानकारी छैन", "सक्दिन", "सक्दैन", "अस्वीकार", "जानकारीमा"]
REFERRAL = ["स्वास्थ्य चौकी", "स्वास्थ्य संस्था", "अस्पताल", "कृषि", "मालपोत", "नापी",
            "वडा", "जिल्ला प्रशासन", "प्रहरी", "चिकित्सक", "डाक्टर", "प्राविधिक"]
BAD_GLYPH = re.compile(r"र्‍?इ")  # ई written as र्+इ → "तपार्इं" instead of "तपाईं"


def fields(row):
    """Return (prompt, answer) for the row formats Invent may return."""
    if "messages" in row:
        msgs = row["messages"]
        user = next((m["content"] for m in msgs if m.get("role") == "user"), "")
        asst = next((m["content"] for m in msgs if m.get("role") == "assistant"), "")
        return user, asst
    for pk in ("enhanced_prompt", "prompt", "instruction", "input", "question"):
        for ak in ("enhanced_completion", "response", "completion", "output", "answer"):
            if pk in row and ak in row:
                return str(row[pk] or ""), str(row[ak] or "")
    return "", ""


def dev_ratio(text):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if DEV.match(c)) / len(letters)


def sentences(text):
    return [s for s in re.split(r"[।!?]\s*", text) if s.strip()]


def screen(rows):
    seen = collections.Counter()
    out = []
    for i, row in enumerate(rows):
        q, a = fields(row)
        flags = []
        key = re.sub(r"\s+", " ", a.strip().lower())
        if key:
            seen[key] += 1
            if seen[key] > 1:
                flags.append("duplicate")
        if not q.strip() or not a.strip():
            flags.append("empty")
        if len(sentences(a)) < 2:
            flags.append("too_short")
        if len(sentences(a)) > 8:
            flags.append("too_long")
        if dev_ratio(a) < 0.90:
            flags.append(f"not_nepali({dev_ratio(a):.0%})")
        if MARKDOWN.search(a):
            flags.append("markdown")
        if DOSE.search(a):
            flags.append("DOSE")
        if len(LATIN.findall(a)) > 40:
            flags.append("latin_heavy")
        if BAD_GLYPH.search(a) or BAD_GLYPH.search(q):
            flags.append("bad_glyph")
        for s in re.split(r"[।?!]\s*", a):
            if len(s.strip()) >= 10 and s.strip() in q:
                flags.append("prompt_leak")
                break
        needs_care = any(w in q for w in ("औषधि", "विषादी", "मात्रा", "मिलिग्राम",
                                          "हानि", "मार्न", "जग्गा", "धनी"))
        if needs_care and not any(r in a for r in REFUSAL):
            flags.append("missing_refusal")
        if len(a) > 20 and not any(r in a for r in REFERRAL + REFUSAL):
            flags.append("no_referral")
        out.append({"i": i, "q": q, "a": a, "flags": flags})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--show", type=int, default=5, help="examples per flag")
    ap.add_argument("--keep", help="write rows with only these flags (comma list)")
    args = ap.parse_args()

    path = Path(args.path)
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    res = screen(rows)

    counts = collections.Counter()
    for r in res:
        counts["clean" if not r["flags"] else r["flags"][0]] += 1
        for f in r["flags"]:
            counts[f.split("(")[0]] += 1

    clean = sum(1 for r in res if not r["flags"])
    print(f"{len(res)} rows, {clean} clean ({clean / max(len(res), 1):.0%}), "
          f"{len(res) - clean} flagged\n")
    for k, v in counts.most_common():
        print(f"  {k:<18} {v}")

    shown = collections.Counter()
    for r in res:
        for f in r["flags"]:
            base = f.split("(")[0]
            if shown[base] < args.show:
                shown[base] += 1
                print(f"\n[{f}] {r['q'][:90]}\n   -> {r['a'][:180]}")

    if args.keep:
        keep = {k.strip() for k in args.keep.split(",")}
        sel = [rows[r["i"]] for r in res if set(f.split("(")[0] for f in r["flags"]) <= keep]
        out = path.with_suffix(".kept.jsonl")
        out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in sel) + "\n",
                       encoding="utf-8")
        print(f"\nwrote {len(sel)} rows to {out}")


if __name__ == "__main__":
    main()
