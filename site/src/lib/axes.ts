// Everything that can go on an axis of the homepage canvas. Each axis says how to read a
// value off an IEM, which end is better, and the words used for its two ends.
import { inr, meta, type Iem } from './data';

export interface Axis {
  key: string;
  group: string;
  label: string;
  /** One plain sentence on what the number is. */
  help: string;
  get: (i: Iem) => number | null;
  /**
   * How values are spread along the axis. Most axes are not linear: the crowded end is
   * stretched and the outlier end squeezed, so a few extreme IEMs do not flatten the rest.
   */
  fwd?: (v: number) => number;
  inv?: (t: number) => number;
  /** Shown beside the axis name whenever the scale is not linear. */
  scaleNote?: string;
  /** Preferred tick values for a non-linear axis. */
  ticks?: number[];
  /** Which end is better. 'mid' means it is a matter of taste and the centre is the target. */
  better: 'low' | 'high' | 'mid';
  /** Fixed centre line. Without it, the median of the plotted IEMs is used. */
  split?: number;
  /** Axis end labels, low end first. */
  ends: [string, string];
  /** Words for the quadrant labels, low end first. */
  words: [string, string];
  fmt: (v: number) => string;
  tick?: (v: number) => string;
}

const signed = (v: number, d = 2) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d);
const one = (v: number) => v.toFixed(1);
const whole = (v: number) => String(Math.round(v));
// Scales. Each is a pair of functions, there and back.
const LOG = { fwd: Math.log, inv: Math.exp, scaleNote: 'log scale' };
/** For 0 to 100 scores where the crowd is near the top: log of the distance from the top. */
const TOP = 105;
const TOP_LOG = {
  fwd: (v: number) => -Math.log(TOP - v),
  inv: (t: number) => TOP - Math.exp(-t),
  scaleNote: 'log scale, stretched near the top',
};
/** For values either side of zero: log-like on both sides, straight through the middle. */
const SYM = 0.3;
const SYM_LOG = {
  fwd: (v: number) => Math.asinh(v / SYM),
  inv: (t: number) => Math.sinh(t) * SYM,
  scaleNote: 'log scale either side of the target',
};
/** For counts that start at zero. */
const COUNT_LOG = { fwd: (v: number) => Math.log(1 + v), inv: (t: number) => Math.exp(t) - 1, scaleNote: 'log scale' };
const SCORE_TICKS = [30, 40, 50, 60, 70, 75, 80, 85, 90, 95];
const DB_TICKS = [0.5, 0.75, 1, 1.5, 2, 3, 4, 5];

const kTick = (v: number) => (v >= 1000 ? `₹${+(v / 1000).toFixed(1)}k` : `₹${Math.round(v)}`);

export const AXES: Axis[] = [
  {
    key: 'price',
    group: 'Money',
    label: 'Price',
    help: `Lowest price found across the stores on ${meta.built}.`,
    get: (i) => i.price_inr,
    ...LOG,
    ticks: [500, 1000, 2000, 5000, 10000],
    better: 'low',
    ends: ['Cheaper', 'Pricier'],
    words: ['cheap', 'pricey'],
    fmt: inr,
    tick: kTick,
  },
  {
    key: 'value',
    group: 'Money',
    label: 'Value score',
    help: 'How far an IEM’s overall score runs ahead of its price. Only measured IEMs in the top half by score have one.',
    get: (i) => i.value_score,
    better: 'high',
    ends: ['Less value', 'More value'],
    words: ['less value', 'more value'],
    fmt: (v) => signed(v, 1),
  },
  {
    key: 'harman',
    group: 'Sound',
    label: 'Sound score (Harman)',
    help: 'Predicted listener preference from the measured frequency response. Higher is closer to the Harman target.',
    get: (i) => i.harman_score,
    ...TOP_LOG,
    ticks: SCORE_TICKS,
    better: 'high',
    ends: ['Further off target', 'Closer to target'],
    words: ['weaker sound', 'great sound'],
    fmt: one,
  },
  {
    key: 'tilt',
    group: 'Sound',
    label: 'Tone: warm to bright',
    help: 'Which way the sound leans from the target. Negative is warmer, with more bass. Positive is brighter, with more treble.',
    get: (i) => i.tilt_slope,
    ...SYM_LOG,
    ticks: [-1.5, -1, -0.5, -0.2, 0, 0.2, 0.5, 1, 1.5],
    better: 'mid',
    split: 0,
    ends: ['Warmer, more bass', 'Brighter, more treble'],
    words: ['warmer', 'brighter'],
    fmt: (v) => signed(v),
    tick: (v) => signed(v, Math.abs(v) < 1 && v % 0.5 ? 2 : 1),
  },
  {
    key: 'sd',
    group: 'Sound',
    label: 'Unevenness',
    help: 'How bumpy the response is around the target, in dB. Lower is smoother.',
    get: (i) => i.sd_db,
    ...LOG,
    ticks: DB_TICKS,
    better: 'low',
    ends: ['Smoother', 'Bumpier'],
    words: ['smooth', 'bumpy'],
    fmt: (v) => `${v.toFixed(2)} dB`,
    tick: one,
  },
  {
    key: 'err',
    group: 'Sound',
    label: 'Distance from the target',
    help: 'Average gap between the measured response and the Harman target, in dB. Lower is closer.',
    get: (i) => i.mean_error_db,
    ...LOG,
    ticks: DB_TICKS,
    better: 'low',
    ends: ['On target', 'Off target'],
    words: ['on target', 'off target'],
    fmt: (v) => `${v.toFixed(2)} dB`,
    tick: one,
  },
  {
    key: 'score',
    group: 'Whole package',
    label: 'Overall score',
    help: `Sound, hardware and box contents added up at the default weights (${meta.weights_default.sound} / ${meta.weights_default.hardware} / ${meta.weights_default.box}). Unmeasured IEMs are included, at a low fixed sound level.`,
    get: (i) => i.score_default,
    ...TOP_LOG,
    ticks: SCORE_TICKS,
    better: 'high',
    ends: ['Lower overall', 'Higher overall'],
    words: ['lower overall', 'higher overall'],
    fmt: one,
  },
  {
    key: 'hardware',
    group: 'Whole package',
    label: 'Hardware points',
    help: 'Share of hardware points: detachable cable, microphone, and easy to drive or a DSP app. As claimed by the store.',
    get: (i) => i.parts.hardware_frac * 100,
    better: 'high',
    ends: ['Less hardware', 'More hardware'],
    words: ['less hardware', 'more hardware'],
    fmt: (v) => `${whole(v)}%`,
  },
  {
    key: 'box',
    group: 'Whole package',
    label: 'In-the-box points',
    help: 'Share of box points: eartips, eartip variety, case, cable, adapter. As claimed by the store.',
    get: (i) => i.parts.box_frac * 100,
    better: 'high',
    ends: ['Less in the box', 'More in the box'],
    words: ['less in the box', 'more in the box'],
    fmt: (v) => `${whole(v)}%`,
  },
  {
    key: 'measurers',
    group: 'Trust',
    label: 'Independent measurers',
    help: 'How many independent people have published a measurement. More means the sound score is firmer.',
    get: (i) => i.n_measurers,
    ...COUNT_LOG,
    ticks: [0, 1, 2, 3, 5, 8, 12],
    better: 'high',
    ends: ['Fewer measurers', 'More measurers'],
    words: ['fewer measurers', 'more measurers'],
    fmt: whole,
  },
];

export const axisBy = new Map(AXES.map((a) => [a.key, a]));
export const AXIS_GROUPS = [...new Set(AXES.map((a) => a.group))].map((g) => ({
  group: g,
  axes: AXES.filter((a) => a.group === g),
}));

export const VIEWS = [
  { label: 'Price vs sound', x: 'price', y: 'harman' },
  { label: 'Warm vs bright', x: 'tilt', y: 'harman' },
  { label: 'Price vs overall', x: 'price', y: 'score' },
  { label: 'Trust vs sound', x: 'measurers', y: 'harman' },
];

/** Round tick values for a linear range. */
export function niceTicks(lo: number, hi: number, want = 6) {
  const span = hi - lo;
  if (!(span > 0)) return [];
  const raw = span / want;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw)!;
  const out: number[] = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(+v.toPrecision(12));
  return out;
}
