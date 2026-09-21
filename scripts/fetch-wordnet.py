#!/usr/bin/env python3
"""
fetch-wordnet.py — pull the six "circuit" noun senses and their neighbors.

Outputs:
  data/circuit-synsets.json   — the six senses with definitions and examples
  data/circuit-graph.json     — all connected synsets and the edges between them
"""

import json
from pathlib import Path

import nltk
from nltk.corpus import wordnet as wn


# ---------- SETUP ----------
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Ensure WordNet is downloaded
try:
    wn.synsets("circuit")
except LookupError:
    nltk.download("wordnet")
    nltk.download("omw-1.4")


# ---------- HELPERS ----------
def synset_to_dict(s):
    """Convert a WordNet synset to a plain dict for JSON output."""
    return {
        "name": s.name(),
        "pos": s.pos(),
        "definition": s.definition(),
        "examples": s.examples(),
        "lemmas": [l.name() for l in s.lemmas()],
        "hypernyms": [h.name() for h in s.hypernyms()],
        "hyponyms": [h.name() for h in s.hyponyms()],
        "part_holonyms": [h.name() for h in s.part_holonyms()],
        "part_meronyms": [h.name() for h in s.part_meronyms()],
        "also_sees": [h.name() for h in s.also_sees()],
    }


# ---------- PULL THE CIRCUIT SENSES ----------
circuit_synsets = wn.synsets("circuit", pos=wn.NOUN)

print(f"Found {len(circuit_synsets)} noun senses for 'circuit':\n")
for i, s in enumerate(circuit_synsets, 1):
    print(f"  {i}. {s.name()}")
    print(f"     {s.definition()}\n")


# ---------- BUILD THE GRAPH ----------
nodes = {}       # name -> dict
edges = set()    # (source, target, relation)

def add_node(s):
    if s.name() not in nodes:
        nodes[s.name()] = synset_to_dict(s)

def add_edge(a, b, relation):
    edges.add((a.name(), b.name(), relation))

# Seed with the six circuit senses
for s in circuit_synsets:
    add_node(s)

# One hop out from each circuit sense
for s in circuit_synsets:
    for h in s.hypernyms():
        add_node(h)
        add_edge(s, h, "hypernym")
    for h in s.hyponyms():
        add_node(h)
        add_edge(s, h, "hyponym")
    for h in s.part_holonyms():
        add_node(h)
        add_edge(s, h, "part_holonym")
    for h in s.part_meronyms():
        add_node(h)
        add_edge(s, h, "part_meronym")
    for h in s.also_sees():
        add_node(h)
        add_edge(s, h, "also_see")

circuit_names = {s.name() for s in circuit_synsets}


# ---------- WRITE OUTPUT ----------
synsets_out = {
    "word": "circuit",
    "pos": "noun",
    "sense_count": len(circuit_synsets),
    "senses": [synset_to_dict(s) for s in circuit_synsets],
}

graph_out = {
    "word": "circuit",
    "node_count": len(nodes),
    "edge_count": len(edges),
    "circuit_senses": list(circuit_names),
    "nodes": list(nodes.values()),
    "edges": [
        {"source": a, "target": b, "relation": r}
        for a, b, r in sorted(edges)
    ],
}

with open(DATA_DIR / "circuit-synsets.json", "w") as f:
    json.dump(synsets_out, f, indent=2)

with open(DATA_DIR / "circuit-graph.json", "w") as f:
    json.dump(graph_out, f, indent=2)

print(f"\nWrote {DATA_DIR / 'circuit-synsets.json'}")
print(f"Wrote {DATA_DIR / 'circuit-graph.json'}")
print(f"\nGraph summary:")
print(f"  Nodes: {len(nodes)}")
print(f"  Edges: {len(edges)}")
print(f"\nIf node count is over 500, we add a filter before laying out.")
print(f"If it's under 200, we have room to expand.")