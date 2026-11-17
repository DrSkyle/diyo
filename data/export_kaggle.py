#!/usr/bin/env python3
"""Build the SFT bundle for the Kaggle run on the Himalaya base.

    python3 data/export_kaggle.py

Merges every generated dataset plus the ASR-robustness pairs, applies the same cleaning as
prepare_training, and writes:

    kaggle/data/diyo-sft-v1.jsonl   {"prompt","completion"} rows
    kaggle/data/diyo-sft-v1.stats.json

Held-out rule: none of the 30 eval cases leak into this file. The export refuses to run if any
prompt matches an eval case closely, because a score on data you trained on is not a score.
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "kaggle" / "data" / "diyo-sft-v1.jsonl"
STATS = OUT.with_suffix(".stats.json")


def norm(text):
    return " ".join(re.sub(r"[।?!,.;:\"'()\[\]]", " ", text).split()).lower()


def main():
    raw = sorted((ROOT / "data" / "raw").glob("diyo-*.jsonl"))
    inputs = [str(p) for p in raw]
    inputs.append(str(ROOT / "data" / "train" / "asr-robust-v0.jsonl"))
    if not inputs:
        sys.exit("no inputs")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "merged.csv"
        subprocess.run([sys.executable, str(ROOT / "data" / "prepare_training.py"),
                        "--input", *inputs, "--output", str(csv_path)], check=True)
        import csv
        rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))

    eval_prompts = [norm(json.loads(l)["prompt"])
                    for l in (ROOT / "evals" / "nepali_eval.jsonl").read_text(encoding="utf-8").splitlines()
                    if l.strip()]
    leaked = [r["prompt"] for r in rows if norm(r["prompt"]) in eval_prompts]
    if leaked:
        sys.exit(f"{len(leaked)} training rows are verbatim eval cases; refusing to export")

    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                   encoding="utf-8")
    stats = {"rows": len(rows), "sources": [Path(i).name for i in inputs],
             "leaked_eval_cases": 0,
             "avg_completion_chars": round(sum(len(r["completion"]) for r in rows) / len(rows))}
    STATS.write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
