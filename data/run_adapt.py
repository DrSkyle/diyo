#!/usr/bin/env python3
"""Run Adaption's Adaptive Data pass over our dataset — the step we had been skipping.

Invent generates candidates; adapt is what improves them. Every training round so far fed raw
Invent output straight into AutoScientist, which is why Adaption graded our completions at the
2nd percentile.

    python3 data/run_adapt.py --name diyo-behaviour-r3 [--estimate]
"""

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from adaption import Adaption  # noqa: E402


def log(m):
    print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} {m}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--blueprint", default=None, help="path to a blueprint text file")
    ap.add_argument("--length", default=None, choices=["minimal", "concise", "detailed", "extensive"])
    args = ap.parse_args()

    c = Adaption()
    ds = None
    for d in c.datasets.list():
        if d.name == args.name and d.status == "succeeded":
            ds = d
            break
    if not ds:
        raise SystemExit(f"no succeeded dataset named {args.name}")
    log(f"{ds.name}: {ds.row_count} rows, {ds.dataset_id}")

    controls = {}
    if args.length:
        controls["length"] = args.length
    if args.blueprint:
        controls["blueprint"] = Path(args.blueprint).read_text(encoding="utf-8").strip()
    extra = {"brand_controls": controls} if controls else {}

    if args.estimate:
        est = c.datasets.adapt(ds.dataset_id, training_type="instruction_dataset",
                               estimate=True, **extra)
        log(json.dumps(est.model_dump() if hasattr(est, "model_dump") else str(est), indent=1))
        return

    res = c.datasets.adapt(
        ds.dataset_id,
        training_type="instruction_dataset",
        column_mapping={"prompt": "prompt", "completion": "completion"}, **extra)
    # adapt transforms the dataset in place; the response carries no new id, so poll the source
    out_id = ds.dataset_id
    log(f"adapt started in place on {out_id} (run {getattr(res, 'run_id', '?')})")

    last = None
    while True:
        rec = c.datasets.get(out_id)
        line = f"{rec.status} rows={rec.row_count}"
        if line != last:
            log(line)
            last = line
        if rec.status in ("succeeded", "failed", "awaits_input", "awaiting_input"):
            break
        time.sleep(30)

    summary = {"source": ds.dataset_id, "adapted": out_id, "status": rec.status,
               "rows": rec.row_count, "name": getattr(rec, "name", None)}
    (ROOT / "data" / "train" / "adapt.json").write_text(json.dumps(summary, indent=1),
                                                        encoding="utf-8")
    log(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
