# Diyo voice: ears + understanding

Nobody types into Diyo. That is the constraint that shapes everything else.

## What Adaption can and cannot do

| | Adaption | Reality |
|---|---|---|
| Train an acoustic model (ASR) | **No** | No audio in the API. SFT/DPO on text only. |
| Train the understanding model | **Yes** | `Qwen3.5-2B / 4B / 9B, 35B-A3B, 122B` via AutoScientist |
| Generate correction + intent data | **Yes** | `datasets.invent` + our deterministic noise model |

So voice is two models, and only the second one is Adaption's:

```
        ┌──────────────────────────────────────────────────────────┐
mic ──► │ 1. EARS   Zipformer / Whisper-small, int8, sherpa-onnx    │
        │    ~40–150MB · streaming · VAD · on-device                 │
        └───────────────────────┬──────────────────────────────────┘
                                │ raw Nepali transcript (wrong words, no punctuation,
                                │ Devanagari digits missing, code-switched)
        ┌───────────────────────▼──────────────────────────────────┐
        │ 2. UNDERSTANDING   Qwen3.5-2B, Adaption-trained            │
        │    fixes the transcript, extracts intent, decides          │
        │    triage vs answer, writes the 25–40 token spoken reply   │
        └───────────────────────┬──────────────────────────────────┘
                                │
        ┌───────────────────────▼──────────────────────────────────┐
        │ 3. MOUTH   Piper Nepali, sherpa-onnx                       │
        └──────────────────────────────────────────────────────────┘
```

**The insight:** ASR will always mangle Nepali numbers, drug names and place names. A 2B model
handed the raw transcript *plus* the offline corpus can fix most of it, and — unlike a bigger
acoustic model — it fits on a ₹6,000 phone. The second model is the product; the first is a
commodity.

## Why the ears must be small

A phone answers in under 1.5s. ASR must therefore stream and finish fast. Whisper-large is a
server model; on the phone it is a battery drain and a 1s+ wait before the brain even starts.
Target: **Zipformer transducer or Whisper-small, int8, <150MB, <400ms after end of speech.**

Training the ears needs a GPU and a speech stack — not Adaption:

- Fine-tune Whisper-small on **OpenSLR SLR54** + **Common Voice `ne` 27.0** + our 50 recorded clips
- Or train an icefall Zipformer with the same data (smaller, streaming, better for the phone)
- Export to ONNX int8 → `sherpa-onnx` Android (ASR + VAD + Piper in one dependency)
- Evaluate with `asr/wer.py` on held-out speakers, not held-out utterances

## What the understanding model is trained on

Not "Nepali instructions" — that exists (`himalaya-ai/nepali-sft-suite`). It is trained on the
one thing nobody has: **noisy Nepali speech transcripts → correct action.**

| Pair type | Input (noisy) | Output (clean) |
|---|---|---|
| correction | `मेरो छोरा लाई तीन दिन देखि जोरो आयो` | `मेरो छोरालाई तीन दिनदेखि ज्वरो आएको छ।` |
| intent + action | `बच्चा लाई जोरो तीन दिन खाना खा न` | triage question + referral answer |
| number rescue | `बीस केजी चामल पन्ध्र सय` | confirm `२० केजी, १५०० रुपैयाँ` |
| refusal | `औषधि कति खाने भन न` | `मलाई थाहा छैन … डाक्टरलाई सोध्नुहोस्।` |
| code-switch | `मेरो फोन मा रिचार्ज गर्न कसरी` | answer in Nepali |

`asr/noise.py` generates the noisy side deterministically from real Nepali text, so the data is
reproducible and auditable. Every pair carries the clean original, so a native reviewer only has
to check that the garbled version is plausible.

Adaption then runs `AutoScientist` on `Qwen3.5-2B` with `training_method="instruction"`, and a
second run with `alignment` if we build preference pairs (good reply vs over-refusing reply).

## Voice-first interaction rules (v0)

1. **Confirm anything numeric before acting.** "तपाईंले २० केजी भन्नुभयो, हो?" Numbers are where
   ASR dies and where doses come from.
2. **Speak 25–40 tokens.** The answer is heard, not read; TTS latency is part of the product.
3. **One question at a time.** Never a list.
4. **Never say a number the model did not hear.** If the user did not say a dose, Diyo does not
   either.
5. **Barge-in.** Speech stops the moment the user speaks.
6. **Repeat by default.** "फेरि भन्नुहोस्" must work without a second tap.
7. **Say what it heard when it is unsure.** "मैले ठीक सुनिनँ" is better than a confident guess.

## Metrics that matter

| Metric | Target | Where |
|---|---|---|
| WER, clean speech | < 15% | `asr/wer.py` |
| WER, code-switched | < 25% | `asr/wer.py` |
| **Entity WER** (numbers, doses, place names) | < 10% | `asr/wer.py --entity` |
| End-to-end, speech end → speech start | < 1.5s | device |
| ASR size | < 150MB | APK |
| Correction model | Qwen3.5-2B Q4 ~1.5GB | pack |

**Entity WER is the one to obsess over.** A 12% overall WER with 30% entity WER is a product that
tells a mother the wrong dose.
