# Voice packs (ship now, consented collection later)

Scraped voices are out. Prebuilt, openly-licensed Nepali voices are in.

## Speaking (TTS) — Piper, on-device
- **Voice:** a single-speaker Nepali Piper `.onnx` + `.onnx.json` config (e.g. from an openly
  licensed pack such as `ampixa/nepali-voices-v0` or a Piper-trained `ne_NP` voice once validated).
- **Runtime:** Piper's C API / `piper-phonemize`, or sherpa-onnx TTS, bundled as a `.so` in the
  model pack. No network, ~15–30 MB for voice + runtime.
- **Fallback:** Android `TextToSpeech` (ne-NP where present) — already wired in `Speak.kt`.

## Listening (ASR) — sherpa-onnx, streaming
- **Model:** `sherpa-onnx-streaming-zipformer-ne` / Whisper-small-ne int8, whichever fits 3GB
  phones after measurement. Streaming partials every ~320 ms feed the turn policy (docs/REALTIME.md).
- **Runtime:** `sherpa-onnx` Android AAR + JNI. Mic audio stays on device; transcripts only.

## Pack layout (under `filesDir/models/`)
```
models/
  base.gguf              # Qwen3.5-2B class, ~1.2GB (downloaded once)
  diyo-lora.gguf         # best adapter, ~85MB (swappable)
  asr/                   # sherpa-onnx streaming model + tokens
  tts/voice.onnx         # Piper voice
  tts/voice.onnx.json
  corpus.jsonl           # 3,253 grounded chunks
```
`Pack.find`/`Brains.pick` already select the grounded brain until a base GGUF is present; native
libs load lazily so the APK runs without them.

## After beta, with consent
`VoiceCommons.kt` records per-item receipts (scope A/B/C, revocable, local-first). Uploads go only
to a Nepal-hosted endpoint, only for items the user explicitly donates, never scraped audio.
