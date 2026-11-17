#!/usr/bin/env python3
"""Upload behaviour data and train Diyo's dialogue model with AutoScientist.

    python3 data/train_autoscientist.py --csv data/train/diyo-behaviour-v0.csv          # upload + recommend only
    python3 data/train_autoscientist.py --csv ... --go                                  # actually train

Adaption trains its own hosted models only: Qwen3.5-2B / 4B / 9B, 35B-A3B, 122B.
The Himalaya Gemma 4 E2B is not trainable there, so Diyo-1's dialogue model is Qwen3.5-2B.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from adaption import Adaption  # noqa: E402

MODEL = "Qwen/Qwen3.5-2B"   # phone-sized; 4B/9B are the upgrade path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--augment-domain", type=float, default=900,
                    help="domain rows added before training (SFT needs >=1000 effective)")
    ap.add_argument("--augment-general", type=float, default=0)
    ap.add_argument("--iterations", type=float, default=1)
    ap.add_argument("--run-id", help="resume polling an existing run")
    ap.add_argument("--go", action="store_true")
    args = ap.parse_args()

    client = Adaption()

    if args.run_id:
        run = client.autoscientist.get(args.run_id)
        print("resuming", run.id, run.status)
        run = client.autoscientist.wait_for_completion(run.id)
        report(run)
        return

    csv_path = Path(args.csv)
    print(f"uploading {csv_path.name} ({csv_path.stat().st_size / 1024:.0f} KB) as raw SFT data")
    ds = client.datasets.upload_file(
        str(csv_path),
        name="diyo-behaviour-v0",
        processing_mode="raw",
        column_mapping={"prompt": "prompt", "completion": "completion"},
    )
    status = client.datasets.wait_for_completion(ds.dataset_id)
    print(f"dataset {ds.dataset_id} status={status.status} rows={status.row_count}")
    if status.status != "succeeded":
        sys.exit(f"upload did not succeed: {status.status}")

    rec = client.autoscientist.recommend_hyperparams(
        dataset_id=ds.dataset_id,
        model=args.model,
        augmentation_domain_rows=args.augment_domain,
        augmentation_general_rows=args.augment_general,
    )
    print("\nrecommended hyperparams:")
    print(json.dumps(rec.model_dump() if hasattr(rec, "model_dump") else str(rec),
                     ensure_ascii=False, indent=1)[:2000])

    if not args.go:
        print("\n(dry run — pass --go to train)")
        return

    run = client.autoscientist.create(
        dataset_id=ds.dataset_id,
        model=args.model,
        training_method="instruction",
        data_format="instruction",
        augmentation_domain_rows=args.augment_domain,
        augmentation_general_rows=args.augment_general,
        max_iterations=args.iterations,
        idempotency_key=f"diyo-behaviour-v0-{args.model.split('/')[-1]}",
    )
    print(f"\nrun {run.id} status={run.status}")
    (ROOT / "data" / "train" / "run.json").write_text(json.dumps({
        "run_id": run.id, "dataset_id": ds.dataset_id, "model": args.model,
        "augmentation_domain": args.augment_domain, "iterations": args.iterations,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }, indent=1), encoding="utf-8")

    while True:
        cur = client.autoscientist.get(run.id)
        print(f"  {cur.status} iterations={cur.iterations_completed} "
              f"win_rate={getattr(cur, 'best_win_rate', None)}", flush=True)
        if cur.status in ("succeeded", "failed", "cancelled"):
            report(cur)
            return
        time.sleep(60)


def report(run):
    print("\nfinal:", run.status)
    if run.status == "failed":
        print("error:", getattr(run, "error", None))
        sys.exit(1)
    print(f"iterations={run.iterations_completed} best_win_rate={run.best_win_rate}")
    print("download the model with: client.autoscientist.download(run.id)")


if __name__ == "__main__":
    main()
