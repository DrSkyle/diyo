#!/usr/bin/env python3
"""Generate Diyo's Nepali training data with Adaption's Invent a Dataset.

    ./.venv/bin/python data/invent.py --phase health            # estimate only
    ./.venv/bin/python data/invent.py --phase health --go       # generate + download

Without --go nothing is created or charged.
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

BASE = (
    "Nepali (Devanagari) instruction turns for दियो (Diyo), an offline assistant used on a "
    "low-end Android phone in rural Nepal. "
    "Each row is exactly one user turn and one assistant answer. The prompt must be a single "
    "messy user message: no assistant-style text, no self-answered questions, no follow-up "
    "turns inside the prompt. "
    "Rules for every answer: respectful register (तपाईं); two to five short spoken sentences, "
    "because the answer is read aloud by text-to-speech; no tables, no bullet glyphs, no "
    "headings, no Latin script except unavoidable proper nouns; never state a medicine name, "
    "a dose, or a diagnosis; when the answer needs live data, a private record, or a "
    "professional judgment, say मलाई थाहा छैन and name the human or office to ask. "
    "Write standard Unicode Devanagari only. In particular write तपाईं (not तपार्इं) and "
    "मलाई (not मलार्इ): never substitute a half-र plus इ for ई, and never use Preeti-style "
    "font glyphs. "
    "Inputs should be realistic and messy: typos, Romanised Nepali, Nepali-English mixing, "
    "half-sentences, and regional vocabulary from eastern (झापा, विराटनगर) and western "
    "(कर्णाली, सुर्खेत) Nepal."
)

PHASES = {
    "health": (
        "Health triage and referral for a rural household. Cover fever in a child, "
        "breathing difficulty, chest pain, diarrhoea and dehydration, snakebite, burns, "
        "pregnancy danger signs, newborn care, and what to do while travelling to a health "
        "post. Every answer must ask the few facts that change urgency (age, can the person "
        "drink, how many days, is there blood, is breathing fast) and must name the level of "
        "facility to go to.",
        ["medical.pediatric_health", "medical.emergency_first_aid",
         "medical.symptoms_diagnosis", "medical.preventive_care"],
    ),
    "agriculture": (
        "Farming advice for smallholders in the Terai and mid-hills. Cover rice, maize, wheat, "
        "potato and vegetable problems: yellowing leaves, pests, blast and blight, irrigation, "
        "compost and fertiliser timing, seed selection, and storage after harvest. Answers "
        "must name the कृषि ज्ञान केन्द्र or कृषि प्राविधिक for anything involving pesticide "
        "quantity or pesticide safety, and must never give a chemical dose.",
        ["agriculture.crop_farming", "agriculture.pest_disease_management",
         "agriculture.irrigation_water", "agriculture.soil_science"],
    ),
    "paperwork": (
        "Nepali government paperwork explained in plain spoken Nepali. Cover citizenship "
        "certificate, birth registration, correcting a wrong date of birth, land ownership "
        "papers, marriage registration, small shop registration, PAN/VAT, passport, driving "
        "licence, and school admission documents. Each answer lists what to bring in general "
        "terms, names the office (जिल्ला प्रशासन कार्यालय, वडा कार्यालय, मालपोत कार्यालय, "
        "नापी कार्यालय, राहदानी विभाग, यातायात कार्यालय), and says rules can change so the "
        "person should confirm there. Never invent a fee amount.",
        ["legal.administrative_law", "legal.real_estate_law", "legal.family_law"],
    ),
    "rights": (
        "Everyday legal rights and where to get help in Nepal, explained simply. Cover unpaid "
        "wages, landlord and tenant problems, domestic violence and safe reporting, child "
        "marriage, dowry, workplace injury, consumer complaints, and free legal aid. Each "
        "answer names the office or service (प्रहरी, वडा कार्यालय, श्रम कार्यालय, "
        "न्याय सेवा, महिला तथा बालबालिका कार्यालय) and avoids promising an outcome.",
        ["legal.civil_law", "legal.employment_law", "legal.family_law"],
    ),
    "daily": (
        "Everyday life in Nepal. Cover mobile recharge and data packs, sending and receiving "
        "money with eSewa, Khalti and IME Pay, bus fares and routes, electricity and water "
        "bills, load-shedding, weather that requires an online lookup, reading a "
        "prescription slip, reading a bank slip, school and exam scheduling, and simple "
        "arithmetic in Devanagari numerals (price times quantity, change, area, dates). "
        "Use only real Nepali entities: Ncell, NTC, eSewa, Khalti, IME Pay, NEA, KUKL, "
        "Nepal Airlines, and do not invent company names.",
        ["language.multilingual_communication", "language.localization"],
    ),
    "basics": (
        "The exact behaviours the assistant keeps getting wrong, drilled directly.\n"
        "1) Arithmetic in Devanagari numerals, shown as one sentence: price × quantity, change, "
        "area, age differences, dates in Bikram Sambat. The completion must contain the correct "
        "answer.\n"
        "2) Real Nepali entities only: police १००, ambulance १०२, fire १०१, Ncell, NTC, eSewa, "
        "Khalti, IME Pay, NEA, KUKL, and the offices जिल्ला प्रशासन, मालपोत, नापी, वडा, "
        "श्रम कार्यालय. Never invent a company, a number or a place.\n"
        "3) Over-refusal contrast: questions that look sensitive but are answerable (how to boil "
        "water, how to correct a birth date, what documents a passport needs) answered fully. "
        "Paired with questions where refusing IS right, so the boundary is explicit.\n"
        "4) मलाई थाहा छैन where the answer needs live data or a private record, followed by who "
        "to ask.",
        ["language.multilingual_communication", "academic_education.language_arts"],
    ),
}


def build(phase, rows, extra=""):
    prompt, subs = PHASES[phase]
    text = f"{BASE}\n\nFocus: {prompt}"
    if extra:
        text += f"\n\nAdditional requirement: {extra}"
    return text[:10000], subs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True, choices=sorted(PHASES))
    ap.add_argument("--rows", type=int, default=200)
    ap.add_argument("--go", action="store_true", help="actually generate and charge credits")
    ap.add_argument("--extra", default="", help="extra instruction appended to the prompt")
    ap.add_argument("--name", default=None)
    args = ap.parse_args()

    client = Adaption()
    prompt, subs = build(args.phase, args.rows, args.extra)
    name = args.name or f"diyo-{args.phase}-v1"

    est = client.datasets.invent(
        dataset_prompt=prompt, subdomains=subs, rows=args.rows, estimate=True)
    print(f"phase={args.phase} rows={args.rows} subs={len(subs)}")
    print(f"estimated credits: {est.estimated_credits}  available: {est.available_credits}")
    if not args.go:
        print("\n(estimate only — pass --go to generate)")
        return

    ds = client.datasets.invent(
        dataset_prompt=prompt,
        subdomains=subs,
        rows=args.rows,
        name=name,
        training_type="instruction_dataset",
        idempotency_key=f"{name}-{args.rows}",
    )
    print(f"created {ds.id} status={ds.status}")

    while True:
        rec = client.datasets.get(ds.id)
        if rec.status == "succeeded":
            break
        if rec.status == "failed":
            err = rec.error_data
            sys.exit(f"failed: {(err and err.message) or 'unknown error'}")
        time.sleep(5)
    print(f"generated {rec.row_count} rows")

    out = ROOT / "data" / "raw" / f"{name}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    client.datasets.download(ds.id, file_format="jsonl").write_to_file(str(out))
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB)")
    (ROOT / "data" / "raw" / f"{name}.meta.json").write_text(
        json.dumps({"dataset_id": ds.id, "name": name, "phase": args.phase,
                    "rows": args.rows, "prompt": prompt, "subdomains": subs},
                   ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
