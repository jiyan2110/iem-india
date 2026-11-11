// One flat table of every IEM. The data page shows it and the CSV download is built from it,
// so the two can never disagree.
import { BOX_LABELS, HARDWARE_LABELS, iems, plugLabel, storeName, type Iem, type Tri } from './data';

export interface Column {
  key: string;
  label: string;
  get: (i: Iem) => string | number | null;
  /** Shown in the on-page table. Every column is in the CSV. */
  show?: boolean;
  num?: boolean;
  digits?: number;
}

const tri = (v: Tri | undefined) => (v === true ? 'yes' : v === false ? 'no' : null);
const hwKeys = [...new Set(iems.flatMap((i) => Object.keys(i.hardware)))];
const boxKeys = [...new Set(iems.flatMap((i) => Object.keys(i.box)))];
const specKeys = [...new Set(iems.flatMap((i) => Object.keys(i.specs_as_claimed)))];

export const COLUMNS: Column[] = [
  { key: 'name', label: 'IEM', get: (i) => i.name, show: true },
  { key: 'brand', label: 'Brand', get: (i) => i.brand },
  { key: 'plug', label: 'Plug', get: (i) => plugLabel(i.plug), show: true },
  { key: 'rank_default', label: 'Rank in its plug', get: (i) => i.rank_default, show: true, num: true },
  { key: 'score_default', label: 'Overall score', get: (i) => i.score_default, show: true, num: true, digits: 1 },
  { key: 'price_inr', label: 'Price ₹', get: (i) => i.price_inr, show: true, num: true },
  { key: 'mrp_inr', label: 'Store MRP ₹', get: (i) => i.mrp_inr, num: true },
  { key: 'availability', label: 'Availability', get: (i) => i.availability, show: true },
  { key: 'availability_note', label: 'Availability note', get: (i) => i.availability_note || null },
  { key: 'measurement_status', label: 'Measurement', get: (i) => i.measurement_status.replace('_', ' '), show: true },
  { key: 'n_measurers', label: 'Measurers', get: (i) => i.n_measurers, show: true, num: true },
  { key: 'harman_score', label: 'Sound score (Harman)', get: (i) => i.harman_score, show: true, num: true, digits: 1 },
  { key: 'harman_adjusted', label: 'Sound score after margin', get: (i) => i.harman_adjusted, show: true, num: true, digits: 1 },
  { key: 'score_spread', label: 'Spread between measurers', get: (i) => i.score_spread, num: true, digits: 1 },
  { key: 'tilt_slope', label: 'Tilt', get: (i) => i.tilt_slope, show: true, num: true, digits: 2 },
  { key: 'sd_db', label: 'Unevenness dB', get: (i) => i.sd_db, show: true, num: true, digits: 2 },
  { key: 'mean_error_db', label: 'Distance from target dB', get: (i) => i.mean_error_db, show: true, num: true, digits: 2 },
  { key: 'sound_frac', label: 'Sound share', get: (i) => i.parts.sound_frac, num: true, digits: 3 },
  { key: 'hardware_frac', label: 'Hardware share', get: (i) => i.parts.hardware_frac, show: true, num: true, digits: 2 },
  { key: 'box_frac', label: 'Box share', get: (i) => i.parts.box_frac, show: true, num: true, digits: 2 },
  { key: 'value_score', label: 'Value score', get: (i) => i.value_score, show: true, num: true, digits: 1 },
  { key: 'collab', label: 'Collab edition', get: (i) => (i.collab ? 'yes' : 'no') },
  ...hwKeys.map((k) => ({ key: `hardware_${k}`, label: `${HARDWARE_LABELS[k] ?? k} (claimed)`, get: (i: Iem) => tri(i.hardware[k]) })),
  ...boxKeys.map((k) => ({ key: `box_${k}`, label: `${BOX_LABELS[k] ?? k} (claimed)`, get: (i: Iem) => tri(i.box[k]) })),
  ...specKeys.map((k) => ({ key: `spec_${k}`, label: `${k} (claimed)`, get: (i: Iem) => i.specs_as_claimed[k] ?? null })),
  { key: 'measurers', label: 'Measured by', get: (i) => i.measurers.join(' ') || null },
  { key: 'cheapest_store', label: 'Cheapest store', get: (i) => storeName(i.cheapest_store), show: true },
  { key: 'stores', label: 'All stores', get: (i) => i.stores.map(storeName).join('; ') },
  { key: 'url', label: 'Store page', get: (i) => i.url },
  { key: 'id', label: 'id', get: (i) => i.id },
];

const cell = (v: string | number | null) => {
  if (v == null) return '';
  const s = String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

export function toCsv() {
  const head = COLUMNS.map((c) => cell(c.key)).join(',');
  const body = iems.map((i) => COLUMNS.map((c) => cell(c.get(i))).join(','));
  return [head, ...body].join('\n') + '\n';
}
