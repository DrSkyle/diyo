#!/usr/bin/env python3
"""Train on an adapted dataset instead of raw Invent output.

After `adapt`, rows carry enhanced_prompt / enhanced_completion. This downloads those, normalises
them into prompt/completion, uploads as raw SFT, and trains.

    python3 data/train_adapted.py --dataset diyo-behaviour-r3 --name a1 --iterations 5
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


def rows_from(path):
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        p = r.get("enhanced_prompt") or r.get("prompt")
        c = r.get("enhanced_completion") or r.get("completion")
        if p and c:
            out.append({"prompt": str(p), "completion": str(c)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, help="adapted dataset name")
    ap.add_argument("--name", required=True)
    ap.add_argument("--iterations", type=int, default=5)
    ap.add_argument("--model", default="Qwen/Qwen3.5-2B")
    args = ap.parse_args()

    client = Adaption()
    before = client.datasets.invent(dataset_prompt="p", rows=1, estimate=True).available_credits
    log(f"credits before: {before}")

    ds = next((d for d in client.datasets.list()
               if d.name == args.dataset and d.status == "succeeded"), None)
    if not ds:
        sys.exit(f"no succeeded dataset named {args.dataset}")

    raw = ROOT / "data" / "raw" / f"adapted-{args.name}.jsonl"
    raw.parent.mkdir(parents=True, exist_ok=True)
    client.datasets.download(ds.dataset_id, file_format="jsonl").write_to_file(str(raw))
    rows = rows_from(raw)
    log(f"{args.dataset}: {len(rows)} usable rows after adapt")
    if not rows:
        sys.exit("adapted dataset had no usable prompt/completion rows")

    lens = sorted(len(r["completion"]) for r in rows)
    log(f"completion chars: median {lens[len(lens)//2]}, p10 {lens[len(lens)//10]}, "
        f"p90 {lens[9*len(lens)//10]}  (speakable target ~250-700)")

    # The adapted rows already went through adaptation; feed them as raw SFT.
    csv_path = ROOT / "data" / "train" / f"adapted-{args.name}.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["prompt", "completion"])
        w.writeheader()
        w.writerows(rows)

    up = client.datasets.upload_file(
        str(csv_path), name=f"diyo-adapted-{args.name}", processing_mode="raw",
        column_mapping={"prompt": "prompt", "completion": "completion"})
    st = client.datasets.wait_for_completion(up.dataset_id)
    log(f"uploaded: {st.status} rows={st.row_count}")

    run = client.autoscientist.create(
        dataset_id=up.dataset_id, model=args.model, training_method="instruction",
        data_format="instruction", augmentation_domain_rows=0, augmentation_general_rows=0,
        max_iterations=args.iterations,
        idempotency_key=f"diyo-adapted-{args.name}-{st.row_count}")
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
    summary = {"name": args.name, "source_dataset": ds.dataset_id, "run_id": run.id,
               "rows": st.row_count, "status": cur.status,
               "iterations": cur.iterations_completed, "best_win_rate": cur.best_win_rate,
               "credits_before": before, "credits_after": after,
               "completion_median_chars": lens[len(lens) // 2]}

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
        log(f"adapter -> {tarball} ({tarball.stat().st_size/1e6:.0f} MB) — upload as a release asset")

    (ROOT / "data" / "train" / f"adapted-{args.name}.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    log(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
