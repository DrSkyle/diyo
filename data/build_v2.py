#!/usr/bin/env python3
"""The whole v1 chain, unattended: wait for datasets, merge, train, extract the adapter.

    ./.venv/bin/python data/build_v2.py

Writes data/train/v1.json with the run id, win rate and the credit delta, and replaces
artifacts/diyo-1-lora/ with the new adapter. It does not commit or push.
"""

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

WANT = ["diyo-health-v1", "diyo-agriculture-v1", "diyo-paperwork-v1",
        "diyo-rights-v1", "diyo-daily-v1"]
MODEL = "Qwen/Qwen3.5-2B"
CSV = ROOT / "data" / "train" / "diyo-behaviour-v1.csv"
SUMMARY = ROOT / "data" / "train" / "v1.json"


def log(msg):
    print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} {msg}", flush=True)


def balance(client):
    try:
        return client.datasets.invent(
            dataset_prompt="probe", rows=1, estimate=True).available_credits
    except Exception:
        return None


def wait_for_datasets(client):
    """Poll until every expected dataset leaves `running`."""
    deadline = time.time() + 120 * 60
    while time.time() < deadline:
        found = {d.name: d for d in client.datasets.list() if d.name in WANT}
        states = {n: (found[n].status if n in found else "missing") for n in WANT}
        if all(found.get(n) and found[n].status == "succeeded" for n in WANT):
            log("all datasets succeeded")
            return found
        bad = [n for n, s in states.items() if s == "failed"]
        if bad:
            sys.exit(f"dataset(s) failed: {bad}")
        log("waiting: " + ", ".join(f"{n}={s}" for n, s in states.items()))
        time.sleep(90)
    sys.exit("timed out waiting for datasets")


def download(client, found):
    out = ROOT / "data" / "raw"
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for name in WANT:
        path = out / f"{name}.jsonl"
        if not path.exists():
            client.datasets.download(found[name].dataset_id, file_format="jsonl") \
                .write_to_file(str(path))
        paths.append(str(path))
        log(f"{name}: {sum(1 for _ in path.open(encoding='utf-8'))} rows")
    return paths


def main():
    client = Adaption()
    before = balance(client)
    log(f"credits before: {before}")

    found = wait_for_datasets(client)
    inputs = download(client, found)
    inputs.append(str(ROOT / "data" / "train" / "asr-robust-v0.jsonl"))

    subprocess.run([sys.executable, str(ROOT / "data" / "prepare_training.py"),
                    "--input", *inputs, "--output", str(CSV)], check=True)

    ds = client.datasets.upload_file(
        str(CSV), name="diyo-behaviour-v1", processing_mode="raw",
        column_mapping={"prompt": "prompt", "completion": "completion"})
    status = client.datasets.wait_for_completion(ds.dataset_id)
    log(f"uploaded: status={status.status} rows={status.row_count}")

    run = client.autoscientist.create(
        dataset_id=ds.dataset_id, model=MODEL, training_method="instruction",
        data_format="instruction",
        augmentation_domain_rows=0, augmentation_general_rows=0,
        max_iterations=2,
        idempotency_key=f"diyo-behaviour-v1-{status.row_count}",
    )
    log(f"run {run.id} {run.status}")

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
    summary = {"run_id": run.id, "dataset_id": ds.dataset_id, "model": MODEL,
               "rows": status.row_count, "status": cur.status,
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
        subprocess.run(["tar", "xf", str(tmp / "adapter.tar.zst"), "-C", str(unpack)],
                       check=True)
        dest = ROOT / "artifacts" / "diyo-1-lora"
        shutil.rmtree(dest, ignore_errors=True)
        dest.mkdir(parents=True)
        for f in unpack.iterdir():
            if f.is_file() and f.suffix != ".json" or f.name == "adapter_config.json":
                shutil.copy2(f, dest / f.name)
        summary["adapter_files"] = sorted(p.name for p in dest.iterdir())
        log(f"adapter written to {dest}")

    SUMMARY.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    log(json.dumps(summary, indent=1))
    sys.exit(0 if cur.status == "succeeded" else 1)


if __name__ == "__main__":
    main()
