# Diyo Android app

Built on CI, not on the dev box (no JDK / SDK / NDK there). Everything here is designed so
that `git push` produces an APK.

## Module layout

```
app/
├── app/                    Kotlin UI (single screen, voice-first)
│   ├── MainActivity.kt     one screen: mic, text, camera, answer
│   ├── Asr.kt              streaming Whisper (ONNX Runtime Mobile)
│   ├── Tts.kt              Piper (native)
│   ├── Ocr.kt              ML Kit Devanagari
│   ├── Llm.kt              JNI bridge to llama.cpp
│   └── NetSearch.kt        the ONLY module allowed to touch the network
├── native/
│   └── llamajni/           CMake + llama.cpp, arm64-v8a only for v0
└── packs/                  model pack downloader (resumable, Wi-Fi only)
```

`NetSearch.kt` being a single module is not style — a test greps the source tree and fails
the build if `java.net`, `okhttp`, `HttpURLConnection` or `URL(` appears anywhere else.

## Build stages

| Stage | Deliverable | Gate |
|---|---|---|
| 0 | Kotlin shell, no model, fake answers | builds on CI |
| 1 | llama.cpp JNI, load GGUF, text in/out | 1.5s for a 40-token answer on a 3GB phone |
| 2 | Whisper ASR streaming | WER on 50 Nepali clips recorded by us |
| 3 | Piper TTS | answer is audible in under 4s total |
| 4 | OCR → model | reads a real medicine label correctly |
| 5 | NetSearch | visibly online, works with no key in the APK |

## Model pack

Not in the APK. ~50MB APK + a ~1.8GB pack downloaded once over Wi-Fi.

```
packs/diyo-np-v0/
├── model.gguf          4-bit, ~2.2GB
├── whisper-small.bin   ~150MB int8
├── piper-np.onnx       ~70MB
├── corpus.sqlite       200–400MB, chunked + source_url + verified_on
└── manifest.json       sha256, version, min_app_version, min_ram_mb
```

## Refusal to run

Below 3GB RAM or without dotprod: show a clear Nepali screen explaining the phone is too
small, and offer the reduced pack. Do not silently crawl.

## CI (`.github/workflows/android.yml`)

- JDK 17, Android SDK 35, NDK r27
- `./gradlew assembleDebug` on every push
- upload APK artifact
- run `evals/run_eval.py` against the chosen GGUF on a Linux runner (llama.cpp server) —
  so a model regression fails the build before it reaches a phone

## Unblocked when

- A GitHub repo exists for the app
- A base model is chosen by eval score
- We have 50 self-recorded Nepali clips for the ASR baseline
