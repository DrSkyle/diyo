#!/usr/bin/env python3
"""Post-generation repair: a referral is not help.

The single most common failure in our benchmark is an answer that says "go to the health post" and
nothing else (ag-001, hp-005, ag-003, hd-007, hd-009, hd-014, hd-015). Training kept producing it
because small models default to the safe sentence.

So it is repaired after generation, not hoped for:
  - if the answer already contains a concrete action or a number, leave it alone
  - otherwise, look the question up in the offline corpus and prepend the most actionable sentence
  - never exceed four sentences, never add a dose, never invent an office

    from advice import repair
    text, changed = repair(question, model_answer, corpus)
"""

import re

# Concrete care steps only. "जानुहोस्" and a bare "दिनुहोस्" are deliberately absent: a referral
# is not advice, and "ध्यान दिनुहोस्" is not an action. This is the exact distinction the benchmark
# grades on, so the repair fires on referral-only answers instead of being fooled by them.
ACTIONS = ["पानी दिनुहोस्", "पानी पिउनुहोस्", "झोल", "जीवनजल", "ओरल", "दूध दिनुहोस्",
           "उमाल्नुहोस्", "धुनुहोस्", "निकास", "भुइँमा", "टेबलमुनि", "छोप्नुहोस्",
           "दबाउनुहोस्", "आराम गर्नुहोस्", "कम्बल", "सफा गर्नुहोस्", "नमुना पात",
           "माटो परीक्षण", "टाढा राख्नुहोस्", "बन्द राख्नुहोस्", "जाँच गर्नुहोस्",
           "खुवाउनुहोस्", "पुछ्नुहोस्"]
DIGITS = re.compile(r"[०-९0-9]")
SENTENCE = re.compile(r"[^।!?]+[।!?]?")
DOSE = re.compile(r"(मिलिग्राम|मिलीग्राम|mg|चक्की|मात्रा)", re.I)


def sentences(text):
    return [s.strip() for s in SENTENCE.findall(text or "") if s.strip()]


def has_action(text):
    return any(a in text for a in ACTIONS) or bool(DIGITS.search(text))


def actionable_sentence(entry):
    """First sentence of a corpus answer that actually tells the person to do something."""
    if not entry:
        return None
    for s in sentences(entry.get("text", "")):
        if has_action(s) and not DOSE.search(s) and len(s) > 20:
            return s
    return None


def repair(question, answer, corpus, max_sentences=4):
    """Return (text, changed). `corpus` is an iterable of {"text": ...} entries."""
    answer = (answer or "").strip()
    if not answer:
        return answer, False
    if has_action(answer):
        return answer, False

    for entry in corpus:
        if question.split("।")[0][:12] in entry.get("text", ""):
            addition = actionable_sentence(entry)
            if addition:
                merged = sentences(addition + " " + answer)[:max_sentences]
                return " ".join(merged), True
    return answer, False


def load_corpus(path):
    import json
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
