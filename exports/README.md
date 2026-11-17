# Diyo SFT dataset

**7,586 rows.** Two columns, `prompt` and `completion`, both Nepali (Devanagari).

| File | Use |
|---|---|
| `diyo-sft-8k.jsonl` | JSON lines, one object per row — QLoRA/Unsloth, Adaption, anything |
| `diyo-sft-8k.csv` | same rows as CSV — Excel, HF datasets, Kaggle |

## What it is

Instruction pairs for an offline Nepali assistant: health triage, farming, government
paperwork, legal rights, daily life, plus 585 rows that pair a misheard (garbled) prompt with the
correct answer, so the model survives ASR errors.

## How it was built

1. Generated with Adaption `datasets.invent` across six domain prompts and four generation rounds.
2. **Repaired** the deterministic glyph defect where `ई` was written as `र्+इ` (`तपार्ईं` → `तपाईं`).
3. **Dropped** empty completions (2,292), near-duplicates at ≥0.85 shingle overlap (585),
   Latin-heavy rows (83), sub-120-character answers (80), markdown (2).
4. **PII redacted** in every row: phone numbers, emails, long digit runs.

## Known weaknesses — read before training

- **Completion median is 248 characters** (p10 178, p90 329). That is roughly three short
  sentences. Adaption's own quality evaluation graded this data **C**, with completion quality at
  the **2nd percentile** against their reference (5.22 vs 9.38). Prompts scored better (12th
  percentile) than answers.
- **More rows did not help.** Training runs measured on our 32-case benchmark and a 20-case
  holdout:

  | rows | Adaption win | 32 cases | holdout |
  |---|---|---|---|
  | 2,256 | 0.9343 | **25/32** | **13/20** |
  | 5,820 | 0.8513 | 22/32 | 11/20 |
  | 7,586 | 0.8257 | 23/32 | 12/20 |

  The smaller set won. If you fine-tune this 7,586-row version, expect it to land *below* the
  25/32 result unless the base is much better than Qwen3.5-2B or the answers are rewritten denser.
- The data teaches **behaviour** (advise before referring, refuse doses, name real offices), not
  facts. Facts belong in retrieval.

## What the model is good for

Health-safety behaviour, refusal discipline, referral patterns, short spoken Nepali answers. Not
open-domain knowledge, not arithmetic, not anything needing live data.

## Base model used in our runs

`Qwen/Qwen3.5-2B` via Adaption (win rates above). The Nepali-finetuned
`himalaya-ai/himalaya-gemma-4-e2b-it` is the better base if you can fine-tune it — see
`kaggle/diyo_finetune.ipynb`.
