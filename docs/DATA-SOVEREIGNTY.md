# Data, consent, and where it lives

Two promises, both checkable:

1. **Nepali voices stay in Nepal.**
2. **Nothing is used to train anything unless the person chose it, per item.**

A product people tell their doctor about cannot rely on a privacy policy nobody reads. It has to be
visible in the interface.

---

## 1. Residency: stored in Nepal

| Layer | Choice | Why |
|---|---|---|
| Primary database | Postgres on a Kathmandu-hosted provider | In-country, under Nepali jurisdiction |
| Object storage (audio, packs) | Nepal S3-compatible bucket, two physical sites | Backups must not leave the country either |
| Backups | Second Kathmandu site, encrypted, 30-day rotation | A backup in Singapore is not "stored in Nepal" |
| CDN | Nepal PoP only, for model packs | Speed for a 1.8GB download matters more than global reach |
| Telemetry | Our own endpoint in Nepal, aggregate only | No third-party analytics SDK that phones home |

This rules out the easy stack. **No Supabase, no Render, no US Cloudflare Workers** for Diyo — those
were fine for Oneiroi, they are wrong here. A Worker in Singapore is not Nepali data residency,
even if the domain says `.np`.

Legal context: the **Individual Privacy Act 2075 (2018)** governs personal data now; a Data
Protection Bill has been in progress. Publish the notice in plain Nepali, at a 6th-grade reading
level, and have a Nepali lawyer read it.

## 2. Consent: three tiers, default is the safest

| Tier | What leaves the phone | Default | How the user chooses |
|---|---|---|---|
| **0 — Stay here** | Nothing. Ever. | ✅ on | The default, and the honest one |
| **1 — Fixes** | The **text** pair: what the mic heard → what the user corrected it to. No audio. | Off | "यो सुधार पठाउने?" on the correction chip |
| **2 — Voice** | The **audio clip** plus its corrected transcript | Off | Per-clip preview: play it, read it, then decide |

Rules that make this real rather than decorative:

- Nothing is ever uploaded in the background. Upload happens on a tap, per item.
- The exact payload is shown before it is sent — the clip, the transcript, the correction.
- Withdrawing consent deletes past contributions from the training set on the next rebuild.
- Audio is stripped of metadata (device, timestamps) before it leaves.
- Deletion is one switch, and it is not buried.

## 3. The flywheel nobody else has

When the mic mishears and the user taps a word to fix it, we get the exact pair that is hardest and
most valuable:

```
heard  : मेरो छोरा लाई तीन दिन देखि जोरो आयो
meant  : मेरो छोरालाई तीन दिनदेखि ज्वरो आएको छ
```

That is a real human correction of a real ASR failure, in a real Nepali voice, in the user's own
dialect. No synthetic pipeline can produce it. This is how Diyo gets better than every model
trained on scraped text.

Make it visible and make it matter:

- A counter on the profile: **"तपाईंले ४७ सुधार दिनुभयो"** — and what those 47 corrections changed.
- Show the outcome: "तपाईंको सुधारबाट ज्वरो शब्द अब ९४% ठीक सुनिन्छ" (before/after on a real metric).
- Credit contributors in release notes if they want it.
- Never pay per clip — that turns consent into a transaction and attracts junk.

## 4. What we never collect

- Background audio, ever.
- Contacts, SMS, call logs, location history.
- Screen contents.
- An advertising identifier, or any third-party tracking SDK.
- Anything at all from a user in tier 0 — and tier 0 must stay genuinely useful, or the promise is
  a hostage situation.

## 5. Enforcement, not promises

- **A test** fails the build if a network call exists outside `NetSearch.kt` (the Soteria discipline).
- **A public dataset ledger**: every training run lists its sources, row counts and consent tier.
- **Reproducible eval**: the 30 blocking cases ship in the repo so anyone can check the claims.
- **A public data page** listing the exact hosts, with their addresses, so residency is verifiable by
  ping.

If we ever cannot honour a line here, we change the product, not the promise.
