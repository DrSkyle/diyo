# Diyo — locked decisions

Each decision is reversible only with a reason. If we change one, we write the reason here.

---

## D1. Base model: a 2–4B multilingual instruct model, QLoRA-finetuned, not trained from scratch

**Chosen:** start from a strong small multilingual instruct model (Gemma-3-class or
Qwen-3-class, 2–4B) and QLoRA-finetune it on Nepali.

**Why:** training a base model from scratch is a research lab, not a product. The moat is
not the weights — it is the Nepali data, the refusal behaviour, and the offline corpus.
A 4B model at 4-bit is ~2.2GB, which fits the target phone. A 7B+ model is correct and
unshippable: 2–4 tok/s turns a 1.5s answer into 12s.

**Rejected:** 7B+ (too slow on target hardware), 1B (too weak at Devanagari reasoning and
refusal), from-scratch pretraining (no).

**Open:** Gemma vs Qwen is decided by the eval set, not by vibes. Run both, keep the winner.

---

## D2. Runtime: llama.cpp via JNI, GGUF 4-bit

**Chosen:** llama.cpp, arm64 build, Q4_K_M (or IQ4_XS if quality holds), Kotlin/JNI wrapper.

**Why:** best-in-class ARM CPU performance, GGUF is the lingua franca of quantised models,
and we can test the exact same file on a laptop (`llama-cli`) and on the phone. Notes:
`llama.cpp` performance work is not something we can outsource.

**Rejected:** MLC-LLM (excellent on GPUs, heavier toolchain and APK), MediaPipe LLM
Inference (Google's models only), ExecuTorch (immature dev loop), ONNX GenAI (fine, but
GGUF tooling is faster to iterate).

---

## D3. ASR: Whisper-small, finetuned on Nepali, exported to ONNX / ggml

**Chosen:** Whisper-small baseline; measure WER on Nepali before anything else. If it is
bad (expect it to be), fine-tune on Nepali read+spontaneous speech, then quantise.

**Why:** Whisper-small is ~480MB in fp16 and ~150MB at 4-bit, fast enough for streaming
chunks on a mid phone, and it handles code-switched Nepali-English poorly but not
catastrophically. Fine-tuning is cheap compared to the alternative of building an ASR
stack.

**Data:** ai4bharat Kathbath is 1,684h but is **Indian languages, not Nepali** — do not
count it as Nepali training data. Nepali sources to assemble: Mozilla Common Voice (ne),
OpenSLR Nepali corpora, and we record our own. Native review is mandatory.

**Rejected:** cloud ASR (defeats the product), Vosk (no strong Nepali model today).

---

## D4. TTS: Piper, one trained Nepali voice, < 80MB

**Chosen:** Piper (VITS). Fast enough for realtime on ARM, tiny, runnable offline.

**Why:** the answer must be *spoken* — a large share of users read Devanagari slowly or not
at all. A single clear voice is enough for v0. Train on the reviewed Nepali speech we
collect for ASR (same corpus, two uses).

**Rejected:** cloud TTS, large neural TTS (latency, size), system TTS (no Nepali voice on
most cheap Androids — verify per device before assuming).

---

## D5. "Seeing" in v0 = Devanagari OCR, not a vision-language model

**Chosen:** on-device OCR (ML Kit Devanagari or Tesseract) feeding the local text model.
Scene description ("what is this photo?") is **online only** in v0.

**Why:** A VLM on a 3GB phone is 3GB+ and seconds-per-token. But OCR is cheap, instant, and
solves the actual Nepali problem: **medicine labels, government forms, bank slips, notices,
exam results**. That is what "seeing" is worth here. Ship the useful half now.

**Rejected:** on-device VLM (too heavy for v0), sending photos to the cloud silently (breaks
principle 3).

---

## D6. Search: online only, explicit, through our own proxy

**Chosen:** a Cloudflare Worker proxy to a search API (Tavily / Brave / self-hosted
SearXNG). The local model summarises results in Nepali. The UI shows a clear "अनलाइन" chip
while it happens.

**Why:** never ship API keys in an APK; a proxy lets us rate-limit, cache, and swap
providers. Search is the one feature that must be *visibly* online.

**Rejected:** in-app API key (leaks in minutes), silent background search (betrays the
product), offline-only (users will ask about weather and bus schedules).

---

## D7. The offline corpus is curated, cited, and small

**Chosen:** ~200–400MB of reviewed Nepali content in five domains — स्वास्थ्य, कृषि,
सरकारी कागजात, कानूनी अधिकार, दैनिक जीवन — stored as chunked text with source URLs and
a "last verified" date, retrieved into the prompt.

**Why:** a small model with good retrieval beats a big model with none, and citations are
what make a health answer defensible. Every chunk names its source; every answer can say
where it came from.

**Rule:** no chunk ships without a named reviewer (clinician, agronomist, lawyer, or
government-office staffer) and a date.

---

## D8. Privacy is enforced by a test, not a promise

**Chosen:** the test suite fails if a network call appears outside `net/search/`. No
analytics SDK. No crash reporting that uploads. Local logs only, wiped from settings.

**Why:** this is the Soteria discipline, and it is the reason a health worker in a remote
post will trust the app with a child's symptoms. A privacy claim you cannot test is
marketing.

---

## D9. Device floor: Android 9, 3GB RAM, arm64

**Chosen:** support Android 9+ on arm64 with dotprod. Refuse to run (with a clear message)
below 3GB RAM rather than crawl.

**Why:** the phones we are targeting are 2019–2023 entry-level Androids. Pretending a 2GB
phone can run this produces a bad first impression that kills word of mouth. Better to say
"this phone needs a little more room."

## D10. Build on CI, not on this box

**Chosen:** GitHub Actions builds the APK (Java + Android SDK + NDK). This machine has no
JDK, no SDK, 5.5GB free and no GPU — it does data, evals and model work only.

**Why:** reproducibility, and we do not want the build to depend on one laptop's state.

---

## D11. Diyo-1 is our fine-tune of the open Nepali base, and we say so

**Chosen:** base is `himalaya-ai/himalaya-gemma-4-e2b-it` (Apache-2.0, Himalaya AI Labs). Our SFT
on top is **Diyo-1**, and Diyo-1 is entirely ours: our name, our checkpoint, our dataset, our
eval. The NOTICE file ships in the APK's About screen and in the repo.

**Why:** the fine-tune is the work and the moat. The base is public and fingerprinted — GGUF
metadata and tensor hashes make a from-scratch claim instantly falsifiable, and the injured party
would be a Nepali non-profit. Crediting the base costs one line and buys credibility, community
and press that a false claim cannot.

**What is ours:** Diyo-1 weights, the behaviour dataset, the 30-case eval, the offline corpus, the
voice stack, the app. **What is not:** the base weights. See `docs/LICENSING.md`.

---

## D12. Voice surfaces: keyboard first, assistant role second, bubble third

**Chosen:** ship an `InputMethodService` keyboard (mic + type into every app), then claim
`ROLE_ASSISTANT` for the system gesture, then an opt-in `SYSTEM_ALERT_WINDOW` orb.

**Why:** the keyboard is the only mechanism that puts Diyo inside every text field with no policy
risk. The assistant role gives the system invocation without an overlay hack. AccessibilityService
is rejected for non-accessibility uses, so it stays out of v1.

**Rejected:** overlay-first (review risk, feels spammy), always-listening ambient mic (Android 14+
restricts it, and it is creepy), screen scraping (policy).

**Voice quality:** single-speaker Piper fine-tuned from the best voice in
`ampixa/nepali-voices-v0`, numbers expanded before synthesis, clause-streamed TTS, barge-in. See
`app/VOICE.md`.

---

## D13. Real-time means duplex cascade + a trained turn policy, not a 7B speech model

**Chosen:** v1 is a streaming cascade — 320ms ASR chunks, speculative LLM start on a stable partial,
clause-streamed TTS, hard barge-in with AEC — plus a small **turn-policy model** trained with
Adaption that decides speak / wait / ask. Target first sound ~900ms.

**Why:** the 2–7s of a naive pipeline is mostly self-inflicted waiting, not compute. Overlap and a
turn policy recover most of the "real conversation" feel with models that fit a 3GB phone. Moshi
(open, full-duplex, sub-200ms) is the reference architecture but is ~7B — it becomes viable later,
and the controller we build now survives the swap.

**Rejected:** waiting for a single on-device S2S model (ships nothing this year); server realtime API
(breaks the offline promise); chasing sub-200ms on hardware that cannot hold the model.

See `docs/REALTIME.md`.

---

## D14. Voices are donated with a consent record, never collected

**Chosen:** **Diyo Voice Commons** — an open Nepali speech corpus with per-contributor consent
records, three scopes (listen / speak / style), in-app withdrawal and deletion receipts, Nepal-hosted.

**Why:** voice is personal data; 2026 practice requires a consent record tying a voice asset to an
authorization. Scraping would end the "made in Nepal, trusted by Nepal" story instantly. And a
500–1,000 hour consented Nepali corpus with provenance is a decade-long asset nobody else has — a
stronger moat than the model itself.

**Hard rules:** no scraping; no cloning of a named individual, including the contributor; no sale of
raw audio; no use outside the declared scope; synthetic audio is marked.

See `docs/VOICE-COMMONS.md`.
