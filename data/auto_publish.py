#!/usr/bin/env python3
"""Wait for a training run, then publish the adapter and dispatch both evals — unattended.

    python3 data/auto_publish.py --run-id 4f885d92-... --name r7-2b

No promises in a chat message: this polls, packages, creates the release, and triggers the 32-case
and holdout evaluations itself.
"""

import argparse
import json
import os
import shutil
import subprocess
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


def sh(*args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--name", required=True)
    args = ap.parse_args()

    client = Adaption()
    last = None
    while True:
        run = client.autoscientist.get(args.run_id)
        line = f"{run.status} iter={run.iterations_completed} win={run.best_win_rate}"
        if line != last:
            log(line)
            last = line
        if run.status in ("succeeded", "failed", "cancelled"):
            break
        time.sleep(60)

    if run.status != "succeeded":
        log(f"run ended {run.status}; nothing published")
        return

    tmp = ROOT / "data" / "models" / args.run_id
    tmp.mkdir(parents=True, exist_ok=True)
    client.autoscientist.download(args.run_id).write_to_file(str(tmp / "adapter.tar.zst"))
    unpack = tmp / "adapter"
    shutil.rmtree(unpack, ignore_errors=True)
    unpack.mkdir()
    sh("tar", "xf", str(tmp / "adapter.tar.zst"), "-C", str(unpack), check=True)

    tarball = ROOT / "artifacts" / f"diyo-{args.name}.tar.gz"
    tarball.parent.mkdir(exist_ok=True)
    sh("tar", "czf", str(tarball), "-C", str(unpack), ".", check=True)
    log(f"packaged {tarball} ({tarball.stat().st_size/1e6:.0f} MB)")

    tag = f"diyo-1-{args.name}"
    notes = (f"LoRA for Qwen3.5-2B from run {args.run_id}. "
             f"Win rate {run.best_win_rate}, {run.iterations_completed} iterations.")
    r = sh("gh", "release", "create", tag, str(tarball), "--title",
           f"Diyo-1 {args.name}", "--notes", notes)
    if r.returncode != 0 and "already exists" not in (r.stderr or ""):
        log("release create: " + (r.stderr or r.stdout)[:300])
    sh("gh", "release", "upload", tag, str(tarball), "--clobber")
    # An eval against an empty release is a wasted run (r10). Verify the asset is downloadable.
    api = sh("gh", "api", f"repos/DrSkyle/diyo/releases/tags/{tag}",
             "--jq", '.assets | map(select(.name == env.A)) | length',
             env={**os.environ, "A": tarball.name})
    if api.stdout.strip() != "1":
        raise SystemExit(f"asset missing from release {tag}: {api.stdout} {api.stderr}")
    probe = sh("curl", "-sL", "-r", "0-0", "-o", "/dev/null", "-w", "%{http_code}",
               f"https://github.com/DrSkyle/diyo/releases/download/{tag}/{tarball.name}")
    if probe.stdout.strip() not in ("200", "206"):
        raise SystemExit(f"asset not downloadable (HTTP {probe.stdout.strip()}) for {tag}")
    log(f"release {tag} verified")

    url = f"https://github.com/DrSkyle/diyo/releases/download/{tag}/diyo-{args.name}.tar.gz"
    for label, extra in (("32", []), ("holdout", ["-f", "eval_file=evals/holdout.jsonl"])):
        model = f"diyo-1-{args.name}" + ("-holdout" if label == "holdout" else "")
        r = sh("gh", "workflow", "run", "eval.yml", "-f", f"lora_url={url}",
               "-f", f"model_name={model}", *extra)
        log(f"eval {label}: {'dispatched' if r.returncode == 0 else (r.stderr or '')[:120]}")

    (ROOT / "data" / "train" / f"{args.name}.json").write_text(json.dumps({
        "run_id": args.run_id, "status": run.status,
        "iterations": run.iterations_completed, "best_win_rate": run.best_win_rate,
        "release": tag, "lora_url": url,
        "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=1), encoding="utf-8")
    log("done — scores will appear on the eval workflow runs")


if __name__ == "__main__":
    main()
