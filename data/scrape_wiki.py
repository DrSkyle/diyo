#!/usr/bin/env python3
"""Scrape public Nepali text into the offline corpus.

Only sources that permit it: Nepali Wikipedia (CC BY-SA 4.0, attribution required) via the
public API, one request at a time, with a real User-Agent. No paywalls, no social media, no
audio — voice requires consent and is handled by the Voice Commons, not here.

    python3 data/scrape_wiki.py --topics health,farming --limit 200

Output rows carry the source URL and licence so every answer can cite where it came from.
"""

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://ne.wikipedia.org/w/api.php"
UA = "DiyoCorpusBot/1.0 (https://devilabs.dev; hello@devilabs.dev) python-urllib"

TOPICS = {
    "health": ["स्वास्थ्य", "रोग", "ज्वरो", "औषधि", "पोषण", "खोप", "सरुवा रोग", "आमा र बच्चा"],
    "farming": ["कृषि", "धान", "मकै", "गहुँ", "माटो", "सिँचाइ", "बाली", "पशुपालन"],
    "paperwork": ["नागरिकता", "जन्म दर्ता", "जग्गा", "लालपुर्जा", "सरकारी सेवा"],
    "law": ["कानून", "अधिकार", "अदालत", "श्रम कानून", "महिला अधिकार"],
    "daily": ["नेपाल", "काठमाडौं", "यातायात", "विद्युत", "शिक्षा"],
}


def api(params):
    params = dict(params, format="json", formatversion="2")
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def search(term, limit):
    try:
        d = api({"action": "query", "list": "search", "srsearch": term,
                 "srlimit": min(limit, 50), "srnamespace": 0})
        return [x["title"] for x in d.get("query", {}).get("search", [])]
    except Exception as e:  # noqa: BLE001
        print(f"  search failed for {term}: {e}")
        return []


def extract(titles):
    out = []
    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        try:
            d = api({"action": "query", "prop": "extracts", "explaintext": "1",
                     # full extracts are capped at one page per request; intros allow 20,
                     # and an intro is exactly the size of a retrieval chunk anyway
                     "exintro": "1", "exlimit": "max",
                     "titles": "|".join(batch), "redirects": "1"})
        except Exception as e:  # noqa: BLE001
            print(f"  extract failed: {e}")
            continue
        for page in d.get("query", {}).get("pages", []):
            text = (page.get("extract") or "").strip()
            if len(text) > 80:
                out.append((page.get("title", ""), text))
        time.sleep(1)
    return out


def chunks(text, size=600, max_chunks=6):
    parts, buf = [], ""
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            continue
        if len(buf) + len(para) < size:
            buf += para + " "
        else:
            if buf:
                parts.append(buf.strip())
            buf = para + " "
        if len(parts) >= max_chunks:
            break
    if buf and len(parts) < max_chunks:
        parts.append(buf.strip())
    return [p for p in parts if len(p) > 80]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topics", default=",".join(TOPICS))
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--out", default="data/corpus/wiki-ne.jsonl")
    args = ap.parse_args()

    topics = [t.strip() for t in args.topics.split(",") if t.strip() in TOPICS]
    titles, seen = [], set()
    for topic in topics:
        for term in TOPICS[topic]:
            for title in search(term, 12):
                if title not in seen:
                    seen.add(title)
                    titles.append((topic, title))
            time.sleep(0.6)
    titles = titles[: args.limit]
    print(f"{len(titles)} articles to fetch")

    rows = []
    by_topic = {}
    topic_of = {title: topic for topic, title in titles}
    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        # Match on the title the API actually returned; redirects and missing pages mean the
        # response order does not line up with the request order.
        for page_title, text in extract([t for _, t in batch]):
            topic = topic_of.get(page_title, "general")
            for ch in chunks(text):
                rows.append({
                    "id": f"wiki-{len(rows)}",
                    "text": f"{page_title}\n{ch}",
                    "domain": topic,
                    "source": f"https://ne.wikipedia.org/wiki/{urllib.parse.quote(page_title)}",
                    "licence": "CC-BY-SA-4.0",
                })
                by_topic[topic] = by_topic.get(topic, 0) + 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                   encoding="utf-8")
    print(json.dumps({"articles": len(titles), "chunks": len(rows), "by_domain": by_topic,
                      "output": str(out)}, indent=1))


if __name__ == "__main__":
    main()
