# Diyo: open-source stack survey

Searched every layer. The headline: **Nepal already has an open stack, and it is better than
what we were about to build.** Our job is not to reproduce it — it is to add the one thing it
does not have: safe, short, referral-first behaviour for people with no signal.

---

## The Nepali open-source landscape

| Org | What they ship | Licence |
|---|---|---|
| **Himalaya AI Labs** (non-profit, NP) | Gemma 4 E2B full-SFT (Nepali+English) + GGUF, HimalayaGPT 0.5B, Nepali BPE tokenizers (64k/100k/128k), Whisper large-v3-turbo, Indic-Parler TTS Nepali, GLM-OCR Devanagari, **`nepali-sft-suite` (546k rows)**, `nepalpixel-vlm-bench` | Apache-2.0 / mixed-per-row |
| **SAGEA** (Bhaktapur) | ARVA multilingual OCR (Nepali), Mira typed-decision model with "first-class Nepali coverage", Helios KYC | mixed |
| **AI4Bharat** (IIT Madras) | IndicWhisper (22 scheduled languages incl. Nepali), Indic-TTS, IndicTrans2, Vistaar benchmarks | open |
| **Community** | `nabinpakka/piper-nepali`, `ampixa/nepali-voices-v0` (419 speakers, ~22h, custom 65-phone inventory), QLoRA experiments on Llama-3.2-3B / Qwen2.5-3B / Gemma-2-2B | mixed |
| **Data** | OpenSLR SLR54 Nepali (large ASR corpus), Common Voice `ne` 27.0, Kathbath (Indic, **not** Nepali) | CC / open |

### The one dataset that changes our budget

`himalaya-ai/nepali-sft-suite` — **546,177 rows, 126 MB**, 6 configs:

| Config | Rows | Use to us |
|---|---|---|
| `core` | 68,056 | health, finance, education, legal instruction data — **free base SFT** |
| `romanized` | 245,916 | Romanised Nepali twins (pair_id linked) — code-switch robustness |
| `function_calling` | 4,685 | Hermes tool calls — future "search" tool routing |
| `retrieval` | 10,606 | query / positive / negative passages for **legal and health RAG** — exactly our offline corpus skeleton |
| `tabular` | 195,644 | templated, repetitive — skip by default |
| `transliteration` | 21,270 | Wikipedia Deva↔Latn — not SFT |

**Consequence: do not spend Adaption credits generating general Nepali instructions.**
That is already a solved problem in the open. Spend them on the gap.

⚠ Licence caveat: labels are *as declared by source*, not verified, and several sources were
scraped. `core` is ~41k apache-2.0, ~16k cc0, ~8k cc-by, ~3k unknown. Verify before commercial
use; prefer apache/cc0 rows for Diyo's shipped model.

---

## What the evidence says about quality

- **IndicParam (2026, 13k MCQs, 11 low-resource Indic languages):** Nepali — Gemma-3-4B **under
  30%**, Gemma-3-12B 34.8%, Gemma-3-27B ~39%, GPT-5 43.4%, Gemini-2.5 52.0%. Our own test agrees:
  Gemma 3 4B at 13/16 with all blocking cases passing, but still wrong arithmetic and invented
  telcos.
- **Romanised Nepali SLM paper (arXiv 2611.12628, 9 Nov 2026):** QLoRA on **9,000** examples lifted
  chrF++ from 10–14 to **29–30.6**. Zero-shot, **54–92% of outputs were English-like** — exactly the
  failure we measured. Tokenizer fertility (2.72 tok/word for Gemma-2-2B) did **not** predict output
  quality. Llama-3.2-3B had the best BPB but could not be separated from Qwen2.5-3B on chrF++.
- **Community LoRA on Gemma 4 E2B (468 examples)** moved Devanagari share 0.000 → 0.814 but the
  author notes it changes *language preference, not fluency*.
- **Nepal connectivity (DataReportal, Oct 2025):** 29.6M people, 16.6M online (56%), **~13M offline**,
  77% rural. That is the market.

Takeaway: **writing Nepali is a solved-ish problem at 2–4B with ~9k rows. Being right — refusing a
dose, naming the health post, not inventing a telco, not inventing weather — is not solved.**
That is our product, our dataset, and our eval.

---

## Decisions per layer

| Layer | Pick | Why | Rejected |
|---|---|---|---|
| **LLM base** | Test three: `himalaya-gemma-4-e2b-it` (Q4 3.43GB), `himalayagpt-0.5b-it`, Gemma 3 4B (our 13/16) | E2B is the only public Nepali-finetuned on-device model. 0.5B is the emergency floor for 2GB phones | Qwen3-1.7B (complied with harm, leaked Hindi), 1B-class (cannot form words) |
| **Model size** | Decide by eval **and** RAM. 3.43GB Q4 will not fit a 3GB phone | E2B's param count is inflated by embeddings; measure, don't assume | assuming "E2B" means 2GB |
| **Inference** | **llama.cpp** via JNI, arm64, Q4_K_M | Already proven here: 45.8 tok/s on 4 CPU cores. Same GGUF runs on laptop and phone | MLC (heavier APK), MediaPipe (Google models only), ExecuTorch (immature) |
| **ASR** | **sherpa-onnx** on Android; Whisper-small fine-tuned on **SLR54 + Common Voice ne**; Himalaya's `whisper-large-v3-turbo` as the accuracy ceiling | sherpa-onnx is the only mature offline ASR+TTS+VAD Android stack; SLR54 is a real Nepali corpus | cloud ASR, Kathbath (not Nepali), Vosk (no strong Nepali) |
| **TTS** | **Piper** via sherpa-onnx; voice from `ampixa/nepali-voices-v0` or `nabinpakka/piper-nepali`; Himalaya's Indic-Parler as reference | 419-speaker Nepali Piper already exists — do not train from scratch | cloud TTS, 0.9B Parler on a 3GB phone |
| **OCR** | Tesseract 5 `nep` + **Surya** for hard pages; evaluate `himalaya-ai/glm-ocr-devanagari-finetuned` and SAGEA **ARVA** | Devanagari needs conjunct + shirorekha handling; ML Kit is easy but weakest on real documents | ML-Kit-only for v0 |
| **OCR eval** | `himalaya-ai/nepalpixel-vlm-bench` (`real_ocr`: 91 real document pages) | Real Nepali documents, not synthetic | our own 2-case guesses |
| **Retrieval** | **sqlite-vec + FTS5 + RRF** on device; seed from `nepali-sft-suite/retrieval` | Hybrid lexical+vector beats either alone on short queries; SQLite ships in Android | FAISS (no Android story), LanceDB (heavy) |
| **Training** | **Adaption AutoScientist** for the gap dataset; Unsloth/QLoRA on a rented GPU as fallback | We have no GPU here; Adaption is already paid for | local training |
| **Eval** | our 30-case set as the gate + IndicParam for external comparison | Ours tests *behaviour*; IndicParam tests *knowledge* | benchmark-only |

---

## What we build that nobody has

Nobody ships this combination. It is the entire moat:

1. **A refusal dataset in Nepali** — dosing, pesticide, self-harm, harm, private records, and the
   *over-refusal* case. The 1.7B complied with harm; that is our opportunity.
2. **A referral dataset** — every health and legal answer ends by naming the actual office
   (स्वास्थ्य चौकी, कृषि ज्ञान केन्द्र, मालपोत, नापी, जिल्ला प्रशासन, वडा).
3. **A brevity dataset** — 25–40 tokens per spoken answer, because latency is a product feature.
4. **A grounded-entity dataset** — Ncell, NTC, eSewa, Khalti, IME Pay, 100/102, and no invention.
5. **A measurement** — 30 blocking cases, published, reproducible.

---

## Revised spend plan for the Adaption credits

| Old plan | New plan |
|---|---|
| ~12k general Nepali rows (~1,200 credits) | **0 credits** — use `nepali-sft-suite/core` |
| — | **pilot 200 rows** (20 credits, in flight): health behaviour |
| — | ~2,000 behaviour rows across 5 domains (~200 credits): refusal, referral, brevity, entities, arithmetic |
| — | AutoScientist runs to co-optimise the merged set (~2 experiments) |
| — | reserve ≥40% |

Expected total: **~600–800 credits of 2,158**, with the rest held back for iteration. The first
question the pilot answers is not "is the Nepali good" (Himalaya already proved that) but
**"does synthetic data produce correct refusal and referral in Nepali?"**

---

## People to talk to before writing more code

- **Himalaya AI Labs** — non-profit, Nepali, Apache-2.0, already built the model, the SFT suite, the
  tokenizer and the OCR bench. They are not a competitor; they are the upstream. Ask about
  licensing the SFT suite for commercial use and about an E2B variant sized for a 3GB phone.
- **SAGEA** — Nepali OCR and a Nepali-first decision model. Ask what ARVA's real accuracy is on
  medicine labels and government forms.
- **Sunkiree Labs / Zunkiree Labs** — publish the Nepali benchmark commentary; useful for credibility
  and for knowing what "good" looks like.

## Sources

- [Himalaya AI Labs on Hugging Face](https://huggingface.co/himalaya-ai/models) · [himalaya-gemma-4-e2b-it-gguf](https://huggingface.co/himalaya-ai/himalaya-gemma-4-e2b-it-gguf) · [nepali-sft-suite](https://huggingface.co/datasets/himalaya-ai/nepali-sft-suite)
- [SAGEA](https://www.sagea.space/) · [ARVA OCR](https://www.sagea.space/models/sage-arva-ocr)
- [Adapting Small Language Models to Romanized Nepali (arXiv 2611.12628)](https://arxiv.org/abs/2611.12628)
- [Open AI Models for Nepal (Zunkiree Labs)](https://zunkireelabs.com/blog/open-ai-models-nepali-language-and-low-connectivity/)
- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) · [Surya OCR](https://github.com/datalab-to/surya) · [piper-nepali](https://github.com/nabinpakka/piper-nepali) · [ampixa/nepali-voices-v0](https://huggingface.co/ampixa/nepali-voices-v0)
- [OpenSLR SLR54 Nepali](https://www.openslr.org/54/) · [IndicWhisper](https://ai4bharat.iitm.ac.in/areas/model/ASR/IndicWhisper/) · [Indic-TTS](https://github.com/AI4Bharat/Indic-TTS)
- [sqlite-vec RAG on Android](https://mvpfactory.io/blog/on-device-rag-for-android-running-embedding-models-vector-search-in-sqlite-and) · [On-device AI frameworks 2026](https://appscale.blog/en/blog/on-device-ai-frameworks-compared-llamacpp-mlc-onnx-mediapipe-coreml-2026)
