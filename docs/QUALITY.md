# What "perfect" means, in numbers

"There is no shitty version" only counts if it is measurable. This is the gate. Nothing ships
because it is impressive in a demo; it ships when these pass.

## Release gate

| # | Gate | Target | Measured by |
|---|---|---|---|
| 1 | Eval set | **30/30** | `evals/run_eval.py` |
| 2 | Blocking cases | **5/5** — dose, pesticide, harm, live weather, land records | same, exits non-zero |
| 3 | Over-refusal | 0 blocked on `over-001` and `gov-002` | same |
| 4 | Entity accuracy | **≥ 95%** numbers, units, drug names, emergency numbers | same + `ent-*` cases |
| 5 | Entity WER (voice) | **< 10%** | `asr/wer.py --entity` |
| 6 | WER, clean speech | < 15% | `asr/wer.py` |
| 7 | First sound | **< 1.5s** | device instrumented run |
| 8 | Cold start | < 3s on 3GB | device |
| 9 | Offline | full eval passes in **airplane mode** | device |
| 10 | Network discipline | build fails if a call exists outside `NetSearch.kt` | CI test |
| 11 | Crash-free sessions | ≥ 99.5% | telemetry (aggregate, Nepal-hosted, opt-in) |
| 12 | Battery | < 4%/hour idle with assistant role held | device, 3 hours |
| 13 | Size | APK < 60MB, pack < 1.8GB | CI |
| 14 | Latency under load | first sound < 2.5s at 80% battery, 2 apps in background | device |

Any gate failing = no release. A build is not "mostly fine".

## The fourteen ways this product would be shitty

These are the specific failures we refuse to ship, each with the test that catches it:

1. It gives a **dose**. → `hp-003`, `ag-002`
2. It gives a **diagnosis** it cannot make. → `hp-001`, `hp-006`
3. It **invents a number** — weather, price, fee, emergency number. → `off-001`, `gov-004`, `ent-001`
4. It **refuses a legitimate question**. → `over-001`, `gov-002`
5. It answers a **Nepali question in English or Hindi**. → `require_devanagari` on all 30
6. It **hallucinates an entity** — `नर्को`, `एग्रिको`, `११२`. → `cs-001`, `ent-001`
7. It takes **> 6 seconds** to start speaking.
8. It goes **silent when offline** without saying why.
9. It **uploads something** the user did not see.
10. It **crashes on a ₹6,000 phone**.
11. It **misspells तपाईं** — the most common word in the language.
12. It **talks over** the person.
13. It **forgets** what was just said, mid-conversation.
14. It looks like a **generic chatbot with a Nepali flag**.

## Device matrix (test before 1.0)

| Tier | Example | RAM | Must |
|---|---|---|---|
| Floor | Redmi 9A-class | 2–3GB | runs, answers in <4s |
| Target | Realme/Samsung A0x | 4GB | answers in <1.5s |
| Modern | 6–8GB, Android 14+ | 8GB | full pack, hotword |

OEM skins diverge most on: assistant role, hotword, lock-screen overlays, battery killing of
foreground services. Test on at least one MIUI, one Realme/ColorOS and one stock Android.

## The rules that keep the gate honest

- **A demo is not evidence.** The eval is. Every claim in a launch post traces to a number here.
- **Never loosen the eval to make a model pass.** If the model fails `hp-003`, fix the data.
- **Two scorers, one truth.** Automated screen for mechanical defects, a native reviewer for
  meaning. The pilot proved they disagree (98% vs 87%) — the reviewer wins.
- **Delete what users ignore.** 50 real health workers before 1.0; any feature they do not use is
  deleted, not explained.
- **Every bug becomes a case.** If a user reports a wrong answer, it is added to the eval before it
  is fixed.

## Publishing the number

When Diyo-1 is ready, publish:

- the 30 cases and their answers,
- the model name, size and quantisation,
- the eval date and the exact command to reproduce,
- the base model, credited once, per `docs/LICENSING.md`.

"Here are the five things our model refuses to do, and the test that proves it" is a launch post
nobody else in this market can write.
