# Diyo Voice Commons: getting voices from everyone, legally

You want the voice to sound like real Nepali people, so you need real Nepali voices. That instinct
is right — and there is no consented Nepali voice corpus at scale, which is exactly why this is the
moat. But "voices from everyone" only works as **a donation programme with a consent record**, not
as collection. The difference is the whole company.

## Why it must be consent-first

Voice is personal data under Nepali law (Individual Privacy Act 2075) and is treated as a
biometric-adjacent identifier in most 2026 regimes. The emerging standard, and the one every serious
voice company follows, is: **a consent record that ties a voice asset to an authorization**, with a
stated scope and a withdrawal path. The EU AI Act adds machine-readable marking of synthetic audio.
Scraped voices from YouTube or TikTok fail all of this and would end the "made in Nepal, trusted by
Nepal" story on day one.

## What people are donating to

**Diyo Voice Commons** — an open Nepali speech corpus, hosted in Nepal, that makes Nepali speech
technology better for everyone. Not "give us your voice so we can clone you."

Three scopes, chosen separately, each revocable:

| Scope | What it allows | Never allows |
|---|---|---|
| **A — Listening** | Training speech recognition (ASR) on your audio | Making a voice that sounds like you |
| **B — Speaking** | Training multi-speaker Nepali text-to-speech | Cloning your identity for others to use |
| **C — Style** | Learning pace, emotion and prosody patterns in aggregate | Any single-person imitation |

Default is **A only**. B and C are separate, explicit ticks, each explained in one plain Nepali
sentence. Nobody can select C without B, and no individual voice is ever extracted as a product.

## The recording session (20–30 minutes, on a cheap phone)

| Part | Length | Purpose |
|---|---|---|
| 1. Read 250 sentences | 15 min | phoneme and conjunct coverage, numbers, units, dates |
| 2. Read 50 digit-heavy lines | 3 min | prices, doses, years — where ASR fails today |
| 3. Speak 5 free-form prompts | 5 min | natural pace, no reading voice ("तपाईंको बिहान कस्तो हुन्छ?") |
| 4. Read 30 code-switch lines | 3 min | "मेरो phone मा recharge…" |
| 5. Emotion pass (optional, scope C) | 3 min | calm, urgent, reassuring — a health assistant needs these |
| 6. Dialect pass (optional) | 5 min | eastern / western / hill vocabulary, in the speaker's own words |

Sentence selection is generated and checked to cover: every Devanagari consonant and matra, common
conjuncts, retroflex vs dental contrasts (ड/द, ण/न), aspiration pairs (क/ख, त/थ), Nepali numerals,
and the top 500 words by frequency.

### Quality control, automatic

| Check | Reject if |
|---|---|
| Clipping | > 0.5% samples at full scale |
| SNR | < 20dB estimated |
| Length | < 1.2s or > 15s for a read line |
| Silence / wrong take | VAD finds no speech |
| Duplicate | near-identical to a prior take |
| Read-back mismatch | forced-align transcript disagrees with the prompt |

Rejected takes are re-recorded immediately, in-session. The contributor always sees the pass rate —
nobody should spend 20 minutes producing data we then throw away.

## The consent record (the part lawyers care about)

```json
{
  "contributor_id": "vc_8f21...",
  "record_version": 3,
  "granted_at": "2026-11-17T09:41:00+05:45",
  "scopes": {"listen": true, "speak": true, "style": false},
  "purpose": "training Nepali speech models for Diyo",
  "territory": "model training and evaluation in Nepal",
  "withdrawal": "any time, in-app, effective at next rebuild within 30 days",
  "audio_license": "Diyo Voice Commons 1.0",
  "signature": "…", "text_hash": "…"
}
```

- Withdrawal deletes the audio and every derived training artefact at the next rebuild **and** the
  record says when.
- Deletion is proven, not implied: the contributor can request a receipt.
- The consent text exists in Nepali (primary), Maithili and English, at a 6th-grade reading level.

## What the corpus becomes

- **ASR**: SLR54 + Common Voice + Voice Commons → fine-tune Whisper-small / Zipformer.
- **TTS**: multi-speaker training on consented scopes B/C → pick the best 1–3 voices, then
  single-speaker fine-tune for naturalness. Voices are credited, never sold individually.
- **Style**: the emotion pass teaches *how* to speak an urgent instruction, not *whose* voice to use.
- **Release**: the corpus is published as an open dataset with the same consent scopes, so Nepali
  researchers benefit too. A public good is what makes people donate.

## Incentives that are not creepy

- The counter that matters: "तपाईंको आवाजले १२,४०० जनालाई सहयोग गर्यो."
- Credit in the dataset and in release notes, if they want it.
- Early access to the better voice, free.
- Airtime/data reimbursement for long sessions — pay in data packs, not per clip. Cash per clip
  turns consent into a transaction and attracts junk audio.
- **Never** pay someone to donate another person's voice. One account, one verified voice.

## Hard rules

1. No scraping social media, YouTube, radio or television audio. Ever.
2. No cloning of a named individual, including the contributor, as a product feature.
3. No sale or sub-licensing of raw audio to third parties.
4. No use outside the declared scope — audio given for "listening" is never used to train a voice.
5. Every generated audio output carries a machine-readable synthetic marker.
6. Any voice actor used for a shipped voice signs a separate, paid, narrow-scope agreement.
7. Data stays in Nepal, per `docs/DATA-SOVEREIGNTY.md`.

## Why this is worth more than the model

Anyone can download a Nepali model. **Nobody has a 500–1,000 hour consented Nepali voice corpus
with provenance and scope metadata.** That corpus is a decade-long asset, it makes the TTS better
than anything closed, and it is the one thing a competitor cannot copy by cloning a repo.
