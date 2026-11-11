// Single source of truth: everything on the site is read from data/*.json.
import raw from '../../data/iems.json';
import metaRaw from '../../data/meta.json';
import removedRaw from '../../data/removed.json';
import photosRaw from '../data/photos.json';

export type Plug = '3.5mm' | 'Type-C';
export type Status = 'measured' | 'proxy' | 'buyer_beware';
export type Tri = boolean | null;

export interface Iem {
  id: string;
  name: string;
  brand: string;
  plug: Plug;
  collab: boolean;
  price_inr: number;
  mrp_inr: number;
  cheapest_store: string;
  url: string;
  stores: string[];
  availability: string;
  availability_note: string;
  measurement_status: Status;
  harman_score: number | null;
  harman_adjusted: number;
  n_measurers: number;
  score_spread: number | null;
  sd_db: number | null;
  tilt_slope: number | null;
  mean_error_db: number | null;
  measurers: string[];
  parts: { sound_frac: number; hardware_frac: number; box_frac: number };
  score_default: number;
  rank_default: number;
  value_score: number | null;
  hardware: Record<string, Tri>;
  box: Record<string, Tri>;
  specs_as_claimed: Record<string, number | null>;
}

export interface Weights {
  sound: number;
  hardware: number;
  box: number;
}

// Two records in the source share one slug (CCA CRA and CCA CRA+). data/ is left untouched,
// so repeated ids get a numeric suffix here to stay unique for links, keys and compare.
const seen = new Map<string, number>();
export const iems = (raw as unknown as Iem[]).map((i) => {
  const n = (seen.get(i.id) ?? 0) + 1;
  seen.set(i.id, n);
  return n === 1 ? i : { ...i, id: `${i.id}-${n}` };
});
export const meta = metaRaw;
export const removed = removedRaw as {
  id: string;
  name: string;
  plug: string;
  availability_note: string;
  harman_score: number | null;
  price_inr: number;
}[];

// Product photo links, looked up from the store pages by scripts/fetch-photos.mjs.
// The image is served by the store; the site only links to it.
const photos = photosRaw as Record<string, string>;
export function photo(i: Iem, width = 320) {
  const src = photos[i.url];
  return src ? `${src}${src.includes('?') ? '&' : '?'}width=${width}` : null;
}

export const byId = new Map(iems.map((i) => [i.id, i]));
export const PLUGS: Plug[] = ['3.5mm', 'Type-C'];
export const plugLabel = (p: string) => (p === '3.5mm' ? '3.5 mm' : 'Type-C');
export const DEFAULT_W: Weights = { ...meta.weights_default };
export const VARIANCE = meta.key_numbers.between_measurer_variance;

export const STORE_NAMES: Record<string, string> = {
  headphonezone: 'Headphone Zone',
  theaudiostore: 'The Audio Store',
  conceptkart: 'Concept Kart',
};
export const storeName = (s: string) => STORE_NAMES[s] ?? s;

export const HARDWARE_LABELS: Record<string, string> = {
  detach: 'Detachable cable',
  mic: 'Microphone',
  drive: 'Easy to drive from a phone',
  dsp: 'DSP / EQ app',
};
export const BOX_LABELS: Record<string, string> = {
  tips: 'Eartips',
  tip_variety: 'More than one kind of eartip',
  case: 'Carry case',
  cable: 'Cable',
  adapter: 'Adapter',
};

export const inr = (n: number) => '₹' + Math.round(n).toLocaleString('en-IN');
export const f1 = (n: number | null | undefined) => (n == null ? 'n/a' : n.toFixed(1));

export function score(i: Iem, w: Weights) {
  return w.sound * i.parts.sound_frac + w.hardware * i.parts.hardware_frac + w.box * i.parts.box_frac;
}

export const isDefault = (w: Weights) =>
  w.sound === DEFAULT_W.sound && w.hardware === DEFAULT_W.hardware && w.box === DEFAULT_W.box;

/** Rank every IEM of one plug type under the given weights. Ties keep the default order. */
export function rankPlug(plug: Plug, w: Weights) {
  const rows = iems
    .filter((i) => i.plug === plug)
    .map((i) => ({ i, s: score(i, w) }))
    .sort((a, b) => b.s - a.s || a.i.rank_default - b.i.rank_default);
  return rows.map((r, k) => ({ ...r, rank: k + 1 }));
}

/** Margin of error taken off the Harman score: sqrt(variance / measurers). */
export const margin = (n: number) => Math.sqrt(VARIANCE / n);

export function tiltWord(t: number | null) {
  if (t == null) return 'Not measured';
  const a = Math.abs(t);
  if (a < 0.15) return 'Close to the target';
  const side = t < 0 ? 'warmer, more bass' : 'brighter, more treble';
  return (a < 0.5 ? 'Slightly ' : a < 1 ? 'Clearly ' : 'Much ') + side;
}

export const inStock = (i: Iem) => i.availability === 'In stock';

export function median(v: number[]) {
  const s = [...v].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/** IEMs that can be drawn on a Harman chart (measured or proxy). */
export const charted = (plug: Plug) => iems.filter((i) => i.plug === plug && i.harman_score != null);

/** A cheap, well-measured IEM and a pricey, poorly-measured one, for the headline. */
export function headlinePair(plug: Plug) {
  const m = charted(plug).filter((i) => i.measurement_status === 'measured');
  const pick = (minN: number, cheapMax: number) => {
    const solid = m.filter((i) => i.n_measurers >= minN);
    const cheap = solid
      .filter((i) => i.price_inr <= cheapMax && inStock(i))
      .sort((a, b) => b.harman_score! - a.harman_score!)[0];
    const pricey = solid.filter((i) => i.price_inr >= 7000).sort((a, b) => a.harman_score! - b.harman_score!)[0];
    return cheap && pricey ? { cheap, pricey } : null;
  };
  return pick(2, 1500) ?? pick(2, 2500) ?? pick(1, 2500)!;
}

export const PRICE_BANDS = [
  { label: 'Under ₹2,000', lo: 0, hi: 2000 },
  { label: '₹2,000 to ₹5,000', lo: 2000, hi: 5000 },
  { label: '₹5,000 to ₹10,000', lo: 5000, hi: 10001 },
];

export function bandStats(plug: Plug) {
  return PRICE_BANDS.map((b) => {
    const rows = charted(plug).filter((i) => i.price_inr >= b.lo && i.price_inr < b.hi);
    return { ...b, n: rows.length, median: rows.length ? median(rows.map((i) => i.harman_score!)) : null };
  });
}

/** R² of Harman score against log price for one plug, straight from meta.json. */
export function r2Text(plug: Plug) {
  const k = meta.key_numbers as Record<string, any>;
  const v = k.harman_vs_log_price_r2?.[plug];
  if (v == null) throw new Error('meta.json: harman_vs_log_price_r2 is missing for ' + plug);
  return String(v);
}

// Constants are parsed out of the formula text in meta.json so the site cannot drift from it.
function nums(text: string, re: RegExp, what: string) {
  const m = text.match(re);
  if (!m) throw new Error(`meta.json: could not read ${what}`);
  return m.slice(1).map(Number);
}
const [hBase, hSd, hSlope, hErr] = nums(
  meta.formulas.harman_score,
  /([\d.]+) - ([\d.]+)\*SD - ([\d.]+)\*\|slope\| - ([\d.]+)\*mean_abs_error/,
  'Harman coefficients',
);
export const HARMAN = { base: hBase, sd: hSd, slope: hSlope, err: hErr };
export const harman = (sd: number, slope: number, err: number) =>
  HARMAN.base - HARMAN.sd * sd - HARMAN.slope * Math.abs(slope) - HARMAN.err * err;
export const [PROXY_PENALTY] = nums(meta.formulas.harman_adjusted, /proxy -([\d.]+)/, 'proxy penalty');
export const [BEWARE_LEVEL] = nums(meta.formulas.harman_adjusted, /\(([\d.]+)\)\s*$/, 'buyer beware level');
const [sLo, sHi] = nums(meta.formulas.sound_frac, /harman_adjusted - ([\d.]+)\) \/ \(([\d.]+) -/, 'sound scale');
export const SOUND_SCALE = { lo: sLo, hi: sHi };
