# Diyo

**by Devilabs**

A Nepali AI that works with no internet, on the cheapest Android phone in the room.

A diyo is an oil lamp: it burns without the grid. That is the whole idea. Two bars of
signal, a 3GB phone, a village in Karnali — Diyo still answers, in Nepali, out loud.

---

## The proof

A ₹6,000 Android in **airplane mode**.

> "मेरो बच्चालाई तीन दिनदेखि ज्वरो आएको छ र केही खाइरहेको छैन। के गर्नुपर्छ?"

Diyo answers out loud, in Nepali, in under two seconds, and says the thing that matters:
how old the child is, whether they can drink, and go to the health post **now** if the
child is under two, limp, or cannot drink.

No bars on the screen. Nothing left the phone. That is the entire launch video.

---

## v0: what actually ships

| Capability | v0 behaviour | Needs internet |
|---|---|---|
| Talk (Nepali in, Nepali out) | On-device ASR → local model → on-device TTS | No |
| Read (text) | Local model + offline corpus | No |
| See (paper) | On-device Devanagari OCR: medicine labels, government forms, bank slips, notices | No |
| See (scenes) | Describe a photo — **online only** in v0, clearly labelled | Yes |
| Search | Ask the web, then answer in Nepali — **online only**, never silent | Yes |
| Know (offline corpus) | Health, farming, government paperwork, legal rights, daily life | No |

**The Nepali-language answer is the product.** Everything else is plumbing.

## Non-goals for v0

- Not an English assistant with Nepali bolted on.
- Not a chatbot that guesses. If it does not know, it says so and points to a human.
- Not a medical device. It triages and refers; it never gives a dose.
- No account, no login, no telemetry.

## Principles

1. **Offline is the default, not a fallback.** Every core answer works at zero bars.
2. **Say "मलाई थाहा छैन" out loud.** A confident wrong answer about a sick child is worse
   than no answer. Refusal is a feature and is measured.
3. **Online is visible.** When Diyo uses the network, the screen says so. There is no
   silent upload.
4. **Nepali first, including code-switching.** Real speech is "मेरो phone मा recharge
   कसरी गर्ने?" — the model must handle that, not correct it.
5. **One test enforces privacy.** Like Soteria: the suite fails if a network call appears
   outside the search module.

## Who it is for

- Community health workers making decisions with no reference book and no signal
- Farmers with no agronomist
- Anyone standing in front of a government form they cannot read
- Families in the hills where the tower dies at 6pm

## Hardware target

| | Minimum | Target |
|---|---|---|
| Android | 9 | 12+ |
| RAM | 3GB | 4–6GB |
| CPU | arm64 with dotprod | + i8mm |
| Storage free | 1.8GB (model pack) | 2.5GB |
| Answer latency | < 4s | < 1.5s |

APK stays small (~50MB). Model pack downloads separately over Wi-Fi, resumable.

## What is in this repo

```
diyo/
├── README.md                 this file
├── DECISIONS.md              the eight locked technical decisions and why
├── evals/
│   ├── nepali_eval.jsonl     the benchmark: 16 cases, incl. must-refuse and must-not-know
│   └── run_eval.py           stdlib-only harness, any OpenAI-compatible endpoint
├── data/
│   └── adaption-dataset-spec.md   how the Adaption credits get spent, with quality gates
└── app/                      Android (built on CI; see app/README.md)
```

## Measure it, or it is a demo

```
python3 evals/run_eval.py --dry-run
python3 evals/run_eval.py --endpoint https://... --model diyo-np-v0
```

A model is shippable when it passes **16/16**, including every `must_refuse` and
`must_not_know` case. A model that passes health but fails refusal does not ship.

## Roadmap

1. **Eval set + data spec** ← we are here
2. Nepali instruction dataset on Adaption, native-reviewed
3. QLoRA fine-tune → 4-bit GGUF → measure on the eval set
4. Android shell: ASR + model + TTS, offline, one screen
5. OCR for labels and forms
6. Online search, gated and visible
7. Ship to 20 health workers. Watch them use it. Delete what they ignore.
