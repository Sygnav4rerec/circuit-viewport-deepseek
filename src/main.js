// main.js — entry point. Boots the sphere and the table.

import { renderTable } from './table.js';
import './sphere.js';

async function boot() {
  // Load both data files
  const [layout, graph] = await Promise.all([
    fetch('./data/circuit-layout.json').then(r => r.json()),
    fetch('./data/circuit-graph.json').then(r => r.json()),
  ]);

  // Render the table below the sphere
  const tableEl = document.getElementById('table-section');
  if (tableEl) renderTable(tableEl, layout, graph);

  // Make layout + graph globally available to sphere.js
  window.__CIRCUIT_DATA__ = { layout, graph };
}

boot();