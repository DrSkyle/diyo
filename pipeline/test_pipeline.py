#!/usr/bin/env python3
"""End-to-end test for the donation pipeline. No dependencies, no network.

    python3 pipeline/test_pipeline.py

Builds a fake donation tree (good takes, clipped take, silent take, a duplicate, a withdrawn
donor, and a transcript containing a phone number), runs build.py, and asserts the guarantees
that matter: scopes are honoured, junk is rejected, PII is redacted, withdrawals are excluded.
"""

import json
import math
import os
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SALT = "test-salt-not-a-secret"
FAILS = []


def check(label, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + label + (f"  {detail}" if detail and not cond else ""))
    if not cond:
        FAILS.append(label)


def write_wav(path, seconds, freq, amplitude, noise=0, sr=16000):
    n = int(seconds * sr)
    frames = bytearray()
    for i in range(n):
        v = amplitude * math.sin(2 * math.pi * freq * i / sr)
        if noise:
            v += noise * math.sin(2 * math.pi * 3100 * i / sr)
        frames += struct.pack("<h", max(-32768, min(32767, int(v))))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(bytes(frames))


def donor(root, name, scopes, takes, identifier):
    d = root / name
    d.mkdir(parents=True)
    (d / "consent.json").write_text(json.dumps({
        "record_version": 1,
        "granted_at": "2026-11-17T09:41:00+05:45",
        "scopes": scopes,
        "purpose": "training Nepali speech models for Diyo",
        "audio_license": "Diyo Voice Commons 1.0",
        "identifier": identifier,
    }, ensure_ascii=False), encoding="utf-8")
    (d / "takes.jsonl").write_text(
        "\n".join(json.dumps(t, ensure_ascii=False) for t in takes) + "\n", encoding="utf-8")
    for t in takes:
        write_wav(d / t["audio"], **t["_wav"])


def main():
    tmp = Path(tempfile.mkdtemp(prefix="diyo-test-"))
    donations, out = tmp / "donations", tmp / "out"
    withdrawals = tmp / "withdrawals.jsonl"

    good = "मेरो बच्चालाई तीन दिनदेखि ज्वरो आएको छ।"
    other = "धानको पात पहेँलो हुँदै गएको छ।"
    pii = "मेरो नम्बर 9841234567 हो, सम्पर्क गर्नुहोस्।"

    donor(donations, "c1", {"listen": True, "speak": True, "style": False}, [
        {"take_id": "t1", "audio": "good.wav", "prompt_text": good,
         "_wav": dict(seconds=1.6, freq=180, amplitude=9000, noise=200)},
        {"take_id": "t2", "audio": "clipped.wav", "prompt_text": other,
         "_wav": dict(seconds=1.6, freq=300, amplitude=32767)},
        {"take_id": "t3", "audio": "silent.wav", "prompt_text": other,
         "_wav": dict(seconds=1.6, freq=300, amplitude=0)},
        {"take_id": "t4", "audio": "pii.wav", "prompt_text": pii,
         "_wav": dict(seconds=1.6, freq=220, amplitude=8000, noise=150)},
        {"take_id": "t5", "audio": "dup.wav", "prompt_text": good,
         "_wav": dict(seconds=1.6, freq=190, amplitude=8800, noise=180)},
    ], "phone:+9779812345678")

    donor(donations, "c2", {"listen": True, "speak": False, "style": False}, [
        {"take_id": "u1", "audio": "good.wav", "prompt_text": other,
         "_wav": dict(seconds=1.6, freq=250, amplitude=8500, noise=250)},
    ], "phone:+9779800000001")

    donor(donations, "c3", {"listen": True, "speak": True, "style": False}, [
        {"take_id": "w1", "audio": "good.wav", "prompt_text": good,
         "_wav": dict(seconds=1.6, freq=200, amplitude=9000, noise=200)},
    ], "phone:+9779800000002")

    sys.path.insert(0, str(ROOT / "pipeline"))
    import consent  # noqa: E402
    c3_id = consent.contributor_id("phone:+9779800000002", SALT)
    withdrawals.write_text(json.dumps({"contributor": c3_id, "withdrawn_at": "2026-11-17"}) + "\n",
                           encoding="utf-8")

    env = dict(os.environ, DIYO_CONSENT_SALT=SALT)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "pipeline" / "build.py"),
         "--input", str(donations), "--output", str(out), "--withdrawals", str(withdrawals)],
        capture_output=True, text=True, env=env)

    print("build.py exit:", proc.returncode)
    if proc.returncode != 0:
        print(proc.stdout[-2000:], proc.stderr[-2000:])
        sys.exit("build failed")

    def rows(scope):
        p = out / f"{scope}.jsonl"
        return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

    listen, speak, style = rows("listen"), rows("speak"), rows("style")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    rejects = manifest["rejected"]

    print("\nresults:")
    check("listen rows == 3 (c1 good, c1 pii, c2 good)", len(listen) == 3, f"got {len(listen)}")
    check("speak rows == 2 (only the donor who granted speak)", len(speak) == 2, f"got {len(speak)}")
    check("style rows == 0 (nobody granted style)", len(style) == 0, f"got {len(style)}")
    check("withdrawn donor excluded", rejects.get("withdrawn", 0) == 1, f"rejects={rejects}")
    check("clipped audio rejected", rejects.get("clipping", 0) == 1, f"rejects={rejects}")
    check("silent audio rejected", rejects.get("no_speech", 0) == 1, f"rejects={rejects}")
    check("duplicate text rejected", rejects.get("duplicate_text", 0) >= 1, f"rejects={rejects}")

    pii_row = next((r for r in listen if "फोन" in r["transcript"]), None)
    check("phone number redacted", pii_row is not None)
    check("no raw phone number survives",
          not any("9841234567" in r["transcript"] for r in listen))
    check("contributor ids are hashes", all(r["id"].startswith("vc_") for r in listen))
    check("audio hash recorded", all(len(r["audio_sha256"]) == 64 for r in listen))
    check("manifest has salt fingerprint", "salt_fingerprint" in manifest["consent"])
    check("scope recorded per row", {r["scope"] for r in listen} == {"listen"})

    print(f"\n{'FAILED: ' + ', '.join(FAILS) if FAILS else 'all checks passed'}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
