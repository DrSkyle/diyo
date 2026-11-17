#!/usr/bin/env python3
"""Wait for an AutoScientist run, then download it and record what it cost.

    python3 data/finish_run.py --run-id c4866724-... --out data/models

Resumable: safe to kill and re-run. Writes data/models/<run-id>/ with the artefacts and a
manifest containing the credit delta, so the next run's cost is a number, not a guess.
"""

import argparse
import json
import os
import shutil
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


def credits(client):
    """Balance probe. Free: an estimate creates and charges nothing."""
    try:
        return client.datasets.invent(
            dataset_prompt="balance probe", rows=1, estimate=True).available_credits
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out", default="data/models")
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--from-balance", type=float, default=2138.0,
                    help="balance before the run, for the cost delta")
    args = ap.parse_args()

    client = Adaption()
    out = Path(args.out) / args.run_id
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"

    last = None
    while True:
        run = client.autoscientist.get(args.run_id)
        line = (f"{run.status} iter={run.iterations_completed} "
                f"win_rate={run.best_win_rate}")
        if line != last:
            print(datetime.now(timezone.utc).strftime("%H:%M:%S"), line, flush=True)
            last = line
        if run.status in ("succeeded", "failed", "cancelled"):
            break
        time.sleep(args.interval)

    after = credits(client)
    manifest = {
        "run_id": args.run_id,
        "status": run.status,
        "iterations": run.iterations_completed,
        "best_win_rate": run.best_win_rate,
        "error": str(getattr(run, "error", None) or ""),
        "credits_before": args.from_balance,
        "credits_after": after,
        "credits_spent": (round(args.from_balance - after, 1)
                          if after is not None else None),
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    if run.status == "succeeded":
        print("downloading artefacts…", flush=True)
        try:
            dest = client.autoscientist.download(args.run_id)
            tmp = out / "_download"
            if hasattr(dest, "write_to_file"):
                suffix = getattr(dest, "file_format", "bin")
                dest.write_to_file(str(tmp.with_suffix(f".{suffix}")))
            elif isinstance(dest, (bytes, bytearray)):
                (out / "model.bin").write_bytes(dest)
            elif hasattr(dest, "read"):
                (out / "model.bin").write_bytes(dest.read())
            else:
                manifest["download_note"] = f"unknown download type: {type(dest).__name__}"
        except Exception as exc:  # noqa: BLE001 - report, do not lose the manifest
            manifest["download_error"] = f"{type(exc).__name__}: {exc}"

    files = []
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            files.append({"name": str(p.relative_to(out)), "bytes": p.stat().st_size})
    manifest["files"] = files

    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(json.dumps(manifest, indent=1))
    shutil.rmtree(out / "_download", ignore_errors=True)
    sys.exit(0 if run.status == "succeeded" else 1)


if __name__ == "__main__":
    main()
