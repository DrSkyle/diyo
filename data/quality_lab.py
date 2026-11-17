#!/usr/bin/env python3
"""Find the adapt configuration that scores highest, without spending on the full dataset.

Adaption grades a dataset A-E on a 0-10 score, split into prompt ("message") quality and
completion quality. Our completions sit at the 2nd percentile, so the lever is how the completion
is generated: blueprint (system instruction), length, grounding and recipes.

This uploads a handful of small copies, adapts each with a different configuration, and prints the
grade, score and average completion length so we can pick before scaling.

    python3 data/quality_lab.py --rows 240
"""

import argparse
import json
import os
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

BLUEPRINT = (
    "You write answers for Diyo, a Nepali assistant used offline on a cheap Android phone in rural "
    "Nepal. Write in Nepali (Devanagari) only, addressing the reader as तपाईं. "
    "Open with two or three concrete things the person can do right now, then the danger signs "
    "that mean go immediately, then the exact office or person to see. "
    "Name real Nepali institutions only. Never state a medicine or pesticide dose. Never invent a "
    "fee, a price, a phone number or a company. If the answer needs live or private data, say "
    "मलाई थाहा छैन and name who to ask. No markdown, no bullet lists, no English sentences."
)

VARIANTS = {
    "concise": {"brand_controls": {"length": "concise", "blueprint": BLUEPRINT}},
    "detailed": {"brand_controls": {"length": "detailed", "blueprint": BLUEPRINT}},
    "grounded": {
        "brand_controls": {"length": "detailed", "blueprint": BLUEPRINT,
                           "hallucination_mitigation": True},
        "recipe_specification": {"recipes": {"deduplication": True, "prompt_rephrase": True}},
    },
}


def log(m):
    print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} {m}", flush=True)


def sample_csv(rows):
    src = ROOT / "data" / "train" / "diyo-behaviour-r3.csv"
    if not src.exists():
        src = ROOT / "data" / "train" / "diyo-behaviour-v1.csv"
    import random
    lines = src.read_text(encoding="utf-8").splitlines()
    header, body = lines[0], lines[1:]
    random.Random(11).shuffle(body)
    out = ROOT / "data" / "train" / f"quality-sample-{rows}.csv"
    out.write_text("\n".join([header] + body[:rows]) + "\n", encoding="utf-8")
    return out


def poll_adapt(c, ds_id, label):
    deadline = time.time() + 60 * 60
    while time.time() < deadline:
        d = c.datasets.get(ds_id)
        if d.status in ("succeeded", "failed"):
            log(f"{label}: adapt {d.status}")
            return d.status == "succeeded"
        time.sleep(20)
    return False


def poll_eval(c, ds_id, label):
    deadline = time.time() + 45 * 60
    while time.time() < deadline:
        ev = c.datasets.get_evaluation(ds_id)
        st = getattr(ev, "status", None)
        if st in ("succeeded", "failed", "skipped"):
            q = getattr(ev, "quality", None)
            return (q.model_dump() if hasattr(q, "model_dump") else q) if q else None
        time.sleep(20)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=240)
    ap.add_argument("--only", nargs="*", help="subset of variants")
    args = ap.parse_args()

    c = Adaption()
    before = c.datasets.invent(dataset_prompt="p", rows=1, estimate=True).available_credits
    log(f"credits: {before}")

    csv_path = sample_csv(args.rows)
    results = {}
    names = args.only or list(VARIANTS)

    for name in names:
        cfg = VARIANTS[name]
        ds = c.datasets.upload_file(
            str(csv_path), name=f"diyo-lab-{name}", processing_mode="raw",
            column_mapping={"prompt": "prompt", "completion": "completion"})
        st = c.datasets.wait_for_completion(ds.dataset_id)
        log(f"{name}: uploaded {st.row_count} rows")

        est = c.datasets.adapt(ds.dataset_id, training_type="instruction_dataset",
                               column_mapping={"prompt": "prompt", "completion": "completion"},
                               estimate=True, **cfg)
        log(f"{name}: estimated {est.estimated_credits_consumed} credits")

        c.datasets.adapt(ds.dataset_id, training_type="instruction_dataset",
                         column_mapping={"prompt": "prompt", "completion": "completion"}, **cfg)
        if not poll_adapt(c, ds.dataset_id, name):
            results[name] = {"status": "adapt_failed"}
            continue
        q = poll_eval(c, ds.dataset_id, name)
        results[name] = {"status": "ok", "quality": q}

    after = c.datasets.invent(dataset_prompt="p", rows=1, estimate=True).available_credits
    (ROOT / "data" / "train" / "quality-lab.json").write_text(json.dumps(
        {"rows": args.rows, "credits_before": before, "credits_after": after,
         "results": results}, indent=1), encoding="utf-8")

    print(f"\n{'variant':<12}{'grade':<8}{'score':<8}{'pct':<8}")
    for name, r in results.items():
        q = (r.get("quality") or {})
        print(f"{name:<12}{str(q.get('grade_after')):<8}{str(q.get('score_after')):<8}"
              f"{str(q.get('percentile_after')):<8}")
    print(f"\ncredits spent: {round((before or 0) - (after or 0), 1)}")


if __name__ == "__main__":
    main()
