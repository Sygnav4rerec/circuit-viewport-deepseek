// sphere.js — the Three.js scene for the circuit semantic sphere.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { ANCHOR_COLORS, DEFAULT_COLOR } from './colors.js';
import { ETYMOLOGY } from './table.js';

// Wait for main.js to provide data
const waitForData = () => new Promise(resolve => {
  const check = () => {
    if (window.__CIRCUIT_DATA__) return resolve(window.__CIRCUIT_DATA__);
    setTimeout(check, 50);
  };
  check();
});

const { layout, graph } = await waitForData();

const nodeByName = new Map();
layout.nodes.forEach(n => nodeByName.set(n.name, n));

const graphNodeByName = new Map();
graph.nodes.forEach(n => graphNodeByName.set(n.name, n));

const anchors = new Set(layout.anchors);

// Map: node name → which anchor it belongs to
const anchorOf = new Map();
layout.anchors.forEach(a => anchorOf.set(a, a));
layout.nodes.forEach(n => {
  if (n.type === 'satellite' && n.parent) {
    let cur = n.parent;
    const seen = new Set();
    while (cur && !anchors.has(cur) && !seen.has(cur)) {
      seen.add(cur);
      const pn = nodeByName.get(cur);
      cur = pn ? pn.parent : null;
    }
    if (cur && anchors.has(cur)) anchorOf.set(n.name, cur);
  }
});

function colorFor(nodeName) {
  const anchor = anchorOf.get(nodeName);
  return anchor ? (ANCHOR_COLORS[anchor] || DEFAULT_COLOR) : DEFAULT_COLOR;
}

// ── Scene ──
const container = document.getElementById('canvas-container');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0a0c11);

const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 200);
camera.position.set(0, 0, 16);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(container.clientWidth, container.clientHeight);
container.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.06;
controls.rotateSpeed = 0.5;
controls.minDistance = 8;
controls.maxDistance = 30;
controls.enablePan = false;

// Reference sphere
const sphereGeo = new THREE.SphereGeometry(layout.anchor_radius, 48, 32);
const sphereMat = new THREE.MeshBasicMaterial({
  color: 0x1a3a2a, wireframe: true, transparent: true, opacity: 0.12,
});
scene.add(new THREE.Mesh(sphereGeo, sphereMat));

// ── Nodes ──
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const clickableNodes = [];
const nodeGroup = new THREE.Group();
scene.add(nodeGroup);

const nodeMeshes = new Map();

layout.nodes.forEach(node => {
  const isAnchor = node.type === 'anchor';
  const color = colorFor(node.name);

  const geo = new THREE.SphereGeometry(node.size, 16, 16);
  const mat = new THREE.MeshBasicMaterial({ color });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.set(node.x, node.y, node.z);
  mesh.userData = { name: node.name, isAnchor };
  nodeGroup.add(mesh);
  nodeMeshes.set(node.name, mesh);

  const haloGeo = new THREE.SphereGeometry(node.size * (isAnchor ? 3.0 : 2.0), 16, 16);
  const haloMat = new THREE.MeshBasicMaterial({
    color, transparent: true, opacity: isAnchor ? 0.22 : 0.10,
  });
  const halo = new THREE.Mesh(haloGeo, haloMat);
  halo.position.set(node.x, node.y, node.z);
  halo.userData = { name: node.name, isAnchor, isHalo: true };
  nodeGroup.add(halo);

  clickableNodes.push(mesh, halo);
});

// ── Edges ──
const edgeGroup = new THREE.Group();
scene.add(edgeGroup);

graph.edges.forEach(edge => {
  const a = nodeByName.get(edge.source);
  const b = nodeByName.get(edge.target);
  if (!a || !b) return;

  const start = new THREE.Vector3(a.x, a.y, a.z);
  const end = new THREE.Vector3(b.x, b.y, b.z);
  const mid = start.clone().add(end).multiplyScalar(0.5);
  const outward = mid.clone().normalize().multiplyScalar(0.15);
  mid.add(outward);

  const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
  const geo = new THREE.BufferGeometry().setFromPoints(curve.getPoints(20));

  const colorA = colorFor(edge.source);
  const colorB = colorFor(edge.target);
  const blended = new THREE.Color(colorA).lerp(new THREE.Color(colorB), 0.5);
  blended.multiplyScalar(0.4);

  const mat = new THREE.LineBasicMaterial({ color: blended, transparent: true, opacity: 0.55 });
  edgeGroup.add(new THREE.Line(geo, mat));
});

// ── Anchor labels ──
function makeLabelSprite(text, color) {
  const canvas = document.createElement('canvas');
  const padding = 16;
  const fontSize = 36;
  const ctx = canvas.getContext('2d');
  ctx.font = `600 ${fontSize}px "IBM Plex Mono", monospace`;
  const metrics = ctx.measureText(text);
  canvas.width = Math.ceil(metrics.width + padding * 2);
  canvas.height = fontSize + padding * 2;

  const ctx2 = canvas.getContext('2d');
  ctx2.font = `600 ${fontSize}px "IBM Plex Mono", monospace`;
  ctx2.fillStyle = '#' + color.toString(16).padStart(6, '0');
  ctx2.textAlign = 'center';
  ctx2.textBaseline = 'middle';
  ctx2.shadowColor = '#' + color.toString(16).padStart(6, '0');
  ctx2.shadowBlur = 14;
  ctx2.fillText(text, canvas.width / 2, canvas.height / 2);

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;

  const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false });
  const sprite = new THREE.Sprite(material);
  const scale = 0.005;
  sprite.scale.set(canvas.width * scale, canvas.height * scale, 1);
  return sprite;
}

// Short, non-truncated label per anchor
const ANCHOR_LABELS = {
  'circuit.n.01':        'electrical',
  'tour.n.01':           'travel',
  'circuit.n.03':        'itinerary',
  'circumference.n.02':  'geometric',
  'circuit.n.05':        'legal',
  'racing_circuit.n.01': 'racing',
  'lap.n.05':            'motion',
};

layout.anchors.forEach(name => {
  const node = nodeByName.get(name);
  const color = colorFor(name);
  const labelText = ANCHOR_LABELS[name] || name.replace(/\.n\.\d+$/, '').replace(/_/g, ' ');
  const sprite = makeLabelSprite(labelText, color);
  const dir = new THREE.Vector3(node.x, node.y, node.z).normalize();
  sprite.position.set(
    node.x + dir.x * 0.7,
    node.y + dir.y * 0.7,
    node.z + dir.z * 0.7
  );
  scene.add(sprite);
});

// ── Info panel ──
const panel = document.getElementById('info-panel');
const infoSymbol = document.getElementById('info-symbol');
const infoName = document.getElementById('info-name');
const infoTagline = document.getElementById('info-tagline');
const infoPhysical = document.getElementById('info-physical');
const infoAtomic = document.getElementById('info-atomic');
const infoDescription = document.getElementById('info-description');
const infoUses = document.getElementById('info-uses');
const infoPosition = document.getElementById('info-position');

document.getElementById('close-panel')?.addEventListener('click', () => {
  panel.classList.remove('visible');
});

function row(label, value) {
  return `<div class="info-row"><span class="info-label">${label}</span><span class="info-value">${value ?? '—'}</span></div>`;
}

function showInfo(name) {
  const gn = graphNodeByName.get(name);
  const ln = nodeByName.get(name);
  if (!gn || !ln) return;

  const color = '#' + colorFor(name).toString(16).padStart(6, '0');
  const displayName = name.replace(/\.n\.\d+$/, '').replace(/_/g, ' ');

  infoSymbol.textContent = displayName.charAt(0).toUpperCase();
  infoSymbol.style.color = color;
  infoName.textContent = displayName;
  infoTagline.textContent = `${name} · ${ln.type}`;

  const parentLabel = ln.parent ? ln.parent.replace(/\.n\.\d+$/, '').replace(/_/g, ' ') : '—';
  infoPhysical.innerHTML =
    row('Type', ln.type) +
    row('Parent', parentLabel) +
    row('Relation', ln.relation || '—') +
    row('Lemma', (gn.lemmas || []).slice(0, 3).join(', '));

  infoAtomic.innerHTML =
    row('Hypernyms', (gn.hypernyms || []).length) +
    row('Hyponyms', (gn.hyponyms || []).length) +
    row('Part-of', (gn.part_holonyms || []).length) +
    row('Has parts', (gn.part_meronyms || []).length);

  infoDescription.textContent = gn.definition || '—';

  const related = [
    ...(gn.hypernyms || []).slice(0, 4),
    ...(gn.hyponyms || []).slice(0, 6),
  ].map(s => s.replace(/\.n\.\d+$/, '').replace(/_/g, ' ')).join(' · ');
  infoUses.textContent = related || '—';

  infoPosition.innerHTML =
    row('X', ln.x.toFixed(2)) +
    row('Y', ln.y.toFixed(2)) +
    row('Z', ln.z.toFixed(2));

  panel?.classList.add('visible');

  // Dispatch selection so table can highlight the matching anchor
  const owningAnchor = anchors.has(name) ? name : anchorOf.get(name);
  document.dispatchEvent(new CustomEvent('anchor-selected', {
    detail: { name: owningAnchor, nodeAnchor: owningAnchor, from: 'sphere' }
  }));
}

renderer.domElement.addEventListener('click', (event) => {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);

  const hits = raycaster.intersectObjects(clickableNodes);
  if (hits.length > 0) {
    showInfo(hits[0].object.userData.name);
  }
});

window.addEventListener('resize', () => {
  const w = container.clientWidth;
  const h = container.clientHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
});

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}
animate();