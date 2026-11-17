#!/usr/bin/env python3
"""Probe Adaption: what domains exist, what do they cost, what is left in the account.

    ./.venv/bin/python data/adaption_probe.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from adaption import Adaption  # noqa: E402

client = Adaption()

PILOT_ROWS = 200
PILOT_PROMPT = (
    "Nepali (Devanagari) instruction turns for a rural offline assistant used on a low-end "
    "Android phone in Nepal. Health triage and referral only: recognise danger signs, ask the "
    "few facts that change urgency (age, can the person drink, how long, fever, breathing), "
    "and name the nearest kind of health facility. Never state a medicine name, dose, or "
    "diagnosis. When the assistant cannot know something it must say मलाई थाहा छैन and name "
    "which human or office to ask. Respectful register (तपाईं), short spoken sentences of two "
    "to five sentences, no tables or bullet glyphs. Include messy realistic inputs: typos, "
    "Romanised Nepali, Nepali-English mixing, half-sentences, eastern and western regional "
    "words. Every answer must be safe to read aloud to a worried parent."
)

print("== domains ==")
domains = client.datasets.invent_domains()
want = ("medic", "health", "legal", "agri", "language", "locale", "educat", "civic",
        "govern", "financ")
found = []
for d in domains.domains:
    line = f"{d.code:<28} {d.title}"
    subs = getattr(d, "subdomains", None) or []
    found.append((d.code, d.title, [s.code for s in subs]))
    print(line)
    for s in subs:
        mark = "*" if any(w in s.code.lower() or w in (s.title or "").lower() for w in want) else " "
        print(f"  {mark} {s.code:<40} {s.title}")

print("\n== estimate for the Diyo pilot ==")
est = client.datasets.invent(
    dataset_prompt=PILOT_PROMPT,
    domains=["medical"] if any(c == "medical" for c, _, _ in found) else None,
    rows=PILOT_ROWS,
    estimate=True,
)
print(f"rows          : {PILOT_ROWS}")
print(f"est. credits  : {est.estimated_credits}")
print(f"available     : {est.available_credits}")
if est.available_credits and est.estimated_credits:
    share = est.estimated_credits / est.available_credits
    print(f"share of plan : {share:.1%}")
print("\nNothing was created or charged.")
