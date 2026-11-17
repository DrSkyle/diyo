#!/usr/bin/env python3
"""Turn invented rows into a clean prompt/completion CSV for AutoScientist.

    python3 data/prepare_training.py --input data/raw/diyo-health-v1.jsonl \
        --output data/train/diyo-behaviour-v0.csv

What it fixes and drops:
  - the र्इ glyph corruption the generator produced (तपार्इं → तपाईं)
  - empty completions
  - rows that are not really Nepali
  - rows shorter than two sentences (they cannot be spoken as an answer)
  - PII (phone numbers, emails, long digit runs)
  - exact duplicates
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from consent import redact  # noqa: E402

DEV = re.compile(r"[\u0900-\u097f]")
GLYPHS = [("र्‍इ", "ई"), ("र्इ", "ई"), ("मलार्इ", "मलाई"), ("तपार्इं", "तपाईं")]


def fields(row):
    for pk in ("enhanced_prompt", "prompt", "instruction"):
        for ak in ("enhanced_completion", "completion", "response", "output"):
            if row.get(pk) and row.get(ak):
                return str(row[pk]), str(row[ak])
    return "", ""


def dev_ratio(text):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if DEV.match(c)) / len(letters)


def sentences(text):
    return [s for s in re.split(r"[।!?]\s*", text) if s.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, nargs="+")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    rows, seen, stats = [], set(), {"in": 0, "kept": 0}
    reasons = {}

    def drop(why):
        reasons[why] = reasons.get(why, 0) + 1

    for path in args.input:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            stats["in"] += 1
            q, a = fields(json.loads(line))
            for bad, good in GLYPHS:
                q, a = q.replace(bad, good), a.replace(bad, good)

            if not q or not a:
                drop("empty")
                continue
            q, a = redact(q), redact(a)
            if dev_ratio(a) < 0.85:
                drop("not_nepali")
                continue
            if len(sentences(a)) < 2:
                drop("too_short")
                continue
            if "र्इ" in a or "र्इ" in q:
                drop("glyph_unfixed")
                continue
            key = re.sub(r"\s+", " ", a.lower())
            if key in seen:
                drop("duplicate")
                continue
            seen.add(key)
            rows.append({"prompt": q, "completion": a})

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["prompt", "completion"])
        w.writeheader()
        w.writerows(rows)

    stats["kept"] = len(rows)
    print(json.dumps({"in": stats["in"], "kept": len(rows),
                      "kept_pct": round(len(rows) / max(stats["in"], 1) * 100, 1),
                      "dropped": reasons, "output": str(out)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
