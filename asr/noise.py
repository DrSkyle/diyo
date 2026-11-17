#!/usr/bin/env python3
"""Deterministic Nepali ASR-noise generator.

Turns clean Nepali text into plausible mis-transcriptions, so we can train the understanding
model on what the ears will actually produce. Deterministic: same seed, same pairs, every time.

    python3 asr/noise.py --input clean.jsonl --output pairs.jsonl --rate 0.20 --variants 3

Input : JSONL with `prompt` and `completion`, or a plain .txt with one utterance per line.
Output: JSONL with `prompt` (noisy *transcript*) and `completion` (the clean *answer*).
        The clean original is kept in `clean_prompt` so a reviewer can check both sides.

Why this exists: a 2B understanding model that only ever sees clean text falls apart on real
speech. The errors below are the ones Nepali ASR actually makes — matra confusion, श/ष/स,
word-boundary drift, English loanwords in Latin script, and numbers written as words.
"""

import argparse
import json
import random
import re
from pathlib import Path

CONS = [("श", "स"), ("ष", "स"), ("श", "ष"), ("ब", "व"), ("व", "ब"), ("ण", "न"),
        ("फ", "प"), ("प", "फ"), ("ड", "ड़"), ("छ", "च"), ("च", "छ"), ("ग", "क"),
        ("त", "ट"), ("द", "ड"), ("ज", "ज")]
MATRA = [("ि", "ी"), ("ी", "ि"), ("ु", "ू"), ("ू", "ु"), ("े", "ै"), ("ै", "े"),
         ("ो", "ौ"), ("ौ", "ो"), ("ृ", "ु")]

DIGIT_WORDS = {
    "१": "एक", "२": "दुई", "३": "तीन", "४": "चार", "५": "पाँच", "६": "छ",
    "७": "सात", "८": "आठ", "९": "नौ", "१०": "दस", "१५": "पन्ध्र", "२०": "बीस",
    "५००": "पाँच सय", "१०००": "हजार",
}
LOANWORDS = [("फोन", "phone"), ("रिचार्ज", "recharge"), ("बस", "bus"),
             ("डाक्टर", "doctor"), ("अस्पताल", "hospital"), ("पैसा", "paisa"),
             ("बजार", "bazar"), ("कम्प्युटर", "computer")]


def sub_chars(word, rng, count=1):
    ops = []
    for _ in range(count):
        for table, tag in ((MATRA, "matra"), (CONS, "cons")):
            cands = [(i, a, b) for i, ch in enumerate(word) for a, b in table if ch == a]
            if cands and rng.random() < 0.5:
                i, a, b = rng.choice(cands)
                word = word[:i] + b + word[i + 1:]
                ops.append(f"{tag}:{a}->{b}")
                break
    return word, ops


def corrupt(words, rng, target):
    """Apply about `target` word-level errors to the token list."""
    words = list(words)
    ops = []
    budget = max(1, round(len(words) * target))
    while budget > 0 and words:
        budget -= 1
        i = rng.randrange(len(words))
        w = words[i]
        kind = rng.choices(
            ["char", "digit", "loan", "delete", "dup", "merge", "split", "drop_matra"],
            weights=[40, 12, 10, 8, 6, 6, 6, 12])[0]

        if kind == "char":
            words[i], o = sub_chars(w, rng, rng.choice([1, 1, 2]))
            ops += o
        elif kind == "drop_matra":
            idx = [j for j, c in enumerate(w) if c in "ािीुूेैोौ"]
            if idx:
                j = rng.choice(idx)
                words[i] = w[:j] + w[j + 1:]
                ops.append("drop_matra")
        elif kind == "digit":
            cands = [(d, s) for d, s in DIGIT_WORDS.items() if d in w or s in w]
            if cands:
                d, s = rng.choice(cands)
                words[i] = w.replace(d, s) if d in w else w.replace(s, d)
                ops.append("digit_word")
        elif kind == "loan":
            hits = [(ne, en) for ne, en in LOANWORDS if ne in w]
            if hits:
                ne, en = rng.choice(hits)
                words[i] = w.replace(ne, en)
                ops.append("loanword")
        elif kind == "delete" and len(words) > 3:
            ops.append(f"delete:{words.pop(i)}")
        elif kind == "dup":
            words.insert(i, w)
            ops.append("duplicate")
        elif kind == "merge" and i + 1 < len(words):
            words[i] = w + words.pop(i + 1)
            ops.append("merge")
        elif kind == "split" and len(w) > 5:
            cut = len(w) // 2
            words[i:i + 1] = [w[:cut], w[cut:]]
            ops.append("split")
    return words, ops


def lev(a, b):
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def load(path):
    p = Path(path)
    rows = []
    if p.suffix == ".jsonl":
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    else:
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append({"prompt": line.strip(), "completion": ""})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--rate", type=float, default=0.2, help="fraction of words corrupted")
    ap.add_argument("--variants", type=int, default=1, help="noisy variants per clean row")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    rows = load(args.input)
    out = []

    for n, row in enumerate(rows):
        clean_prompt = row.get("prompt") or row.get("instruction") or ""
        clean_answer = row.get("completion") or row.get("output") or ""
        if not clean_prompt:
            continue
        base_words = clean_prompt.split()
        for v in range(args.variants):
            rng = random.Random(f"{args.seed}:{n}:{v}")
            noisy_words, ops = corrupt(base_words, rng, args.rate)
            noisy = " ".join(noisy_words)
            dist = lev(base_words, noisy_words)
            out.append({
                "prompt": noisy,
                "completion": clean_answer or clean_prompt,
                "clean_prompt": clean_prompt,
                "pair_id": f"{n}-{v}",
                "noise_ops": ops,
                "word_error_rate": round(dist / max(len(base_words), 1), 3),
            })

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n", encoding="utf-8")

    rates = [r["word_error_rate"] for r in out]
    print(f"{len(out)} pairs -> {args.output}")
    print(f"mean corruption rate: {sum(rates) / len(rates):.1%} "
          f"(min {min(rates):.0%}, max {max(rates):.0%})")
    print(f"target was {args.rate:.0%}")


if __name__ == "__main__":
    main()
