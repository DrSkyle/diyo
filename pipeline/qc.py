#!/usr/bin/env python3
"""Quality control for donated Nepali speech.

Rejects a take before it reaches a dataset. Stdlib only; the energy VAD is a stand-in for Silero
VAD in production, and says so.
"""

import difflib
import hashlib
import math
import struct
import wave
from pathlib import Path

FRAME_MS = 20
MIN_SR = 16000
MIN_DUR, MAX_DUR = 1.2, 15.0
MAX_CLIP_RATIO = 0.005
MIN_SNR_DB = 20.0
MIN_VOICED_RATIO = 0.25
MIN_READBACK = 0.80


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        ch = w.getnchannels()
        width = w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise ValueError(f"expected 16-bit PCM, got {width * 8}-bit")
    count = len(raw) // 2
    samples = list(struct.unpack(f"<{count}h", raw[:count * 2]))
    if ch > 1:
        samples = samples[::ch]
    return sr, samples


def frames(samples, sr, ms=FRAME_MS):
    size = max(1, int(sr * ms / 1000))
    return [samples[i:i + size] for i in range(0, len(samples), size) if samples[i:i + size]]


def rms(chunk):
    if not chunk:
        return 0.0
    return math.sqrt(sum(s * s for s in chunk) / len(chunk))


def qc_audio(path):
    """Return (ok, metrics, reasons)."""
    reasons, metrics = [], {}
    try:
        sr, samples = read_wav(path)
    except Exception as exc:  # noqa: BLE001 - any decode failure is a rejection
        return False, {}, [f"decode:{type(exc).__name__}"]

    dur = len(samples) / sr
    metrics.update(sample_rate=sr, duration_s=round(dur, 2))
    if sr < MIN_SR:
        reasons.append(f"sample_rate:{sr}<{MIN_SR}")
    if not MIN_DUR <= dur <= MAX_DUR:
        reasons.append(f"duration:{dur:.1f}s outside {MIN_DUR}-{MAX_DUR}")

    clip = sum(1 for s in samples if abs(s) >= 32767 * 0.999)
    clip_ratio = clip / max(len(samples), 1)
    metrics["clip_ratio"] = round(clip_ratio, 5)
    if clip_ratio > MAX_CLIP_RATIO:
        reasons.append(f"clipping:{clip_ratio:.2%}")

    fr = frames(samples, sr)
    levels = [rms(f) for f in fr]
    if not levels or max(levels) < 120:
        return False, metrics, reasons + ["no_speech"]

    overall = sum(levels) / len(levels)
    thr = max(overall * 0.25, 200)
    speech = [l for l in levels if l >= thr]
    quiet = [l for l in levels if l < thr]
    voiced_ratio = len(speech) / len(levels)
    noise = sum(quiet) / len(quiet) if quiet else 1.0
    speech_rms = sum(speech) / len(speech) if speech else 0.0
    snr = 20 * math.log10(speech_rms / max(noise, 1.0)) if speech_rms > 0 else 0.0

    metrics.update(snr_db=round(snr, 1), voiced_ratio=round(voiced_ratio, 2),
                   peak=max(abs(s) for s in samples))
    if voiced_ratio < MIN_VOICED_RATIO:
        reasons.append("no_speech")
    elif snr < MIN_SNR_DB:
        reasons.append(f"snr:{snr:.1f}dB<{MIN_SNR_DB}")

    return not reasons, metrics, reasons


def normalize(text):
    for zw in ("\u200b", "\u200c", "\u200d", "\ufeff", "\u00a0"):
        text = text.replace(zw, "")
    text = text.translate(str.maketrans("०१२३४५६७८९", "0123456789"))
    drop = "।?!,.;:\"'()[]{}–—…/\\|"
    text = "".join(" " if c in drop else c for c in text)
    return " ".join(text.split()).lower()


def readback_score(transcript, prompt_text):
    """Did the speaker actually read the line? Cheap stand-in for forced alignment."""
    a, b = normalize(transcript), normalize(prompt_text)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def shingles(text, k=5):
    t = normalize(text)
    return {t[i:i + k] for i in range(max(0, len(t) - k + 1))}


def near_duplicate(text, seen, threshold=0.8):
    """True if this text overlaps an existing take enough to be a re-record of the same line."""
    s = shingles(text)
    for other in seen:
        inter = len(s & other)
        if inter and inter / len(s | other) >= threshold:
            return True
    return False


def audio_fingerprint(path):
    """Detects byte-identical and re-encoded copies of the same take."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
