#!/usr/bin/env python3
"""Nepali ASR scoring: WER, CER, and the one that matters — entity error rate.

Stdlib only. Reads a TSV or JSONL with fields `ref` and `hyp` (JSONL) or two tab-separated
columns (TSV).

    python3 asr/wer.py test.tsv
    python3 asr/wer.py test.jsonl --show 10 --entity

Normalisation is deliberately conservative: it removes things a human would not count as a
mistake (ZWJ/ZWNJ, punctuation, Devanagari-vs-ASCII digits) and nothing else. Do not add fuzzy
matching here — that hides real failures.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ZW = ("\u200b", "\u200c", "\u200d", "\ufeff", "\u00a0")
PUNCT = "।?!,.;:\"'()[]{}–—…/\\|"
DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

# tokens that carry risk: numbers, doses, quantities, currency
ENTITY = re.compile(
    r"(\d+(?:\.\d+)?)|"
    r"(\d+\s*(?:केजी|किलो|ग्राम|मिली|लिटर|मिटर|फिट|रुपैयाँ|रु|वर्ष|महिना|दिन|घण्टा|बजे|पटक|चक्की))|"
    r"(?:mg|ml|kg)\b",
    re.I)


def norm(text):
    for zw in ZW:
        text = text.replace(zw, "")
    text = text.translate(DEV_DIGITS)
    text = "".join(" " if c in PUNCT else c for c in text)
    return " ".join(text.split()).strip().lower()


def words(text):
    return norm(text).split()


def edit_ops(ref, hyp):
    """Levenshtein with backtrace. Returns (distance, ops) where ops are (tag, ref, hyp)."""
    n, m = len(ref), len(hyp)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)

    ops = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref[i - 1] == hyp[j - 1]:
            i, j = i - 1, j - 1
        elif i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + 1:
            ops.append(("sub", ref[i - 1], hyp[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            ops.append(("del", ref[i - 1], ""))
            i -= 1
        else:
            ops.append(("ins", "", hyp[j - 1]))
            j -= 1
    return d[n][m], list(reversed(ops))


def char_distance(a, b):
    return edit_ops(list(a), list(b))[0]


def load(path):
    p = Path(path)
    rows = []
    if p.suffix == ".jsonl":
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                rows.append((r.get("ref", ""), r.get("hyp", ""), r.get("id", "")))
    else:
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                sys.exit(f"bad TSV row: {line[:80]}")
            rows.append((parts[0], parts[1], parts[2] if len(parts) > 2 else ""))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--show", type=int, default=5, help="worst N utterances")
    ap.add_argument("--entity", action="store_true",
                    help="also score only tokens that carry numbers/units")
    args = ap.parse_args()

    rows = load(args.path)
    if not rows:
        sys.exit("no rows")

    total_ref = total_err = 0
    total_chars = total_char_err = 0
    ent_ref = ent_err = 0
    scored = []

    for ref, hyp, rid in rows:
        rw, hw = words(ref), words(hyp)
        dist, ops = edit_ops(rw, hw)
        total_ref += len(rw)
        total_err += dist
        total_chars += len(norm(ref).replace(" ", ""))
        total_char_err += char_distance(norm(ref).replace(" ", ""), norm(hyp).replace(" ", ""))
        scored.append((dist / max(len(rw), 1), ref, hyp, ops, rid))

        if args.entity:
            r_ent = [w for w in rw if ENTITY.search(w)]
            h_ent = [w for w in hw if ENTITY.search(w)]
            ent_ref += len(r_ent)
            ent_err += edit_ops(r_ent, h_ent)[0]

    wer = total_err / max(total_ref, 1)
    cer = total_char_err / max(total_chars, 1)
    print(f"utterances : {len(rows)}")
    print(f"WER        : {wer:.1%}  ({total_err}/{total_ref} words)")
    print(f"CER        : {cer:.1%}")
    if args.entity:
        print(f"ENTITY WER : {ent_err / max(ent_ref, 1):.1%}  "
              f"({ent_err}/{ent_ref} number+unit tokens)  <-- the one that matters")

    print(f"\nworst {args.show}:")
    for rate, ref, hyp, ops, rid in sorted(scored, reverse=True)[:args.show]:
        print(f"\n[{rate:.0%}] {rid}")
        print(f"  ref: {ref}")
        print(f"  hyp: {hyp}")
        bad = [f"{t}:{a}->{b}" if t == "sub" else (f"missing:{a}" if t == "del" else f"extra:{b}")
               for t, a, b in ops][:8]
        if bad:
            print("  err: " + ", ".join(bad))


if __name__ == "__main__":
    main()
