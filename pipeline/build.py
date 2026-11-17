#!/usr/bin/env python3
"""Turn consented donations into training datasets for the scopes the donor granted.

    DIYO_CONSENT_SALT=... python3 pipeline/build.py --input donations --output data/voice-commons/v1

Input layout:
    donations/<contributor>/
        consent.json     {record_version, granted_at, scopes, purpose, audio_license, identifier}
        takes.jsonl      {"take_id","audio","prompt_text","transcript"}
        *.wav

Output:
    <output>/listen.jsonl   scopes.listen  → ASR training
    <output>/speak.jsonl    scopes.speak   → multi-speaker TTS
    <output>/style.jsonl    scopes.style   → prosody/emotion, aggregate only
    <output>/manifest.json  provenance, rejects, counts, hashes

Nothing is written for a scope the donor did not tick. Nothing is written for a withdrawn donor.
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import consent  # noqa: E402
import qc  # noqa: E402


def load_env_salt():
    salt = os.environ.get("DIYO_CONSENT_SALT")
    if salt:
        return salt
    env = Path(__file__).resolve().parents[1] / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("DIYO_CONSENT_SALT="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def read_jsonl(path):
    if not Path(path).exists():
        return []
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="donations directory")
    ap.add_argument("--output", required=True)
    ap.add_argument("--withdrawals", default="data/voice-commons/withdrawals.jsonl")
    ap.add_argument("--copy-audio", action="store_true")
    args = ap.parse_args()

    salt = load_env_salt()
    if not salt:
        sys.exit("DIYO_CONSENT_SALT is required — an unsalted hash of a phone number is not anonymous")

    root = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    withdrawn = consent.withdrawn_set(args.withdrawals)

    rows = {s: [] for s in consent.SCOPES}
    rejects = {}
    contributors, seen_text, seen_fp = [], [], set()

    def reject(reason):
        key = reason.split(":")[0]
        rejects[key] = rejects.get(key, 0) + 1

    for contributor_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        cpath = contributor_dir / "consent.json"
        if not cpath.exists():
            reject("missing_consent")
            continue
        record = json.loads(cpath.read_text(encoding="utf-8"))
        bad = consent.problems(record)
        if bad:
            for b in bad:
                reject(f"consent_{b.split(':')[0]}")
            continue

        cid = consent.contributor_id(record.get("identifier", contributor_dir.name), salt)
        if cid in withdrawn:
            reject("withdrawn")
            continue
        scopes = consent.allowed_scopes(record)
        contributors.append({"id": cid, "scopes": sorted(scopes)})

        for take in read_jsonl(contributor_dir / "takes.jsonl"):
            audio = contributor_dir / take["audio"]
            ok, metrics, reasons = qc.qc_audio(audio)
            if not ok:
                for r in reasons:
                    reject(r)
                continue

            fp = qc.audio_fingerprint(audio)
            if fp in seen_fp:
                reject("duplicate_audio")
                continue

            transcript = consent.redact(take.get("transcript") or take.get("prompt_text", ""))
            prompt_text = consent.redact(take.get("prompt_text", ""))
            score = qc.readback_score(transcript, prompt_text)
            if score < qc.MIN_READBACK:
                reject(f"readback:{score:.2f}")
                continue
            if qc.near_duplicate(transcript, seen_text):
                reject("duplicate_text")
                continue

            seen_fp.add(fp)
            seen_text.append(qc.shingles(transcript))

            base = {
                "id": f"{cid[:11]}-{take['take_id']}",
                "audio": str(audio.relative_to(root)),
                "audio_sha256": fp,
                "prompt_text": prompt_text,
                "transcript": transcript,
                "readback": round(score, 3),
                "qc": metrics,
                "consent_version": record.get("record_version"),
            }
            for scope in scopes:
                rows[scope].append(dict(base, scope=scope))

    counts = {}
    for scope, items in rows.items():
        path = out_dir / f"{scope}.jsonl"
        path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in items) + "\n", encoding="utf-8")
        counts[scope] = {
            "rows": len(items),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()[:16] if items else None,
        }

    manifest = {
        "name": out_dir.name,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "audio_copied": bool(args.copy_audio),
        "contributors": len(contributors),
        "withdrawn_contributors_excluded": len(withdrawn),
        "scopes": counts,
        "rejected": dict(sorted(rejects.items(), key=lambda kv: -kv[1])),
        "rejected_total": sum(rejects.values()),
        "consent": {"record_version": consent.CURRENT_VERSION,
                    "salt_fingerprint": hashlib.sha256(salt.encode()).hexdigest()[:8]},
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    print(json.dumps(manifest, ensure_ascii=False, indent=1))
    if sum(c["rows"] for c in counts.values()) == 0:
        sys.exit("no rows produced — check rejects above")


if __name__ == "__main__":
    main()
