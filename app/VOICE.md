# Diyo voice: how it is always there

ChatGPT and Gemini are always available on Android because they hold **the assistant role**, not
because of a floating window. That is the mechanism, and it is open to us.

## The invocation stack (what "always there" actually means)

| What the user experiences | Android mechanism | Notes |
|---|---|---|
| Long-press home / power → Diyo opens, even **locked** | `ROLE_ASSISTANT` + `VoiceInteractionService` + `VoiceInteractionSession` | The system launches us, above the keyguard. `setShowWhenLocked(true)` on the session activity. This is the main surface. |
| Say **"दियो"** with the screen off | `AlwaysOnHotwordDetector` (via `VoiceInteractionService`) or `HotwordDetectionService` (API 31+) | Only available to the app holding the assistant role. System owns the mic; we get the event. |
| Pull down → tap Diyo tile | `TileService` | One tap from any screen, including over apps. |
| Hold the power button, or a gesture | System assistant gesture | Configured by the user; the device already has this. |
| In any app → small orb | `SYSTEM_ALERT_WINDOW` | Opt-in, small, dismissable. For "while I'm in WhatsApp" moments. |
| Type instead | `InputMethodService` keyboard | **Still worth building** — but as a *text* surface, not the main entry point. |

**Order:** assistant role → hotword → tile → orb → keyboard. The role is first because without it
there is no lock-screen access and no hotword, and those two are the whole product.

### Requirements to hold the role

- Declare `VoiceInteractionService` + `VoiceInteractionSessionService` and a `RecognitionService`.
- Request it with `RoleManager.createRequestRoleIntent(RoleManager.ROLE_ASSISTANT)`; the user
  confirms once.
- Hotword needs the role **and** an explicit user opt-in; the OS shows the mic indicator and the
  privacy dot whenever it is listening. We surface that honestly: an ongoing "दियो सुन्दै छ" chip.
- Only one app can be the assistant at a time. Losing the role degrades Diyo to tile + orb + keyboard
  — design for that, never assume it.

**Verify on real devices before committing:** lock-screen invocation, hotword with screen off, and
battery cost of the detector. Do this on a 3GB Android 12 and an Android 15 phone. OEM skins
(Custom ROMs, MIUI, Realme) diverge here more than anywhere else in Android.

---

## The conversation loop (voice, not text-to-speech over chat)

1. **Invoke.** Long-press, hotword, tile, or orb.
2. **Listen.** VAD opens on speech, closes after ~200ms of silence. Waveform on screen, not a spinner.
3. **Hear back.** Final transcript appears on screen *before* the answer, so the user can catch a
   mishear. Tap any word to fix it — **and that correction is the most valuable data we get**
   (see `docs/DATA-SOVEREIGNTY.md`).
4. **Answer.** First clause is spoken while the rest is still generating.
5. **Barge-in.** Any speech from the user stops playback instantly.
6. **Continue.** Follow-up questions keep context for the session; "फेरि भन्नुहोस्" always works.

Text mode is the same screen with the mic off. Speak or type, one interface.

---

## Natural voice

The public Nepali voices sound robotic because they are **419-speaker averages** — they have to
sound like everyone, so they sound like nobody.

1. **Pick one voice.** The cleanest, warmest speaker from `ampixa/nepali-voices-v0`, with consent.
   A real voice actor, not a clone of a real person.
2. **Fine-tune single-speaker VITS/Piper** at 22.05 kHz on that speaker's hours only.
3. **Expand numbers before synthesis.** `११४०` → "एक हजार एक सय चालीस". TTS reads raw digits badly;
   this single step removes most "robot" moments in a product about prices, doses and dates.
4. **Stream by clause.** Synthesise the first sentence at the first `।`; do not wait for the answer.
5. **Prosody lives in the text.** Short sentences, correct `।`, no lists, no parentheses — written
   for the ear.
6. **Backchannel.** A quiet "हँ" while thinking. Silence reads as broken.
7. **Reference ceiling:** `himalaya-ai/indic-parler-tts-nepali-finetuned` (0.9B) for A/B audio; later
   distil it into the small voice model.

## Latency budget — first sound in ~1.15s

| Step | Budget |
|---|---|
| End-of-speech (VAD) | 200ms |
| ASR finalise | 300ms |
| LLM first clause | 400ms |
| TTS first audio | 250ms |
| **First sound** | **~1.15s** |
| Whole 3-sentence answer | ~6s |

This is why answers are 25–40 tokens. Brevity is a latency feature.

## What we will not do

- Background listening without a visible, ongoing indicator.
- `AccessibilityService` screen scraping.
- Voice cloning of real people.
- Cloud round-trips for anything an on-device model can do.
- Claiming the base model as ours (see `docs/LICENSING.md`).
