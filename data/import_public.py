#!/usr/bin/env python3
"""Import public Nepali instruction data with licence filtering.

Source: himalaya-ai/nepali-sft-suite `core` (68,056 rows, all Nepali, CC/Apache per row).
We keep only permissively licensed rows and pure Devanagari script, because this will train a
model that ships commercially.

    python3 data/import_public.py --out data/public/nepali-core.jsonl
"""

import argparse
import json
import statistics
import urllib.request
from pathlib import Path

URL = ("https://huggingface.co/datasets/himalaya-ai/nepali-sft-suite/"
       "resolve/main/core/train.parquet")
OK_LICENCES = {"apache-2.0", "cc0-1.0", "cc-by-4.0"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/public/nepali-core.jsonl")
    ap.add_argument("--cache", default="/tmp/core.parquet")
    args = ap.parse_args()

    import pyarrow.parquet as pq

    cache = Path(args.cache)
    if not cache.exists():
        print("downloading…")
        urllib.request.urlretrieve(URL, cache)
        print(f"{cache.stat().st_size/1e6:.1f} MB")

    d = pq.read_table(cache).to_pydict()
    rows, dropped = [], {"licence": 0, "script": 0, "shape": 0}
    for i in range(len(d["id"])):
        if d["license"][i] not in OK_LICENCES:
            dropped["licence"] += 1
            continue
        if d["script"][i] != "Deva":
            dropped["script"] += 1
            continue
        conv = d["conversations"][i] or []
        human = next((c["value"] for c in conv if c.get("from") == "human"), None)
        gpt = next((c["value"] for c in conv if c.get("from") == "gpt"), None)
        if not human or not gpt or len(gpt) < 80:
            dropped["shape"] += 1
            continue
        rows.append({"prompt": human.strip(), "completion": gpt.strip(),
                     "domain": d["domain"][i], "licence": d["license"][i],
                     "source": d["source_name"][i]})

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                   encoding="utf-8")

    lens = sorted(len(r["completion"]) for r in rows)
    by_domain = {}
    for r in rows:
        by_domain.setdefault(r["domain"], []).append(len(r["completion"]))

    print(json.dumps({
        "kept": len(rows),
        "dropped": dropped,
        "completion_median": lens[len(lens) // 2],
        "completion_p90": lens[9 * len(lens) // 10],
        "by_domain": {k: {"rows": len(v), "median_chars": statistics.median(v)}
                      for k, v in sorted(by_domain.items())},
        "output": str(out),
    }, indent=1))


if __name__ == "__main__":
    main()
