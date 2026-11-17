#!/usr/bin/env python3
"""The improvement loop: eval failures → targeted data requests → new model.

    python3 pipeline/improve.py --model himalaya-e2b
    python3 pipeline/improve.py --model himalaya-e2b --json out/requests.json

Reads the eval set and the cached answers from `evals/results/answers-<model>.json`, classifies
every failure, and emits one Adaption generation request per failure class. The point is that
credits are spent against a measured weakness, never on "more data".
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))
import run_eval  # noqa: E402

# failure class -> what to generate
REQUESTS = {
    "no_referral": {
        "why": "Answer did not name the office or person to see.",
        "prompt": ("Nepali health and paperwork answers that always end by naming the exact "
                   "office to visit: स्वास्थ्य चौकी, अस्पताल, कृषि ज्ञान केन्द्र, मालपोत "
                   "कार्यालय, नापी कार्यालय, जिल्ला प्रशासन कार्यालय, वडा कार्यालय, श्रम "
                   "कार्यालय. Two to four short spoken sentences. Never invent a fee."),
        "rows": 400,
    },
    "over_refusal": {
        "why": "Refused a legitimate question. Over-caution is a product failure.",
        "prompt": ("Nepali questions that ARE answerable but look sensitive — a birthday, a "
                   "citizenship correction, boiling water, a bus route, crop spacing — answered "
                   "fully and briefly. Contrast rows: the same shape of question where refusing "
                   "IS correct, so the model learns the boundary."),
        "rows": 400,
    },
    "wrong_number": {
        "why": "Arithmetic or a numeric fact was wrong in Devanagari.",
        "prompt": ("Nepali arithmetic with Devanagari numerals: price × quantity, change, area, "
                   "ages, dates in Bikram Sambat, unit conversion (केजी, मन, पाथी, रोपनी). "
                   "Show the result in Devanagari digits, one sentence. Include the correct "
                   "answer in the completion."),
        "rows": 300,
    },
    "hallucinated_entity": {
        "why": "Invented a company, number or place that does not exist in Nepal.",
        "prompt": ("Nepali everyday questions whose answers involve real Nepali entities only: "
                   "Ncell, NTC, eSewa, Khalti, IME Pay, NEA, KUKL, Nepal Airlines, 100 police, "
                   "102 ambulance, 101 fire, and named government offices. Never invent a brand, "
                   "a number or a place. If unsure, say मलाई थाहा छैन."),
        "rows": 300,
    },
    "not_nepali": {
        "why": "Answered in English or Hindi instead of Nepali.",
        "prompt": ("Nepali-English code-switched questions (मेरो phone मा recharge…) answered "
                   "entirely in Nepali Devanagari, short and spoken. Never answer in Hindi. "
                   "Keep proper nouns in Latin only when unavoidable."),
        "rows": 300,
    },
    "unknown_missing": {
        "why": "Did not admit it cannot know live or private data.",
        "prompt": ("Nepali questions that need live or private data — today's weather, today's "
                   "bus fare, who owns a plot, a school's fee this year, a hospital's OPD "
                   "schedule — answered with मलाई थाहा छैन plus where to ask, in two sentences."),
        "rows": 300,
    },
    "missing_content": {
        "why": "Answer was too thin or missed the danger signs.",
        "prompt": ("Nepali triage answers that name the danger signs first (age, can the person "
                   "drink, breathing fast, blood, limp, unable to feed), ask at most one "
                   "follow-up, and name the facility. No diagnosis, no dose."),
        "rows": 400,
    },
}


def classify(fail):
    if "not Nepali" in fail:
        return "not_nepali"
    if "did not refuse" in fail:
        return "over_refusal"
    if "did not admit" in fail:
        return "unknown_missing"
    if "contains forbidden" in fail:
        return "hallucinated_entity"
    if "missing any of" in fail:
        return "no_referral"
    return "missing_content"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="himalaya-e2b")
    ap.add_argument("--json", help="write requests here")
    args = ap.parse_args()

    answers_path = ROOT / "evals" / "results" / f"answers-{args.model}.json"
    if not answers_path.exists():
        sys.exit(f"no answers for {args.model}; run evals/run_eval.py first")
    answers = json.loads(answers_path.read_text(encoding="utf-8"))
    items = run_eval.load()

    buckets, failures = {}, []
    for item in items:
        answer = answers.get(item["id"])
        if answer is None:
            continue
        answer = run_eval.strip_thinking(answer)
        fails = run_eval.check(item, answer)
        if not fails:
            continue
        bucket = classify(fails[0])
        buckets.setdefault(bucket, []).append(item["id"])
        failures.append({"id": item["id"], "domain": item["domain"],
                         "fails": fails, "bucket": bucket,
                         "answer": answer[:200]})

    total = len([i for i in items if i["id"] in answers])
    print(f"model: {args.model}   scored: {total}   failures: {len(failures)}\n")
    print(f"{'bucket':<20}{'cases':<7}rows to generate")
    for bucket, ids in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        rows = REQUESTS.get(bucket, {}).get("rows", 0)
        print(f"{bucket:<20}{len(ids):<7}{rows}   ({', '.join(ids[:5])})")

    requests = []
    for bucket, ids in buckets.items():
        spec = REQUESTS.get(bucket)
        if not spec:
            continue
        requests.append({
            "bucket": bucket,
            "covers": ids,
            "why": spec["why"],
            "dataset_prompt": spec["prompt"],
            "rows": spec["rows"],
            "idempotency_key": f"diyo-{bucket}-v1",
        })

    out = {"model": args.model, "scored": total, "failures": failures, "requests": requests}
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nwrote {args.json}")
    else:
        print("\nnext: generate these, merge, re-run eval, repeat until 30/30")


if __name__ == "__main__":
    main()
