#!/usr/bin/env python3
"""Collect consented corrections into the next training set.

Inputs: exported JSON/JSONL from VoiceCommons (local receipts uploaded to a Nepal-hosted store).
This script never scrapes and never accepts items without a scope + receipt id.

    python3 pipeline/collect.py --inbox data/inbox --out data/train/corrections.csv
"""
import argparse, csv, json
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inbox", default="data/inbox")
    ap.add_argument("--out", default="data/train/corrections.csv")
    args = ap.parse_args()
    inbox = Path(args.inbox)
    rows = []
    for p in sorted(inbox.glob("**/*")) if inbox.exists() else []:
        if p.suffix not in (".json", ".jsonl"): continue
        items = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.suffix==".jsonl" else [json.loads(p.read_text(encoding="utf-8"))]
        for o in items:
            if o.get("kind") == "correction" or ("prompt" in o and "correct" in o):
                prompt = (o.get("prompt") or "").strip()
                right = (o.get("correct") or "").strip()
                if prompt and right:
                    rows.append({"prompt": prompt, "completion": right, "receipt": o.get("receipt",""), "scope": o.get("scope","A")})
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["prompt","completion","receipt","scope"]); w.writeheader(); w.writerows(rows)
    print(json.dumps({"accepted": len(rows), "out": str(out)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
PY
