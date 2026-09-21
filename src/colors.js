// colors.js — shared palette for anchors across sphere and table.

export const ANCHOR_COLORS = {
  'circuit.n.01':        0x4a8fc0,  // electrical — blue
  'tour.n.01':           0xd9a441,  // travel — amber
  'circuit.n.03':        0x5a9e8f,  // social itinerary — teal
  'circumference.n.02':  0xb05a8f,  // geometric — magenta
  'circuit.n.05':        0x8f5ab0,  // legal — purple
  'racing_circuit.n.01': 0xc0664f,  // motorsport — orange
  'lap.n.05':            0x8b8f5a,  // motion — olive
};

export const ANCHOR_COLORS_STR = Object.fromEntries(
  Object.entries(ANCHOR_COLORS).map(([k, v]) => [
    k,
    '#' + v.toString(16).padStart(6, '0'),
  ])
);

export const DEFAULT_COLOR = 0x888888;