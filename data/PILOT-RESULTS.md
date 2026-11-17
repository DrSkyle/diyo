# Adaption pilot: 200 health rows — verdict

**Dataset:** `diyo-health-v1` (id `2e6974ef-…`) · **Cost:** 20 credits of 2,158 · **Rows:** 200
**Wall time:** ~40 min generation · **Model:** Adaption Invent a Dataset, instruction format

## Verdict

**The behaviour is right. The text hygiene is not. Fix the generator before spending more.**

This is the answer we actually needed, and it is cheaper to learn now than after 1,200 credits.

## What came back (automated screen)

```
200 rows, 195 clean (98%), 5 flagged
  empty        5   (generation produced no completion)
  too_short    0
  DOSE         0   ← no medicine or pesticide doses invented
  missing_refusal 0
  no_referral  0   ← every clinical row names a facility
```

## What reading 4 rows found that the screen missed

The automated checks said 98% clean. Reading four rows by hand found three real defects:

1. **Corrupted `ई` → `र्+इ`.** `तपाईं` came back as **`तपार्इं`**, and `मलाई` as **`मलार्इ`**.
   **18 of 200 rows (9%).** This matters more than the percentage suggests: `तपाईं` is the single
   most frequent word in the product, and training on it would teach Diyo to misspell it.
2. **Prompt leakage** — one row had assistant-style text inside the prompt
   (`…बच्चा कति दिनको भयो? … तुरुन्तै स्वास्थ्य चौकी जानुहोस्।`), which trains the model to
   answer inside the question.
3. **Occasional garbled word** (`मलामी बिरामीको निदान` for `म कुनै बिरामीको निदान`).

Lesson to keep: **automated screening is necessary and not sufficient.** 98% clean by checks,
~87% usable by reading.

## What the good rows look like (this is the win)

Prompt (code-switched, regional, messy):

> नवान बच्चा १० दिनको, दूध चुस्दैन र सुत्छ मात्र। कर्णाली, ज्वरो छ कि छैन थाहा छैन।

Answer:

> दस दिनको बच्चाले दूध नचुस्नु र सुत्नु मात्र गम्भीर संकेत हो, कृपया बच्चाको सास फेर्ने गति
> छिटो छ कि छैन हेर्नुहोस्। यो अवस्थाको उपचारको विषयमा मलाई थाहा छैन, त्यसैले तुरुन्तै नजिकैको
> अस्पतालका डाक्टरलाई सोध्नुहोस्।

That is the target behaviour, from a synthetic row, in Nepali, with:
- danger sign named,
- one useful follow-up (breathing rate),
- explicit `मलाई थाहा छैन`,
- referral to a facility,
- no diagnosis, no medicine, no dose,
- 3 sentences, speakable.

Also observed: `Newborn baby ko jwaro aayo, fever` answered in Nepali — exactly the code-switch
case we need, and the reverse of what every base model did.

## Before the next credit is spent

1. **Append a glyph rule to the prompt** — "write तपाईं, not तपार्इं; every word must use standard
   Unicode Devanagari, no half-र substitutions" — and add a worked example.
2. **Post-normalise** any residual `र्इ` → `ई` in the pipeline, and keep the flag so we can measure
   how often the generator does it.
3. **Drop empty completions at ingest**, and require `completion` length ≥ 2 sentences.
4. **Require the prompt to be a single user turn** — no assistant text, no self-answered questions.
5. **Re-run 200 rows with the fixed prompt and compare the defect rate before scaling to 2,000.**

If the defect rate drops under 2%, generate the remaining domains (agriculture, paperwork,
rights, daily) with the same prompt and the same screen.

## Cost so far

| | |
|---|---|
| Credits spent | **20 / 2,158 (0.9%)** |
| Rows that would survive a careful review | ~174 / 200 (87%) |
| Credits for the full behaviour set, at this yield | ~700 |
| Held in reserve | ~1,400 |
