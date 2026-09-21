# circuit-viewport-deepseek

A 3D semantic sphere for the word "circuit." Six meanings, six regions, one label. 
The gap between them is the point.

Live: https://circuit.vi5wport.xyz

## What this is

An experiment in mapping polysemy — one word, many locations. Built on WordNet's 
six `circuit` synsets, laid out on a navigable sphere. If the senses cluster 
cleanly, the concept scales to other words. If they blob, we rethink the layout.

## Structure

- `/src` — browser code (Three.js scene, layout, UI)
- `/data` — WordNet pulls, processed graphs
- `/scripts` — data fetch and processing (Python)
- `/notes` — timestamped experiment log

## Status

- [ ] WordNet pull for `circuit` synsets
- [ ] Graph processing (nodes + edges)
- [ ] Sphere layout
- [ ] UI + labels
- [ ] Deploy to subdomain

## Related

- Main site: https://sygnav4rerec.xyz
- Applied Conceptualist taxonomy