#!/usr/bin/env python3
"""
layout.py — compute 3D positions for the circuit graph.

Reads:   data/circuit-graph.json
Writes:  data/circuit-layout.json

Algorithm:
  1. Compute pairwise semantic distance between the 7 anchors (WordNet path).
  2. Position anchors in 3D using classical MDS on the distance matrix.
  3. Scale anchors so they sit on a sphere of radius ANCHOR_RADIUS.
  4. Place satellites in a shell around their parent anchor, radius scaled
     by satellite count. Satellites of satellites get pushed outward.
"""

import json
import math
from pathlib import Path

import numpy as np
from nltk.corpus import wordnet as wn


# ---------- CONFIG ----------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

ANCHOR_RADIUS = 5.0          # radius of the anchor sphere
SHELL_MIN     = 0.6          # min satellite shell radius
SHELL_MAX     = 1.6          # max satellite shell radius (for the densest anchor)
SAT_RADIUS    = 0.05         # base visual size for a satellite node
ANCHOR_SIZE   = 0.14         # base visual size for an anchor node


# ---------- LOAD GRAPH ----------
with open(DATA_DIR / "circuit-graph.json") as f:
    graph = json.load(f)

nodes = {n["name"]: n for n in graph["nodes"]}
anchors = set(graph["circuit_senses"])
edges = graph["edges"]

print(f"Loaded {len(nodes)} nodes, {len(anchors)} anchors, {len(edges)} edges")


# ---------- DISTANCE BETWEEN ANCHORS ----------
def anchor_distance(a_name, b_name):
    """Semantic distance between two anchor synsets via WordNet path."""
    a_syn = wn.synset(a_name)
    b_syn = wn.synset(b_name)
    try:
        path = a_syn.shortest_path_distance(b_syn)
        if path is None:
            return 10.0  # fallback: treat as very distant
        return float(path)
    except Exception:
        return 10.0


anchor_list = sorted(anchors)
n_anchors = len(anchor_list)

dist_matrix = np.zeros((n_anchors, n_anchors))
for i, a in enumerate(anchor_list):
    for j, b in enumerate(anchor_list):
        if i == j:
            dist_matrix[i, j] = 0.0
        elif j < i:
            dist_matrix[i, j] = dist_matrix[j, i]
        else:
            dist_matrix[i, j] = anchor_distance(a, b)

print("\nAnchor distance matrix:")
for i, a in enumerate(anchor_list):
    row = "  ".join(f"{dist_matrix[i, j]:5.1f}" for j in range(n_anchors))
    print(f"  {a:24s}  {row}")


# ---------- CLASSICAL MDS ----------
def classical_mds(dist_matrix, dims=3):
    """
    Classical multidimensional scaling.
    Input:  n x n distance matrix
    Output: n x dims coordinate array, centered
    """
    n = dist_matrix.shape[0]
    # Square the distances
    D2 = dist_matrix ** 2
    # Double centering
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ D2 @ J
    # Eigendecomposition
    eigvals, eigvecs = np.linalg.eigh(B)
    # Sort descending
    idx = np.argsort(eigvals)[::-1]
    eigvals = eigvals[idx]
    eigvecs = eigvecs[:, idx]
    # Take top `dims` components, clamp negatives to 0
    eigvals = np.maximum(eigvals[:dims], 1e-9)
    coords = eigvecs[:, :dims] * np.sqrt(eigvals)
    return coords


anchor_coords = classical_mds(dist_matrix, dims=3)

# Normalize to a sphere of radius ANCHOR_RADIUS
norms = np.linalg.norm(anchor_coords, axis=1, keepdims=True)
norms[norms == 0] = 1.0
anchor_coords = anchor_coords / norms * ANCHOR_RADIUS

anchor_positions = {name: anchor_coords[i] for i, name in enumerate(anchor_list)}


# ---------- SATELLITE PLACEMENT ----------
# For each anchor, find its direct satellites (hyponyms, part_meronyms,
# part_holonyms, hypernym) and place them on a shell around the anchor.

def classify_children(anchor_name):
    """Return list of (satellite_name, relation) connected to the anchor."""
    children = []
    for e in edges:
        if e["source"] == anchor_name and e["relation"] != "hypernym":
            children.append((e["target"], e["relation"]))
        elif e["target"] == anchor_name and e["relation"] == "hypernym":
            # anchor's own hypernym (parent) — treat as satellite
            children.append((e["source"], "parent"))
    return children


positions = {}

# Anchor positions
for name, pos in anchor_positions.items():
    positions[name] = {
        "x": float(pos[0]), "y": float(pos[1]), "z": float(pos[2]),
        "type": "anchor",
        "parent": None,
        "relation": None,
        "size": ANCHOR_SIZE,
    }

# Satellites
for anchor_name in anchor_list:
    children = classify_children(anchor_name)
    n_children = len(children)
    if n_children == 0:
        continue

    # Shell radius scaled by number of children (denser anchors get wider shells)
    shell_radius = SHELL_MIN + (SHELL_MAX - SHELL_MIN) * min(n_children / 25.0, 1.0)

    anchor_pos = anchor_positions[anchor_name]
    anchor_dir = anchor_pos / np.linalg.norm(anchor_pos)

    # Build a local frame: anchor direction is the pole, two tangents span the shell
    up = np.array([0.0, 1.0, 0.0])
    if abs(np.dot(anchor_dir, up)) > 0.95:
        up = np.array([1.0, 0.0, 0.0])
    tangent_a = np.cross(anchor_dir, up)
    tangent_a /= np.linalg.norm(tangent_a)
    tangent_b = np.cross(anchor_dir, tangent_a)

    for k, (sat_name, relation) in enumerate(children):
        # Distribute satellites on a ring around the anchor direction
        theta = (k / max(n_children, 1)) * 2 * math.pi
        # Slight radial wobble so they aren't perfectly coplanar
        radial = shell_radius * (0.85 + 0.15 * math.sin(k * 2.399))  # golden-angle-ish
        offset = (
            tangent_a * math.cos(theta) * radial
            + tangent_b * math.sin(theta) * radial
        )
        pos = anchor_pos + offset
        positions[sat_name] = {
            "x": float(pos[0]), "y": float(pos[1]), "z": float(pos[2]),
            "type": "satellite",
            "parent": anchor_name,
            "relation": relation,
            "size": SAT_RADIUS,
        }


# ---------- ANY NODES LEFT OVER? ----------
# Satellites that weren't reached directly (e.g., hyponyms of satellites)
# get placed near their parent using edge traversal.
unplaced = set(nodes.keys()) - set(positions.keys())
iterations = 0
while unplaced and iterations < 5:
    iterations += 1
    placed_now = []
    for name in unplaced:
        # Find any edge linking this node to a placed node
        for e in edges:
            if e["source"] == name and e["target"] in positions:
                parent_pos = np.array([
                    positions[e["target"]]["x"],
                    positions[e["target"]]["y"],
                    positions[e["target"]]["z"],
                ])
                direction = parent_pos / np.linalg.norm(parent_pos)
                pos = parent_pos + direction * 0.4
                positions[name] = {
                    "x": float(pos[0]), "y": float(pos[1]), "z": float(pos[2]),
                    "type": "satellite",
                    "parent": e["target"],
                    "relation": e["relation"],
                    "size": SAT_RADIUS * 0.8,
                }
                placed_now.append(name)
                break
            elif e["target"] == name and e["source"] in positions:
                parent_pos = np.array([
                    positions[e["source"]]["x"],
                    positions[e["source"]]["y"],
                    positions[e["source"]]["z"],
                ])
                direction = parent_pos / np.linalg.norm(parent_pos)
                pos = parent_pos + direction * 0.4
                positions[name] = {
                    "x": float(pos[0]), "y": float(pos[1]), "z": float(pos[2]),
                    "type": "satellite",
                    "parent": e["source"],
                    "relation": e["relation"],
                    "size": SAT_RADIUS * 0.8,
                }
                placed_now.append(name)
                break
    for name in placed_now:
        unplaced.discard(name)

if unplaced:
    print(f"\nWarning: {len(unplaced)} nodes could not be placed: {sorted(unplaced)}")


# ---------- WRITE OUTPUT ----------
layout_out = {
    "word": "circuit",
    "anchor_radius": ANCHOR_RADIUS,
    "anchors": sorted(anchor_list),
    "node_count": len(positions),
    "nodes": [
        {
            "name": name,
            "x": positions[name]["x"],
            "y": positions[name]["y"],
            "z": positions[name]["z"],
            "type": positions[name]["type"],
            "parent": positions[name]["parent"],
            "relation": positions[name]["relation"],
            "size": positions[name]["size"],
        }
        for name in nodes.keys()
        if name in positions
    ],
}

with open(DATA_DIR / "circuit-layout.json", "w") as f:
    json.dump(layout_out, f, indent=2)

print(f"\nWrote {DATA_DIR / 'circuit-layout.json'}")
print(f"  Placed {len(positions)} of {len(nodes)} nodes")
print(f"  Anchors: {len(anchor_list)}")
print(f"  Satellites: {len(positions) - len(anchor_list)}")