#!/usr/bin/env python3
"""Poll an Adaption dataset to completion and download it.

    ./.venv/bin/python data/fetch.py --name diyo-health-v1
    ./.venv/bin/python data/fetch.py --id 2e6974ef-...
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id")
    ap.add_argument("--name")
    ap.add_argument("--interval", type=int, default=15)
    args = ap.parse_args()

    client = Adaption()
    ds_id, name = args.id, args.name
    if not ds_id:
        if not name:
            sys.exit("pass --id or --name")
        for d in client.datasets.list():
            if d.name == name:
                ds_id = d.dataset_id
                break
        if not ds_id:
            sys.exit(f"no dataset named {name}")

    last = None
    while True:
        rec = client.datasets.get(ds_id)
        status = rec.status
        if status != last:
            print(f"{ds_id} {status} rows={rec.row_count} progress={rec.progress}", flush=True)
            last = status
        if status == "succeeded":
            break
        if status == "failed":
            err = rec.error_data
            sys.exit(f"failed: {(err and err.message) or 'unknown error'}")
        time.sleep(args.interval)

    out = ROOT / "data" / "raw" / f"{args.name or rec.name or ds_id}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    client.datasets.download(ds_id, file_format="jsonl").write_to_file(str(out))
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB, {rec.row_count} rows)")
    (out.with_suffix(".meta.json")).write_text(
        json.dumps({"dataset_id": ds_id, "name": rec.name, "rows": rec.row_count},
                   ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
