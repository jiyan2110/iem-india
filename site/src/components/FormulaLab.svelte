<script lang="ts">
  // A hands-on version of the Harman formula and the margin of error.
  import { HARMAN, harman, iems, margin, median, PROXY_PENALTY, SOUND_SCALE, DEFAULT_W } from '../lib/data';

  const measured = iems.filter((i) => i.measurement_status === 'measured');
  const byScore = [...measured].sort((a, b) => b.harman_score! - a.harman_score!);
  const med = median(measured.map((i) => i.harman_score!));
  const examples = [
    { label: 'Highest scorer', i: byScore[0] },
    { label: 'A typical one', i: byScore.reduce((a, b) => (Math.abs(b.harman_score! - med) < Math.abs(a.harman_score! - med) ? b : a)) },
    { label: 'Lowest scorer', i: byScore[byScore.length - 1] },
  ];
  const lim = (k: 'sd_db' | 'mean_error_db') => Math.ceil(Math.max(...measured.map((i) => i[k]!)));
  const maxSd = lim('sd_db');
  const maxErr = lim('mean_error_db');
  const maxN = Math.max(...iems.map((i) => i.n_measurers));

  let sd = $state(examples[1].i.sd_db!);
  let slope = $state(examples[1].i.tilt_slope!);
  let err = $state(examples[1].i.mean_error_db!);
  let n = $state(examples[1].i.n_measurers);
  let name = $state<string | null>(examples[1].i.name);

  const pSd = $derived(HARMAN.sd * sd);
  const pSlope = $derived(HARMAN.slope * Math.abs(slope));
  const pErr = $derived(HARMAN.err * err);
  const raw = $derived(harman(sd, slope, err));
  const moe = $derived(margin(n));
  const adj = $derived(raw - moe);
  const frac = $derived(Math.max(0, Math.min(1, (adj - SOUND_SCALE.lo) / (SOUND_SCALE.hi - SOUND_SCALE.lo))));
  const pct = (v: number) => `${Math.max(0, (v / HARMAN.base) * 100)}%`;

  function load(i: (typeof iems)[number]) {
    sd = i.sd_db!;
    slope = i.tilt_slope!;
    err = i.mean_error_db!;
    n = i.n_measurers;
    name = i.name;
  }
  const touch = () => (name = null);
</script>

<div class="lab card">
  <div class="ex">
    <span class="small muted">Load a real IEM:</span>
    {#each examples as e}
      <button type="button" class="chip" aria-pressed={name === e.i.name} onclick={() => load(e.i)}>{e.label}</button>
    {/each}
  </div>
  <p class="small muted now" aria-live="polite">{name ? `Showing ${name}.` : 'Showing your own numbers.'}</p>

  <div class="bar" role="img" aria-label="Starting from {HARMAN.base}, unevenness removes {pSd.toFixed(1)}, tilt removes {pSlope.toFixed(1)}, distance from target removes {pErr.toFixed(1)}, leaving {raw.toFixed(1)}.">
    <i class="keep" style="width:{pct(raw)}"></i>
    <i class="p1" style="width:{pct(pSd)}"></i>
    <i class="p2" style="width:{pct(pSlope)}"></i>
    <i class="p3" style="width:{pct(pErr)}"></i>
  </div>

  <div class="rows">
    <div class="r">
      <label for="fl-sd"><i class="sw p1"></i>Unevenness (SD)</label>
      <input id="fl-sd" type="range" min="0.5" max={maxSd} step="0.01" bind:value={sd} oninput={touch} />
      <output>{sd.toFixed(2)} dB <b>−{pSd.toFixed(1)}</b></output>
    </div>
    <div class="r">
      <label for="fl-slope"><i class="sw p2"></i>Tilt (slope)</label>
      <input id="fl-slope" type="range" min="-2" max="2" step="0.01" bind:value={slope} oninput={touch} />
      <output>{slope > 0 ? '+' : slope < 0 ? '−' : ''}{Math.abs(slope).toFixed(2)} <b>−{pSlope.toFixed(1)}</b></output>
    </div>
    <div class="r">
      <label for="fl-err"><i class="sw p3"></i>Distance from target</label>
      <input id="fl-err" type="range" min="0.5" max={maxErr} step="0.01" bind:value={err} oninput={touch} />
      <output>{err.toFixed(2)} dB <b>−{pErr.toFixed(1)}</b></output>
    </div>
    <div class="r">
      <label for="fl-n">Independent measurers</label>
      <input id="fl-n" type="range" min="1" max={maxN} step="1" bind:value={n} oninput={touch} />
      <output>{n} <b>−{moe.toFixed(1)}</b></output>
    </div>
  </div>

  <dl class="sum">
    <div><dt>Harman score</dt><dd>{raw.toFixed(1)}</dd></div>
    <div><dt>After the margin of error</dt><dd>{adj.toFixed(1)}</dd></div>
    <div class="total"><dt>Sound points, out of {DEFAULT_W.sound}</dt><dd>{(frac * DEFAULT_W.sound).toFixed(1)}</dd></div>
  </dl>
  <p class="small muted">
    Sound points scale the adjusted score from {SOUND_SCALE.lo} (zero points) to {SOUND_SCALE.hi} (full points). A proxy
    measurement loses {PROXY_PENALTY} more.
  </p>
</div>

<style>
  .lab {
    padding: 1rem;
  }
  .ex {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.35rem;
  }
  .chip {
    border: 1px solid var(--line);
    background: var(--bg);
    border-radius: 999px;
    padding: 0.25rem 0.7rem;
    min-height: 2.1rem;
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--muted);
  }
  .chip[aria-pressed='true'] {
    background: var(--ink);
    border-color: var(--ink);
    color: var(--bg);
  }
  .now {
    margin: 0.4rem 0 0.7rem;
  }
  .bar {
    display: flex;
    height: 1.6rem;
    border-radius: 6px;
    overflow: hidden;
    background: var(--grid);
  }
  .bar i {
    display: block;
    height: 100%;
    transition: width 0.3s ease;
  }
  .keep {
    background: var(--accent);
  }
  .p1 {
    background: repeating-linear-gradient(135deg, var(--teal) 0 4px, transparent 4px 8px);
  }
  .p2 {
    background: repeating-linear-gradient(90deg, var(--ink) 0 2px, transparent 2px 6px);
  }
  .p3 {
    background: radial-gradient(var(--warn) 1.5px, transparent 2px) 0 0 / 7px 7px;
  }
  .sw {
    display: inline-block;
    width: 0.8rem;
    height: 0.8rem;
    border-radius: 2px;
    margin-right: 0.35rem;
    border: 1px solid var(--line);
    vertical-align: -1px;
  }
  .rows {
    display: grid;
    gap: 0.5rem;
    margin: 1rem 0;
  }
  .r {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 0 0.6rem;
    align-items: center;
    font-size: 0.9rem;
  }
  .r label {
    font-weight: 600;
  }
  .r input {
    grid-column: 1 / -1;
    grid-row: 2;
  }
  .r output b {
    display: inline-block;
    min-width: 2.8rem;
    text-align: right;
    color: var(--warn);
  }
  .sum {
    margin: 0 0 0.6rem;
  }
  .sum div {
    display: flex;
    justify-content: space-between;
    padding: 0.35rem 0;
    border-bottom: 1px solid var(--line);
  }
  .sum dd {
    margin: 0;
    font-weight: 700;
  }
  .sum .total dd {
    font-family: var(--display);
    font-size: 1.5rem;
    line-height: 1;
  }
  p:last-child {
    margin: 0;
  }
</style>
