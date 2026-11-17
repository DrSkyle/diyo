#!/usr/bin/env python3
"""Pre-generation guard.

Some requests must never reach the model. A 2B model that gets `safe-001` wrong once is a
liability, and no amount of fine-tuning makes that a guarantee. So the five dangerous shapes are
caught before inference, in Nepali, deterministically.

This is a floor, not a filter: it only blocks the narrow set of requests where *any* answer from a
small model is unsafe to ship. Everything else goes to the model.

    from guard import check
    forced = check("औषधि दिनको कति चक्की खाने?")
    if forced: return forced          # do not call the model
"""

import re

HARM = re.compile(
    r"(छिमेकी|मान्छे|मानिस|श्रीमान|श्रीमती|बुबा|आमा|सासू|बच्चा|कसैलाई|उसलाई|उनलाई)"
    r"[^।?!]{0,30}"
    r"(मार्न|मार्ने|हानि|हत्या|घाउ|पुर्‍याउन|पुर्‍याउने|जलाउन|विष दिन)",
    re.I)
SELF = re.compile(r"(आत्महत्या|आफूलाई मार्न|आफ्नै ज्यान|ज्यान लिन)", re.I)
DOSE = re.compile(
    r"(?:औषधि|औषध|विषादी|विष|युरिया|डीएपी|पोटास|कीटनाशक|पेस्टिसाइड"
    r"|(?<!चा)(?<!ता)मल(?!ा|ि|ु|े|ो))"          # मल, but not चामल / मलाई
    r"[^।?!]{0,30}"
    r"(?:कति|मात्रा|मिलिग्राम|मिलीग्राम|चक्की|ml|मिली|केजी|हाल्ने|खाने|दिने)",
    re.I)
TOXIC = re.compile(r"(विष हालेर|विष खान|जहर|सल्फास|कीटनाशक खान)", re.I)

# Insects are not people: "कीरा मार्ने" is legitimate farming.
BENIGN = re.compile(r"(कीरा|किरा|माहुरी|झिंगा|लामखुट्टे|मुसा|सर्प)[^।?!]{0,12}मार्न", re.I)

NEPAL_EMERGENCY = "प्रहरी १००, एम्बुलेन्स १०२"

REFUSALS = {
    "harm": (
        "म यसमा सहयोग गर्न सक्दिन। कसैलाई हानि पुर्‍याउनु गैरकानुनी हो र त्यसले जीवन बिगार्छ। "
        "धम्की वा झगडा भइरहेको छ भने नजिकको प्रहरी कार्यालय वा वडा कार्यालयमा जानुहोस्। "
        f"आपत्कालीन अवस्थामा {NEPAL_EMERGENCY} मा फोन गर्नुहोस्।"
    ),
    "self": (
        "तपाईं अहिले धेरै गाह्रो अनुभव गरिरहनुभएको जस्तो लाग्छ, र त्यो एक्लै बोक्नु पर्दैन। "
        "कृपया अहिले कसैलाई भन्नुहोस् — परिवार, नजिकको साथी, वा स्वास्थ्यकर्मी। "
        f"तुरुन्त सहयोग चाहिए {NEPAL_EMERGENCY} मा फोन गर्नुहोस् वा नजिकको अस्पताल जानुहोस्।"
    ),
    "dose": (
        "औषधि वा विषादीको मात्रा म भन्न सक्दिन, गलत मात्राले गम्भीर हानि गर्छ। "
        "प्याकेटको लेबलमा लेखेको कुरा पढ्नुहोस्, र डाक्टर वा कृषि प्राविधिकले भनेको मात्र पालना गर्नुहोस्। "
        "शंका भए नजिकको स्वास्थ्य चौकी वा कृषि ज्ञान केन्द्रमा सोध्नुहोस्।"
    ),
    "toxic": (
        "विष वा कीटनाशक खाएको वा हालेको भए तुरुन्त अस्पताल जानुहोस्। "
        "बिरामीलाई जबरजस्ती उल्टी गराउने प्रयास नगर्नुहोस्, र बोतल वा प्याकेट साथै लिएर जानुहोस्। "
        f"एम्बुलेन्स १०२ मा फोन गर्नुहोस्।"
    ),
}


def check(prompt):
    """Return a forced Nepali response, or None if the request may reach the model."""
    text = prompt or ""
    if BENIGN.search(text):
        return None
    if SELF.search(text):
        return REFUSALS["self"]
    if TOXIC.search(text):
        return REFUSALS["toxic"]
    if HARM.search(text):
        return REFUSALS["harm"]
    if DOSE.search(text):
        return REFUSALS["dose"]
    return None
