# Spend plan for the Adaption Labs credits

Two products of theirs matter to us:

1. **Invent a Dataset** — generates instruction/preference rows from a task description,
   no seed corpus needed.
2. **Fine-tuning** — runs the training loop.

The trap: synthetic Nepali looks right to a non-speaker and is wrong in ways that matter.
A model trained on unreviewed synthetic Nepali will confidently say `"तपाईंको बच्चालाई
निमोनिया भएको छ"` with perfect grammar. That is worse than useless.

**Rule: Adaption generates candidates. Humans approve every row that ships.**
The credits are for *volume of candidates*, not for skipping review.

---

## Target dataset

| | |
|---|---|
| Examples | 10,000–15,000 (QLoRA needs quality, not millions) |
| Languages | Nepali 90%, Nepali↔English code-switch 10% |
| Domains | स्वास्थ्य 30%, कृषि 15%, सरकारी कागजात 20%, कानूनी अधिकार 10%, दैनिक जीवन 25% |
| Registered as | तपाईं (respectful), short sentences, no Sanskritised bureaucratese |
| Dialect coverage | at least 15% marked Eastern (झापा/विराटनगर) and 15% Western (कर्णाली/सुर्खेत) phrasing |

### Non-negotiable slices

These are the rows that decide whether the product is safe, so they get dedicated
generation passes and 100% human review:

- **Refusals** (~600): dosing, pesticide dosing, self-harm, harming others, illegal
  documents, pretending to be a doctor/lawyer.
- **"मलाई थाहा छैन"** (~600): live weather, private land records, specific prices,
  another person's data, anything requiring a database we do not have.
- **Referral** (~800): every health and legal answer must end by naming the human or
  office to see, in Nepali (स्वास्थ्य चौकी, कृषि ज्ञान केन्द्र, मालपोत, जिल्ला
  प्रशासन, वडा कार्यालय).
- **Code-switching** (~1,000): real Nepali speech is mixed. `"मेरो phone मा recharge
  कसरी गर्ने?"` must be answered, not corrected.
- **Devanagari numerals** (~400): १२, ९५, ११४० — reading and arithmetic.
- **Label/form reading** (~1,000): medicine label, prescription slip, bank slip,
  government notice, exam result — text in, plain Nepali explanation out.

---

## Row schema

```json
{
  "messages": [
    {"role": "system", "content": "<the Diyo system prompt>"},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "domain": "health",
  "subtype": "urgent_referral",
  "source": "adaption:invent/v3 | human | gov.np | who",
  "reviewer": "initials + date",
  "verified_on": "2026-11-17",
  "dialect": "standard | eastern | western",
  "notes": "why this row exists"
}
```

Rows without `reviewer` do not train. Rows without a `source` do not train.

---

## Prompt to paste into Invent a Dataset

> Generate Nepali (Devanagari) instruction-tuning rows for a rural offline health and
> daily-life assistant used on a low-end Android phone in Nepal.
>
> Constraints:
> - Register: respectful `तपाईं`, short sentences, common spoken Nepali. No Sanskritised
>   formal register, no English-only answers.
> - Every health answer must (a) name the danger signs, (b) tell the person where the
>   nearest health facility is in general terms, (c) never state a medicine dose, and
>   (d) never claim a diagnosis.
> - Every legal or paperwork answer must name the office to visit and say the rules can
>   change, so the person should confirm there.
> - Where live data is required (weather, prices, land ownership), the assistant must say
>   `मलाई थाहा छैन` and explain why, rather than inventing a value.
> - Answers: 2–5 sentences spoken aloud. They will be read by TTS, so avoid tables,
>   bullet glyphs, and long numbers.
> - Include realistic messy inputs: typos, Romanised Nepali, Nepali-English mixing,
>   half-sentences, and regional words (eastern and western Nepal).
> - Produce 10 variants per seed with genuinely different phrasings, not paraphrases of
>   the same sentence.

---

## Budget shape (check Adaption's current pricing before committing)

| Slice | Share | What it buys |
|---|---|---|
| Candidate generation across 5 domains | ~45% | 30–40k raw rows, of which ~12k survive review |
| Two fine-tune experiments (model A vs model B) | ~25% | Same data, different base — this is how D1 gets decided |
| Second fine-tune after eval failures | ~20% | The iteration everyone forgets to budget |
| Reserve | ~10% | Re-runs, ASR/TTS if their stack supports audio |

**Do not spend any of it before `evals/run_eval.py` runs against a base model.** You need
a baseline score for the chosen base model (Gemma-class and Qwen-class) first, or you are
buying upgrades you cannot measure.

---

## Order of operations

1. Baseline: run the eval set against both candidate base models. Record scores.
2. Generate a 500-row pilot. Human-review 100%. Measure the review-accept rate.
   If acceptance is under 50%, fix the prompt before spending the rest.
3. Generate the real set. Review in slices, keep accept/reject reasons.
4. Fine-tune model A. Eval. Fine-tune model B. Eval. Keep the winner.
5. Iterate on the blocking IDs (`hp-003`, `ag-002`, `off-001`, `law-001`, `safe-001`)
   until they are perfect. Everything else is secondary.
6. Export 4-bit GGUF, re-run the eval against the quantised file — quantisation breaks
   refusal behaviour before it breaks fluency.
