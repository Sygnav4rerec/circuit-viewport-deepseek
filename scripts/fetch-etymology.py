#!/usr/bin/env python3
"""
fetch-etymology.py — pull etymologies from Wiktionary for every node in the circuit graph.

Reads:   data/circuit-graph.json
         data/circuit-etymology.json (if it exists — for resume)
Writes:  data/circuit-etymology.json

Polite: 2s between requests. Retries on 429 with exponential backoff.
Resumes: skips words already in the output file.
"""

import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_PATH = DATA_DIR / "circuit-etymology.json"

# ---------- LOAD GRAPH ----------
with open(DATA_DIR / "circuit-graph.json") as f:
    graph = json.load(f)

def base_word(name):
    return name.split(".")[0].replace("_", " ")

words = sorted({base_word(n["name"]) for n in graph["nodes"]})
print(f"Total unique words: {len(words)}")

# ---------- RESUME ----------
if OUTPUT_PATH.exists():
    with open(OUTPUT_PATH) as f:
        existing = json.load(f)
    results = existing.get("etymologies", {})
    print(f"Found existing file with {len(results)} entries — resuming")
else:
    results = {}

remaining = [w for w in words if results.get(w) is None or w not in results]
print(f"Words still to fetch: {len(remaining)}\n")

if not remaining:
    print("Nothing to do — all words already have entries (or nulls).")
    print("To retry nulls, delete the file first.")
    exit(0)

# ---------- FETCH ----------
WIKTIONARY_API = "https://en.wiktionary.org/w/api.php"

HEADERS = {
    "User-Agent": "CircuitSphere/0.1 (https://circuit.vi5wport.xyz; contact: sygna@sygnav4rerec.xyz) Python/urllib",
    "Accept": "application/json",
}

def fetch_wikitext(word, max_retries=3):
    """Get raw wikitext with retry on 429."""
    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "titles": word,
        "redirects": "1",
    }
    url = WIKTIONARY_API + "?" + urllib.parse.urlencode(params)

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for _, page in pages.items():
                if "revisions" in page:
                    return page["revisions"][0]["slots"]["main"]["*"]
            return None  # page exists but no content (missing page)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 30 * (attempt + 1)
                print(f"     429 rate limit — sleeping {wait}s before retry {attempt+1}/{max_retries}")
                time.sleep(wait)
            else:
                print(f"     HTTP {e.code} — skipping")
                return None
        except Exception as e:
            print(f"     error: {e}")
            return None
    print(f"     giving up on {word}")
    return None


def extract_etymology(wikitext):
    if not wikitext:
        return None

    # Prefer English section
    english = wikitext
    m = re.search(r"==\s*English\s*==(.*?)(?=\n==[^=]|\Z)", wikitext, re.DOTALL)
    if m:
        english = m.group(1)

    # Find Etymology section (Etymology, Etymology 1, Etymology 2...)
    m = re.search(
        r"===\s*Etymology(?:\s*\d+)?\s*===(.*?)(?=\n===|\n==[^=]|\Z)",
        english,
        re.DOTALL,
    )
    if not m:
        return None

    raw = m.group(1)

    # Strip refs first
    raw = re.sub(r"<ref[^>]*>.*?</ref>", "", raw, flags=re.DOTALL)
    raw = re.sub(r"<ref[^>]*/>", "", raw)

    # Convert common templates to readable forms
    def clean_template(match):
        inner = match.group(1)
        parts = [p.strip() for p in inner.split("|")]
        if len(parts) < 2:
            return ""
        # Heuristic: for {{inh|en|enm|word}}, {{der|en|la|word}}, take the last meaningful word
        useful = []
        for p in parts[1:]:
            # Skip short language codes and named params (key=val)
            if "=" in p:
                continue
            if len(p) <= 4 and p.isalpha() and p.islower():
                continue
            if p:
                useful.append(p)
        return " ".join(useful) if useful else ""

    for _ in range(6):
        raw = re.sub(r"\{\{([^{}]+)\}\}", clean_template, raw)

    # Wiki links → display text
    raw = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", raw)
    raw = re.sub(r"\[\[([^\]]+)\]\]", r"\1", raw)

    # Remove remaining markup
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = re.sub(r"'''?", "", raw)
    raw = re.sub(r"\[\[File:[^\]]+\]\]", "", raw)
    raw = re.sub(r"\[\[Category:[^\]]+\]\]", "", raw)
    raw = re.sub(r"\s+", " ", raw).strip()

    # Take first 2-3 sentences
    sentences = re.split(r"(?<=[.!?])\s+", raw)
    summary = " ".join(sentences[:3]).strip()

    if not summary or len(summary) < 15:
        return None

    if len(summary) > 700:
        summary = summary[:697].rsplit(" ", 1)[0] + "..."

    return summary


# ---------- MAIN LOOP ----------
DELAY = 2.0  # seconds between requests

for i, word in enumerate(remaining, 1):
    print(f"[{i:2d}/{len(remaining)}] {word}")
    wikitext = fetch_wikitext(word)
    etym = extract_etymology(wikitext)

    if etym:
        results[word] = etym
        print(f"     ✓ {etym[:90]}{'...' if len(etym) > 90 else ''}")
    else:
        results[word] = None
        print(f"     ✗ no etymology")

    # Save after every word — resume-safe
    out = {
        "source": "Wiktionary REST API",
        "fetched": time.strftime("%Y-%m-%d"),
        "word_count": len(words),
        "with_etymology": sum(1 for v in results.values() if v),
        "etymologies": results,
    }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    if i < len(remaining):
        time.sleep(DELAY)

# ---------- FINAL SUMMARY ----------
out = {
    "source": "Wiktionary REST API",
    "fetched": time.strftime("%Y-%m-%d"),
    "word_count": len(words),
    "with_etymology": sum(1 for v in results.values() if v),
    "etymologies": results,
}
with open(OUTPUT_PATH, "w") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

print(f"\nWrote {OUTPUT_PATH}")
print(f"  {out['with_etymology']} of {out['word_count']} words have etymologies")
print(f"  Nulls: {sum(1 for v in results.values() if v is None)}")