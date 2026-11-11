import { DEFAULT_W, type Plug, type Weights } from './data';

/** State shared by every island on a page: which plug, which weights, what is open. */
export const ui = $state({
  plug: '3.5mm' as Plug,
  weights: { ...DEFAULT_W } as Weights,
  detail: null as string | null,
  compare: [] as string[],
  compareOpen: false,
});

export const MAX_COMPARE = 3;

export function toggleCompare(id: string) {
  const at = ui.compare.indexOf(id);
  if (at >= 0) ui.compare.splice(at, 1);
  else if (ui.compare.length < MAX_COMPARE) ui.compare.push(id);
}

export function readHash() {
  return new URLSearchParams(location.hash.slice(1));
}

/** Merge params into the URL hash without adding history entries. */
export function writeHash(patch: Record<string, string | null>) {
  const p = readHash();
  for (const [k, v] of Object.entries(patch)) {
    if (v == null || v === '') p.delete(k);
    else p.set(k, v);
  }
  const s = p.toString().replace(/%2C/g, ',');
  const next = s ? '#' + s : location.pathname + location.search;
  if ((location.hash || '') !== (s ? '#' + s : '')) history.replaceState(null, '', next);
}
