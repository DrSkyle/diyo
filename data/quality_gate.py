#!/usr/bin/env python3
"""Local quality gate for generated rows. No credits, no network.

Adaption grades our completions at the 2nd percentile against its reference (5.22 vs 9.38) and the
main drivers are visible locally: how much concrete detail the answer carries, whether it is
speakable, and whether it repeats the row before it. This applies those checks before anything is
uploaded, so a bad batch never reaches training or costs another adapt run.

    python3 data/quality_gate.py --input data/raw/*.jsonl --output data/train/gated.jsonl

Hard drops (a row that fails these is not trainable):
  - completion shorter than 120 characters (nothing to learn)
  - markdown, bullet glyphs, numbered lists (unreadable aloud)
  - mostly Latin script (a Nepali assistant)
  - exact or near duplicate of a row already kept (shingles >= 0.85)

Everything else is kept, and the score distribution is reported so we can see whether the batch is
worse than the last one before spending a credit on it.
"""

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

DEV = re.compile(r"[\u0900-\u097f]")
LATIN = re.compile(r"[A-Za-z]")
MARKDOWN = re.compile(r"(^\s*[-*•]\s)|(^\s*\d+\.\s)|(\*\*)|(`)|(^#{1,6}\s)", re.M)
DIGITS = re.compile(r"[०-९0-9]")

# What a good Nepali answer actually contains: a place to go, something to watch for, a number.
INSTITUTIONS = ["स्वास्थ्य चौकी", "स्वास्थ्य संस्था", "अस्पताल", "डाक्टर", "चिकित्सक",
                "कृषि ज्ञान केन्द्र", "कृषि प्राविधिक", "मालपोत", "नापी", "जिल्ला प्रशासन",
                "वडा कार्यालय", "प्रहरी", "श्रम कार्यालय", "औषधि पसल"]
DANGER = ["तुरुन्त", "आपत्कालीन", "तुरुन्तै", "गम्भीर", "खतरा", "सास फेर्न", "रगत", "बेहोस"]
ACTIONS = ["दिनुहोस्", "जानुहोस्", "पिउनुहोस्", "खुवाउनुहोस्", "धुनुहोस्", "राख्नुहोस्",
           "सोध्नुहोस्", "गर्नुहोस्", "पुछ्नुहोस्", "देखाउनुहोस्", "हेर्नुहोस्"]


def fields(row):
    p = row.get("enhanced_prompt") or row.get("prompt") or ""
    c = row.get("enhanced_completion") or row.get("completion") or ""
    return str(p), str(c)


def english_ratio(text):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if LATIN.match(c)) / len(letters)


def repetition(text):
    words = re.findall(r"\S+", text)
    if len(words) < 9:
        return 0.0
    trigrams = [" ".join(words[i:i + 3]) for i in range(len(words) - 2)]
    return 1 - len(set(trigrams)) / len(trigrams)


def shingles(text, k=6):
    t = " ".join(re.sub(r"[।?!,.;:\"'()\[\]]", " ", text).split()).lower()
    return {t[i:i + k] for i in range(max(0, len(t) - k + 1))}


def score(row):
    """0-1 quality proxy; the same levers Adaption's grader reacts to."""
    _, c = fields(row)
    length = min(len(c), 700) / 700
    marks = sum(1 for group in (INSTITUTIONS, DANGER, ACTIONS) if any(w in c for w in group))
    numbers = 1 if DIGITS.search(c) else 0
    detail = (marks / 3) * 0.6 + numbers * 0.4
    pen = 0.5 * repetition(c) + 0.5 * english_ratio(c)
    return round(max(0.0, min(1.0, 0.45 * length + 0.55 * detail - pen)), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", nargs="+", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--min-score", type=float, default=0.0, help="drop below this score")
    ap.add_argument("--keep-shortest", type=float, default=0.0,
                    help="drop the bottom fraction by score, e.g. 0.2")
    args = ap.parse_args()

    rows, dropped = [], {}
    seen = []

    def drop(reason):
        dropped[reason] = dropped.get(reason, 0) + 1

    for pattern in args.input:
        for path in sorted(Path().glob(pattern)) if "*" in pattern else [Path(pattern)]:
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                p, c = fields(row)
                if not p or not c:
                    drop("empty")
                    continue
                if len(c) < 120:
                    drop("too_short")
                    continue
                if MARKDOWN.search(c):
                    drop("markdown")
                    continue
                if english_ratio(c) > 0.15:
                    drop("latin_heavy")
                    continue
                if broken_script(c):
                    drop("broken_script")
                    continue
                s = shingles(c)
                if any(len(s & o) / max(len(s | o), 1) >= 0.85 for o in seen):
                    drop("near_duplicate")
                    continue
                seen.append(s)
                rows.append({"prompt": p, "completion": c, "quality": score(row)})

    before = len(rows)
    if args.keep_shortest > 0 and rows:
        rows.sort(key=lambda r: -r["quality"])
        cut = rows[int(len(rows) * args.keep_shortest):]
        dropped["low_score"] = len(rows) - len(cut)
        rows = cut
    rows = [r for r in rows if r["quality"] >= args.min_score]

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                   encoding="utf-8")

    scores = [r["quality"] for r in rows]
    lens = sorted(len(r["completion"]) for r in rows) or [0]
    print(json.dumps({
        "kept": len(rows),
        "from": before + sum(dropped.values()),
        "dropped": dict(sorted(dropped.items(), key=lambda kv: -kv[1])),
        "quality_mean": round(statistics.mean(scores), 3) if scores else 0,
        "quality_p10": scores and sorted(scores)[len(scores) // 10],
        "completion_chars_median": lens[len(lens) // 2],
        "completion_chars_p10": lens[len(lens) // 10],
        "output": str(out),
    }, ensure_ascii=False, indent=1))


def broken_script(text):
    """The र्इ artefact the generator produced, and stray non-Devanagari letters."""
    if re.search(r"र्‍?इ", text):
        return True
    return bool(re.search(r"[\u0400-\u04FF\u0600-\u06FF]", text))  # Cyrillic / Arabic leakage


if __name__ == "__main__":
    main()
