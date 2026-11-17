# Train Diyo-1 on the Himalaya base (Kaggle)

The decision this folder implements: **Adaption generates data, Kaggle does the fine-tune.**

Adaption trains only its hosted Qwen3.5 models, and Qwen3.5-2B's Nepali is the ceiling we keep
hitting (11/30 on our benchmark). The Himalaya base already speaks Nepali — it scored 18/30 with no
training at all. Adding our behaviour data to it is worth far more than adding more data to Qwen.

Adaption stays in the loop for one job: `0.1 credit/row` dataset generation. That is the part it
does better than anything else.

## What you need

| | |
|---|---|
| Kaggle account | free GPU, ~30 h/week (T4 ×2 or P100) |
| Hugging Face token | **required** — Gemma is licence-gated. Accept the terms on the model page, then create a read token |
| `diyo-sft-v1.jsonl` | built by `python3 data/export_kaggle.py` (2,256 rows, 2.0 MB) |

## Steps

1. **Build the data** (already done, rerun after generating more):
   ```sh
   python3 data/export_kaggle.py
   ```
   It refuses to export if any training prompt is a verbatim eval case. Keep it that way.

2. **Upload the dataset.** Kaggle → Datasets → New → drop `kaggle/data/diyo-sft-v1.jsonl` →
   name it exactly `diyo-sft`. It lands at `/kaggle/input/diyo-sft/`.

3. **Add the token.** Kaggle → Add-ons → Secrets → `HF_TOKEN`. The notebook reads it with
   `UserSecretsClient`.

4. **Create the notebook.** Kaggle → Code → New → File → Import notebook → `diyo_finetune.ipynb`.
   Set **Accelerator: GPU T4 ×2**, **Internet: on**.

5. **Run all.** On 2,256 rows and 3 epochs expect roughly 1–2 hours on T4 ×2.

6. **Take the adapter.** `diyo-gemma-lora/` (~100 MB). Download it, then:

   ```sh
   rm -rf artifacts/diyo-gemma-lora
   cp -r ~/Downloads/diyo-gemma-lora artifacts/diyo-gemma-lora
   git add artifacts/diyo-gemma-lora && git commit -m "diyo-gemma: QLoRA on the Himalaya base" && git push
   ```

7. **Score it** — dispatch the eval workflow against the Gemma base:

   ```sh
   gh workflow run eval.yml -f lora_dir=artifacts/diyo-gemma-lora \
     -f base_url=https://huggingface.co/himalaya-ai/himalaya-gemma-4-e2b-it-gguf/resolve/main/himalaya_gemma_4_q4_k_m.gguf \
     -f base_model_id=himalaya-ai/himalaya-gemma-4-e2b-it \
     -f model_name=diyo-gemma-lora
   ```

## What "good" looks like

| Run | Expected |
|---|---|
| Himalaya base, no training | 18/30, 0 blocking |
| **+ this adapter** | **22–26/30, 0 blocking** |
| Anything below 18 | the training data is wrong, not the base |

The adapter has to fix exactly three behaviours: advise before referring, refuse the five blocking
cases, and answer in 2–4 speakable sentences with real Nepali entities.

## If it breaks

- **`unsloth` fails on Gemma 4** → fall back to `transformers` + `peft` + `bitsandbytes`
  (`prepare_model_for_kbit_training`, same LoRA config, `Trainer` instead of `SFTTrainer`).
- **OOM on T4** → `per_device_train_batch_size=1`, `gradient_accumulation_steps=16`.
- **The model answers in English** → the chat template is wrong. Inspect one `text` row before
  training; the assistant turn must be present.
- **Loss goes to zero in 20 steps** → overfitting on duplicates. Rebuild the export.

## Rules

- Never train on the 30 eval cases. `export_kaggle.py` enforces the obvious cases; keep the
  discipline for near-duplicates too.
- Hold back 10 cases as a private set before the next round. A score on data you chose the model by
  is not a score.
- Adaption is for data only from here on.
