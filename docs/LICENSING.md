# Licensing: how Diyo-1 becomes genuinely ours

## What we are building on

`himalaya-ai/himalaya-gemma-4-e2b-it` — Apache-2.0, from Himalaya AI Labs (non-profit, Nepal).
Base: `google/gemma-4-E2B-it` (Gemma licence).

## What Apache-2.0 gives us

| We can | We must |
|---|---|
| Use it commercially | Keep the copyright notice and licence text |
| Modify it, fine-tune it, quantise it | State that we changed it |
| Distribute the result under our own product name | Include the NOTICE file with any distribution |
| Charge for it | Not use their trademarks to endorse us |

Apache-2.0 is **permissive on purpose**. It is not a limitation, it is permission.

## The honest framing is also the strongest framing

> **Diyo-1** — our Nepali model. Built on the open Gemma-4-E2B Nepali base from Himalaya AI Labs,
> then trained by Devilabs on 12,000 Nepali safety and referral examples, evaluated on a 30-case
> published benchmark.

Every word of that is true, and it is *better* marketing than "we made it from scratch":

- **It is checkable.** A journalist or a competitor can verify it in an afternoon. A lie cannot
  survive that; this survives everything.
- **It earns the community.** Himalaya AI Labs is a Nepali non-profit doing the same work for the
  same country. Crediting them is how you get their help, their data, and their audience. Fighting
  them is how you lose all three.
- **It makes the claim specific.** "We made a model" is noise in 2026. "We made the model that
  refuses to give a dose in Nepali, and here are the 30 tests" is a story.
- **Weights carry fingerprints.** GGUF files record architecture, tensor names and metadata; the
  hash chain back to the base is public. Pretending otherwise is not a risk, it is a certainty.

## What is actually ours (the part worth defending)

1. **Diyo-1**: our SFT on top of the base — the checkpoint is ours.
2. **The behaviour dataset**: refusal, referral, brevity, entities, arithmetic, over-refusal.
3. **The eval**: 30 blocking cases, published and reproducible.
4. **The offline corpus**: curated, cited, reviewer-signed, in five domains.
5. **The voice stack**: our single-speaker Nepali voice, our ASR fine-tune, our latency budget.
6. **The product**: the keyboard, the overlay, the offline pack, the whole thing.

That is a real moat. The base weights are not, and never were.

## NOTICE file (ship this)

```
Diyo
Copyright 2026 Devilabs

This product includes a model derived from himalaya-ai/himalaya-gemma-4-e2b-it,
Copyright Himalaya AI Labs, licensed under the Apache License, Version 2.0.
The base model is derived from google/gemma-4-E2B-it, used under the Gemma Terms of Use.

Diyo-1 is a modified version: it was fine-tuned by Devilabs on Nepali instruction data.
The original licence and this notice are retained in full at:
    https://github.com/<org>/diyo-models/blob/main/NOTICE

Apache License 2.0: https://www.apache.org/licenses/LICENSE-2.0
```

Put it in the About screen too. One line, under the version number. Nobody will ever complain, and
the right people will notice that we did it.

## Naming

- **Diyo-1** — our fine-tune. Ours. Say "we trained Diyo-1" freely, because we did.
- **Base: Gemma-4-E2B-Nepali (Himalaya AI Labs)** — say it once, wherever the model is described.

Two names, no argument, and the product is still completely ours.
