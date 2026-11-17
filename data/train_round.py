#!/usr/bin/env python3
"""One training round: merge every generated dataset, train, extract the adapter.

    python3 data/train_round.py --name r2 --iterations 5

More iterations is Adaption's own co-optimisation loop, which is the cheapest quality lever we
have: it tunes the data/recipe pair per iteration instead of us guessing.
"""

import argparse
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


def balance(c):
    try:
        return c.datasets.invent(dataset_prompt="p", rows=1, estimate=True).available_credits
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--iterations", type=int, default=5)
    ap.add_argument("--model", default="Qwen/Qwen3.5-2B")
    args = ap.parse_args()

    client = Adaption()
    before = balance(client)
    log(f"credits before: {before}")

    # every finished diyo dataset, downloaded if missing
    raw = ROOT / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    inputs = []
    total = 0
    # Only raw generation outputs. Exclude Adaption's derived datasets (it re-uploads
    # "behaviour-v0 (augmented)" and our own processed "behaviour-v1"), which duplicated rows.
    skip = ("augmented", "behaviour-v", "behaviour-r")
    seen = set()
    for d in client.datasets.list():
        if not d.name.startswith("diyo-") or d.status != "succeeded" or not d.row_count:
            continue
        if any(x in d.name for x in skip) or d.name in seen:
            continue
        seen.add(d.name)
        path = raw / f"{d.name}.jsonl"
        if not path.exists():
            client.datasets.download(d.dataset_id, file_format="jsonl").write_to_file(str(path))
        inputs.append(str(path))
        total += d.row_count
        log(f"{d.name}: {d.row_count} rows")

    inputs.append(str(ROOT / "data" / "train" / "asr-robust-v0.jsonl"))
    log(f"{len(inputs)} sources, {total} raw rows")

    csv = ROOT / "data" / "train" / f"diyo-behaviour-{args.name}.csv"
    subprocess.run([sys.executable, str(ROOT / "data" / "prepare_training.py"),
                    "--input", *inputs, "--output", str(csv)], check=True)

    ds = client.datasets.upload_file(
        str(csv), name=f"diyo-behaviour-{args.name}", processing_mode="raw",
        column_mapping={"prompt": "prompt", "completion": "completion"})
    st = client.datasets.wait_for_completion(ds.dataset_id)
    log(f"uploaded: {st.status} rows={st.row_count}")

    run = client.autoscientist.create(
        dataset_id=ds.dataset_id, model=args.model, training_method="instruction",
        data_format="instruction", augmentation_domain_rows=0, augmentation_general_rows=0,
        max_iterations=args.iterations,
        idempotency_key=f"diyo-{args.name}-{st.row_count}-{args.iterations}")
    log(f"run {run.id} started ({args.iterations} iterations)")

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

    after = balance(client)
    summary = {"name": args.name, "run_id": run.id, "dataset_id": ds.dataset_id,
               "rows": st.row_count, "sources": len(inputs), "status": cur.status,
               "iterations": cur.iterations_completed, "best_win_rate": cur.best_win_rate,
               "credits_before": before, "credits_after": after,
               "credits_spent": round(before - after, 1) if None not in (before, after) else None}

    if cur.status == "succeeded":
        tmp = ROOT / "data" / "models" / run.id
        tmp.mkdir(parents=True, exist_ok=True)
        client.autoscientist.download(run.id).write_to_file(str(tmp / "adapter.tar.zst"))
        unpack = tmp / "adapter"
        shutil.rmtree(unpack, ignore_errors=True)
        unpack.mkdir()
        subprocess.run(["tar", "xf", str(tmp / "adapter.tar.zst"), "-C", str(unpack)], check=True)
        dest = ROOT / "artifacts" / "diyo-1-lora"
        shutil.rmtree(dest, ignore_errors=True)
        dest.mkdir(parents=True)
        for f in unpack.iterdir():
            if f.is_file():
                shutil.copy2(f, dest / f.name)
        summary["adapter_files"] = sorted(p.name for p in dest.iterdir())
        log(f"adapter -> {dest}")

    (ROOT / "data" / "train" / f"{args.name}.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    log(json.dumps(summary, indent=1))
    sys.exit(0 if cur.status == "succeeded" else 1)


if __name__ == "__main__":
    main()
