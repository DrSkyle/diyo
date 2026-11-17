#!/usr/bin/env python3
"""Consent for Diyo Voice Commons: records, scopes, withdrawal, anonymisation.

The rule this file enforces: **audio is only usable for a scope the contributor ticked.**
Nothing downstream may widen that. If a take is donated for "listen", it can never train a voice.
"""

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCOPES = ("listen", "speak", "style")
REQUIRED = ("record_version", "granted_at", "scopes", "purpose", "audio_license")
CURRENT_VERSION = 1

# style without speak makes no sense: style learns how a voice speaks, speak learns the voice
IMPLIES = {"style": ("speak",), "speak": ()}


def problems(record):
    """Return a list of reasons this consent record cannot be used. Empty == valid."""
    out = []
    for key in REQUIRED:
        if key not in record:
            out.append(f"missing:{key}")
    if record.get("record_version") != CURRENT_VERSION:
        out.append(f"unsupported_version:{record.get('record_version')}")
    scopes = record.get("scopes") or {}
    unknown = set(scopes) - set(SCOPES)
    if unknown:
        out.append(f"unknown_scope:{','.join(sorted(unknown))}")
    for scope, needs in IMPLIES.items():
        if scopes.get(scope) and not all(scopes.get(n) for n in needs):
            out.append(f"scope_order:{scope}_requires_{'+'.join(needs)}")
    if not any(scopes.get(s) for s in SCOPES):
        out.append("no_scope_granted")
    if not record.get("purpose"):
        out.append("missing:purpose")
    return out


def contributor_id(identifier, salt):
    """Stable, non-reversible id. Same person, same id across sessions; nobody can reverse it."""
    if not salt:
        raise ValueError("salt required — an unsalted hash of a phone number is not anonymous")
    return "vc_" + hashlib.sha256(f"{salt}\x00{identifier}".encode()).hexdigest()[:20]


def allowed_scopes(record):
    scopes = record.get("scopes") or {}
    return {s for s in SCOPES if scopes.get(s)}


PHONE = re.compile(r"(?:\+?977[-\s]?)?9\d{9}|\b\d{3}[-\s]\d{3}[-\s]\d{4}\b")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
LONGNUM = re.compile(r"\b\d{6,}\b")
DEVNUM = re.compile(r"[०-९]{6,}")


def redact(text):
    """Remove the things a transcript should never carry into a training set."""
    text = EMAIL.sub("[इमेल]", text)
    text = PHONE.sub("[फोन]", text)
    text = LONGNUM.sub("[नम्बर]", text)
    text = DEVNUM.sub("[नम्बर]", text)
    return re.sub(r"\s+", " ", text).strip()


def withdraw(contributor, withdrawals_path, reason=""):
    """Record a withdrawal and return a receipt the contributor can keep."""
    path = Path(withdrawals_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entry = {"contributor": contributor, "withdrawn_at": stamp, "reason": reason,
             "effective": "next dataset rebuild, within 30 days"}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    digest = hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()[:16]
    return {"receipt": f"WD-{digest}", **entry}


def withdrawn_set(withdrawals_path):
    path = Path(withdrawals_path)
    if not path.exists():
        return set()
    out = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.add(json.loads(line)["contributor"])
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", help="validate a consent.json")
    ap.add_argument("--withdraw", help="contributor id to withdraw")
    ap.add_argument("--withdrawals", default="data/voice-commons/withdrawals.jsonl")
    args = ap.parse_args()

    if args.check:
        record = json.loads(Path(args.check).read_text(encoding="utf-8"))
        bad = problems(record)
        print("invalid: " + ", ".join(bad) if bad else "valid")
        sys.exit(1 if bad else 0)

    if args.withdraw:
        print(json.dumps(withdraw(args.withdraw, args.withdrawals), ensure_ascii=False, indent=1))
        return

    ap.print_help()


if __name__ == "__main__":
    main()
