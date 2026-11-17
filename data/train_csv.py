#!/usr/bin/env python3
"""Train on a local clean CSV — upload, run AutoScientist, extract the adapter.

    python3 data/train_csv.py --csv data/train/gated-repaired.csv --name r4 --iterations 5
"""

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
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
    ap.add_argument("--csv", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--iterations", type=int, default=5)
    ap.add_argument("--model", default="Qwen/Qwen3.5-2B")
    args = ap.parse_args()

    client = Adaption()
    before = client.datasets.invent(dataset_prompt="p", rows=1, estimate=True).available_credits
    rows = list(csv.DictReader(Path(args.csv).open(encoding="utf-8")))
    lens = sorted(len(r["completion"]) for r in rows)
    log(f"credits {before} | {len(rows)} rows | completion chars median {lens[len(lens)//2]}")

    up = client.datasets.upload_file(
        args.csv, name=f"diyo-{args.name}", processing_mode="raw",
        column_mapping={"prompt": "prompt", "completion": "completion"})
    st = client.datasets.wait_for_completion(up.dataset_id)
    log(f"uploaded: {st.status} rows={st.row_count}")

    run = client.autoscientist.create(
        dataset_id=up.dataset_id, model=args.model, training_method="instruction",
        data_format="instruction", augmentation_domain_rows=0, augmentation_general_rows=0,
        max_iterations=args.iterations,
        idempotency_key=f"diyo-{args.name}-{st.row_count}-{args.iterations}")
    log(f"run {run.id} started")

    last = None
    while True:
        cur = client.autoscientist.get(run.id)
        line = f"{cur.status} iter={cur.iterations_completed} win={cur.best_win_rate}"
        if line != last:
            log(line)
            last = line
        if cur.status in ("succeeded", "failed", "cancelled"):
            break
        time.sleep(60)

    after = client.datasets.invent(dataset_prompt="p", rows=1, estimate=True).available_credits
    summary = {"name": args.name, "run_id": run.id, "rows": st.row_count,
               "status": cur.status, "iterations": cur.iterations_completed,
               "best_win_rate": cur.best_win_rate, "credits_before": before,
               "credits_after": after}

    if cur.status == "succeeded":
        tmp = ROOT / "data" / "models" / run.id
        tmp.mkdir(parents=True, exist_ok=True)
        client.autoscientist.download(run.id).write_to_file(str(tmp / "adapter.tar.zst"))
        unpack = tmp / "adapter"
        shutil.rmtree(unpack, ignore_errors=True)
        unpack.mkdir()
        subprocess.run(["tar", "xf", str(tmp / "adapter.tar.zst"), "-C", str(unpack)], check=True)
        tarball = ROOT / "artifacts" / f"diyo-{args.name}.tar.gz"
        tarball.parent.mkdir(exist_ok=True)
        subprocess.run(["tar", "czf", str(tarball), "-C", str(unpack), "."], check=True)
        summary["adapter_asset"] = str(tarball)

    (ROOT / "data" / "train" / f"{args.name}.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    log(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
