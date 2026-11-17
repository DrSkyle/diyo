#!/usr/bin/env python3
"""Tests for the referral repair. No model, no network."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from advice import has_action, repair, load_corpus  # noqa: E402

CORPUS = [
    {"text": "धानको पात पहेँलो हुँदै गएको छ। खेतमा पानी जमेको छ भने निकास गर्नुहोस्। "
             "पातको टुप्पो पहेँलो छ भने नाइट्रोजनको कमी हुन सक्छ।"},
    {"text": "भूकम्प आउँदा के गर्ने? भुइँमा ढल्किनुहोस् र टेबलमुनि टाउको छोप्नुहोस्। "
             "हल्लिन छाडेपछि बाहिर जानुहोस्।"},
]

fails = []


def check(label, cond):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        fails.append(label)


def main():
    referral_only = "आजै नजिकको स्वास्थ्य चौकी जानुहोस्।"
    check("a referral alone is not advice", has_action(referral_only) is False)

    dead = "यो अवस्थामा सावधानी आवश्यक छ। ध्यान दिनुहोस्।"
    check("no action detected", has_action(dead) is False)

    text, changed = repair("धानको पात पहेँलो हुँदै गयो", referral_only, CORPUS)
    check("prompt match adds an action", changed is True and has_action(text))
    check("stays within four sentences", len([s for s in text.split("।") if s.strip()]) <= 4)

    untouched, changed2 = repair("केही अप्रासंगिक", dead, CORPUS)
    check("no corpus match leaves it alone", changed2 is False and untouched == dead)
    check("dead answer has no action", has_action(dead) is False)

    already = "दिनमा धेरै पटक पानी दिनुहोस्। आजै स्वास्थ्य चौकी जानुहोस्।"
    same, changed3 = repair("धानको पात पहेँलो हुँदै गयो", already, CORPUS)
    check("an answer with action is untouched", changed3 is False and same == already)

    empty, changed4 = repair("x", "", CORPUS)
    check("empty answer is not invented for", changed4 is False and empty == "")

    corpus = load_corpus(ROOT / "data" / "corpus" / "health-legal.jsonl")
    check("real corpus loads", len(corpus) > 1000)

    print("\n" + ("FAILED: " + ", ".join(fails) if fails else "all advice checks passed"))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
