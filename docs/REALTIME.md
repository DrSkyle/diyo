# Real-time conversation (not voice-to-text)

A person should be able to talk *with* Diyo, interrupt it, and hear it think — the way GPT-4o
Advanced Voice and Gemini Live feel. Not: speak, wait, read, listen.

## Where the latency actually comes from

A naive cascade is VAD → ASR → LLM → TTS, each one waiting for the previous to finish:

| Naive cascade | Time |
|---|---|
| wait for silence | 500–800ms |
| transcribe the whole utterance | 400–1200ms |
| generate the whole answer | 800–3000ms |
| synthesise the whole answer | 500–2000ms |
| **Total to first sound** | **2.2–7s** |

That is why pipelines "cannot emulate the experience of real conversations" (Moshi paper). But
most of that delay is **self-inflicted waiting**, not compute. Three fixes, in order of impact:

### 1. Overlap everything (the big one)

- **Stream the ASR** on 320ms chunks while the person is still talking.
- **Speculate**: once the partial transcript is stable for ~250ms, start the LLM on it. If the
  final transcript differs, cancel and regenerate. On short Nepali questions this hits >80% of the
  time.
- **Stream the TTS by clause**: synthesise at the first `।`, not at the last.

Result: first sound at ~700–900ms with the *same* models. No new training.

### 2. Turn-taking, not silence detection

Silence detection cannot tell "finished" from "thinking". A small **turn-policy model** decides
speak / wait / ask, from features the phone already has: trailing silence length, pitch contour
(falling = done), whether the last word is a filler ("अनि…", "मतलब…"), speech rate, and the
partial transcript.

**This is the model Adaption should train** — it is text + features, it is small, and it is the
difference between "a robot that talks" and "a conversation". Nobody has a Nepali one.

### 3. A real-time-feeling loop

| Stage | Budget | Implementation |
|---|---|---|
| VAD frame | 20ms | Silero VAD (or sherpa-onnx VAD) |
| Trailing silence before "done" | 180–250ms | tuned to Nepali pauses; shorter if pitch falls |
| ASR partial | every 320ms | Whisper-small / Moonshine-v2 streaming, int8 |
| LLM first clause | 400ms | Qwen3.5-2B, prompt capped, stop at `।` |
| TTS first audio | 250ms | Clause-streamed Piper / Phonon |
| **First sound** | **~900ms** | |
| Barge-in cut | **< 120ms** | VAD + AEC, hard stop |

## The state machine (this is the product)

```
IDLE ──tap/hotword──► LISTENING ──speech──► LISTENING(partial)
                          │                      │
                          │            turn-policy: DONE
                          ▼                      ▼
                      (no speech)            THINKING ──first clause──► SPEAKING
                          │                      │                          │
                          └──timeout──► IDLE     └──user speaks──► INTERRUPTED
                                                                           │
                                                        SPEAKING + LISTENING (full duplex)
```

Rules that make it feel human:

- **Barge-in is instant.** Any detected speech stops playback in <120ms. Never talk over a person.
- **Echo cancellation is mandatory.** Without AEC the mic hears Diyo's own voice and it
  interrupts itself forever. Use `AcousticEchoCanceler` + `NoiseSuppressor`, and gate the mic
  during playback on devices where AEC is weak.
- **Backchannel.** A soft "हँ" at ~700ms of thinking. Silence reads as broken; a filler reads as
  listening.
- **Overlap is allowed.** Diyo may start speaking while the user finishes a trailing clause — that
  is what real conversation does.
- **One question at a time**, still. Full duplex does not mean rambling.
- **Show the transcript** as it forms, so a mishear is visible before the answer.

## On-device speech-to-speech: the honest 2026 state

| Option | Reality on a ₹6,000 phone |
|---|---|
| **Moshi (Kyutai)** — open full-duplex S2S, Mimi codec, sub-200ms | Reference architecture. ~7B; not a 3GB phone in v1. |
| **Qwen-Audio-3.1-Realtime** — think/act/speak/coordinate | Server-class. Use as a benchmark, not a payload. |
| **Phonon (Gradium)** — open on-device TTS | Very promising for the mouth; evaluate against Piper. |
| **Streaming cascade** (Moonshine-v2 / Whisper-small + Qwen3.5-2B + Piper) | **Ships today. ~900ms. This is v1.** |

So v1 is a *duplex cascade*, and the architecture is written so the speech stack can be swapped for
a single S2S model when one fits. The conversation controller — barge-in, overlap, turn policy —
is the part that stays, and it is the part users actually feel.

## What we measure (add to `docs/QUALITY.md`)

| Metric | Target |
|---|---|
| First sound after the person stops | < 1.2s |
| Barge-in cut latency | < 150ms |
| False barge-ins (Diyo interrupting itself) | 0 per 50 turns |
| Turn-end detection accuracy | > 95% on 100 real recordings |
| Talk-over time per 10 turns | < 1.5s |
| End-to-end, 5-minute conversation | no drift, no repeated question |

## Sources

- [Moshi: a speech-text foundation model for real-time dialogue (arXiv 2410.00037)](https://arxiv.org/abs/2410.00037) · [kyutai-labs/moshi](https://github.com/kyutai-labs/moshi)
- [Qwen-Audio-3.1-Realtime (arXiv 2609.25176)](https://arxiv.org/abs/2609.25176)
- [Gradium releases Phonon, open-source on-device TTS](https://gradium.ai/blog/gradium-releases-phonon)
- [The 2026 edge speech stack](https://blog.mickeyzzc.tech/en/posts/aihelper/on-device-voice-stack/)
