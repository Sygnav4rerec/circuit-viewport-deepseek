// table.js — the flat "concept table" below the sphere.
// Seven anchor blocks, one per meaning of "circuit."
// Click a block: highlight the anchor on the sphere.
// Click a node on the sphere: highlight the matching block here.

import { ANCHOR_COLORS_STR as ANCHOR_COLORS } from './colors.js';

// Etymology — one summary for the word as a whole.
// Shown in the table header and (optionally) in popups.
export const ETYMOLOGY = {
  word: 'circuit',
  latin: 'circuitus',
  literal: '"a going around"',
  components: [
    { form: 'circum', meaning: 'around' },
    { form: 'ire', meaning: 'to go' },
  ],
  summary:
    'From Latin circuitus, "a going around," formed from circum ("around") + ire ("to go"). Entered English in the 14th century via Old French, originally meaning a circular journey or a boundary line. The electrical sense was added in the 18th century, when the closed-loop path of current was recognized as a "circuit" in the original Latin sense. The legal sense — a judge\'s traveling route — dates from the 16th century.',
};

// Curated one-line label per anchor.
// These are how each meaning will be titled in the table.
const ANCHOR_LABELS = {
  'circuit.n.01':        'Electrical',
  'tour.n.01':           'Travel',
  'circuit.n.03':        'Social itinerary',
  'circumference.n.02':  'Geometric',
  'circuit.n.05':        'Legal',
  'racing_circuit.n.01': 'Motorsport',
  'lap.n.05':            'Motion',
};

// Order in the table. Dense anchors first, sparse ones after.
const ANCHOR_ORDER = [
  'circuit.n.01',
  'tour.n.01',
  'lap.n.05',
  'circuit.n.03',
  'racing_circuit.n.01',
  'circumference.n.02',
  'circuit.n.05',
];


export function renderTable(container, layout, graph) {
  container.innerHTML = '';

  const nodeByName = new Map();
  layout.nodes.forEach(n => nodeByName.set(n.name, n));

  const graphNodeByName = new Map();
  graph.nodes.forEach(n => graphNodeByName.set(n.name, n));

  // Count satellites per anchor (walk down parent chain)
  function countSatellites(anchorName) {
    let count = 0;
    layout.nodes.forEach(n => {
      if (n.type !== 'satellite') return;
      let cur = n.parent;
      const seen = new Set();
      while (cur && !seen.has(cur)) {
        if (cur === anchorName) { count++; break; }
        seen.add(cur);
        const pn = nodeByName.get(cur);
        cur = pn ? pn.parent : null;
      }
    });
    return count;
  }

  // ── HEADER ──
  const header = document.createElement('header');
  header.className = 'table-header';
   header.innerHTML = `
    <a href="#canvas-container" class="back-to-sphere">↑ back to sphere</a>
    <div class="table-word">circuit</div>
    <div class="table-etym">
      From Latin <em>${ETYMOLOGY.latin}</em> — ${ETYMOLOGY.literal}
      <span class="table-etym-detail">
        ${ETYMOLOGY.components.map(c => `${c.form} (“${c.meaning}”)`).join(' + ')}
      </span>
    </div>
    <div class="table-etym-full">${ETYMOLOGY.summary}</div>
  `;
  container.appendChild(header);

  // ── ANCHOR BLOCKS ──
  const grid = document.createElement('div');
  grid.className = 'table-grid';

  ANCHOR_ORDER.forEach(anchorName => {
    const node = nodeByName.get(anchorName);
    const gn = graphNodeByName.get(anchorName);
    if (!node || !gn) return;

    const color = ANCHOR_COLORS[anchorName] || '#888888';
    const label = ANCHOR_LABELS[anchorName] || anchorName;
    const satCount = countSatellites(anchorName);

    const block = document.createElement('div');
    block.className = 'table-block';
    block.dataset.anchor = anchorName;
    block.style.setProperty('--anchor-color', color);
    block.innerHTML = `
      <div class="block-bar"></div>
      <div class="block-head">
        <div class="block-label">${label}</div>
        <div class="block-synset">${anchorName}</div>
      </div>
      <div class="block-def">${gn.definition || '—'}</div>
      <div class="block-meta">
        <span class="block-count">${satCount} ${satCount === 1 ? 'related word' : 'related words'}</span>
      </div>
    `;

    block.addEventListener('click', () => {
      document.dispatchEvent(new CustomEvent('anchor-selected', {
        detail: { name: anchorName, from: 'table' }
      }));
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    grid.appendChild(block);
  });

  container.appendChild(grid);

  // ── SYNC: sphere → table ──
  document.addEventListener('anchor-selected', (e) => {
    const anchorName = e.detail?.name;
    // Highlight blocks whose anchor matches the selected node's anchor
    grid.querySelectorAll('.table-block').forEach(b => {
      const isMatch = b.dataset.anchor === anchorName ||
        // also match if the selected node is a satellite of this anchor
        (e.detail?.nodeAnchor && b.dataset.anchor === e.detail.nodeAnchor);
      b.classList.toggle('active', isMatch);
    });
  });
}