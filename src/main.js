// main.js — entry point. Fetch data first, then boot sphere and table.

async function boot() {
  const [layout, graph] = await Promise.all([
    fetch('./data/circuit-layout.json').then(r => {
      if (!r.ok) throw new Error(`layout: ${r.status}`);
      return r.json();
    }),
    fetch('./data/circuit-graph.json').then(r => {
      if (!r.ok) throw new Error(`graph: ${r.status}`);
      return r.json();
    }),
  ]);

  window.__CIRCUIT_DATA__ = { layout, graph };

  const { renderTable } = await import('./table.js');
  await import('./sphere.js');

  const tableEl = document.getElementById('table-section');
  if (tableEl) renderTable(tableEl, layout, graph);
}

boot().catch(err => {
  console.error('Boot failed:', err);
  const el = document.getElementById('canvas-container');
  if (el) {
    el.innerHTML = `<pre style="color:#d9a441;padding:40px;font-family:monospace;font-size:12px;white-space:pre-wrap;">Boot failed:\n${err.message}\n\nStack:\n${err.stack || '(none)'}\n\nOpen console for details.</pre>`;
  }
});