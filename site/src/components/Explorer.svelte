<script lang="ts">
  import { onMount } from 'svelte';
  import { flip } from 'svelte/animate';
  import { prefersReducedMotion } from 'svelte/motion';
  import Badges from './Badges.svelte';
  import PlugToggle from './PlugToggle.svelte';
  import { DEFAULT_W, inr, isDefault, meta, plugLabel, rankPlug, type Weights } from '../lib/data';
  import { MAX_COMPARE, readHash, toggleCompare, ui, writeHash } from '../lib/state.svelte';

  const AV = [
    { k: 'i', v: 'In stock', label: 'In stock' },
    { k: 'r', v: 'Sold out, restocking signs', label: 'Sold out, restocking signs' },
    { k: 'u', v: 'Sold out, status unclear', label: 'Sold out, status unclear' },
  ];
  const MS = [
    { k: 'm', v: 'measured', label: 'Measured' },
    { k: 'p', v: 'proxy', label: 'Proxy (base model measured)' },
    { k: 'b', v: 'buyer_beware', label: 'Buyer beware (not measured)' },
  ];
  const SORTS = [
    { k: 'score', label: 'Score, high to low' },
    { k: 'price', label: 'Price, low to high' },
    { k: 'price_desc', label: 'Price, high to low' },
    { k: 'value', label: 'Value, high to low' },
  ];
  const PRESETS: { label: string; w: Weights }[] = [
    { label: 'Default', w: { ...DEFAULT_W } },
    { label: 'Sound only', w: { sound: 100, hardware: 0, box: 0 } },
    { label: 'Equal thirds', w: { sound: 34, hardware: 33, box: 33 } },
    { label: 'Kit first', w: { sound: 30, hardware: 40, box: 30 } },
  ];
  const WKEYS = [
    { k: 'sound', label: 'Sound' },
    { k: 'hardware', label: 'Hardware' },
    { k: 'box', label: 'In the box' },
  ] as const;
  const PRICE_MAX = 10000;
  const PAGE = 40;

  let q = $state('');
  let min = $state(0);
  let max = $state(PRICE_MAX);
  let av = $state<Record<string, boolean>>({ i: true, r: true, u: true });
  let ms = $state<Record<string, boolean>>({ m: true, p: true, b: true });
  let sort = $state('score');
  let limit = $state(PAGE);
  let ready = $state(false);
  let filtersOpen = $state(false);

  const w = $derived(ui.weights);
  const ranked = $derived(rankPlug(ui.plug, w));
  const avSet = $derived(new Set(AV.filter((a) => av[a.k]).map((a) => a.v)));
  const msSet = $derived(new Set(MS.filter((m) => ms[m.k]).map((m) => m.v)));
  const needle = $derived(q.trim().toLowerCase());

  const filtered = $derived(
    ranked.filter(
      ({ i }) =>
        i.price_inr >= min &&
        i.price_inr <= max &&
        avSet.has(i.availability) &&
        msSet.has(i.measurement_status) &&
        (!needle || i.name.toLowerCase().includes(needle) || i.brand.toLowerCase().includes(needle)),
    ),
  );
  const sorted = $derived.by(() => {
    if (sort === 'score') return filtered;
    const rows = [...filtered];
    if (sort === 'price') rows.sort((a, b) => a.i.price_inr - b.i.price_inr || a.rank - b.rank);
    else if (sort === 'price_desc') rows.sort((a, b) => b.i.price_inr - a.i.price_inr || a.rank - b.rank);
    else rows.sort((a, b) => (b.i.value_score ?? -1e9) - (a.i.value_score ?? -1e9) || a.rank - b.rank);
    return rows;
  });
  const visible = $derived(sorted.slice(0, limit));
  const custom = $derived(!isDefault(w));
  const keptTop20 = $derived(ranked.slice(0, 20).filter((r) => r.i.rank_default <= 20).length);
  const activeFilters = $derived(
    (min > 0 || max < PRICE_MAX ? 1 : 0) + AV.filter((a) => !av[a.k]).length + MS.filter((m) => !ms[m.k]).length,
  );

  function setW(k: keyof Weights, v: number) {
    const others = (['sound', 'hardware', 'box'] as const).filter((x) => x !== k);
    const rest = 100 - v;
    const sum = w[others[0]] + w[others[1]];
    const a = sum === 0 ? Math.round(rest / 2) : Math.round((rest * w[others[0]]) / sum);
    ui.weights = { ...w, [k]: v, [others[0]]: a, [others[1]]: rest - a } as Weights;
  }

  function reset() {
    q = '';
    min = 0;
    max = PRICE_MAX;
    av = { i: true, r: true, u: true };
    ms = { m: true, p: true, b: true };
  }

  onMount(() => {
    const h = readHash();
    if (h.get('p') === 'c') ui.plug = 'Type-C';
    if (h.get('p') === '35') ui.plug = '3.5mm';
    q = h.get('q') ?? '';
    const n = (k: string, d: number) => {
      const v = Number(h.get(k));
      return h.has(k) && Number.isFinite(v) ? Math.max(0, Math.min(PRICE_MAX, v)) : d;
    };
    min = n('min', 0);
    max = n('max', PRICE_MAX);
    if (h.has('av')) for (const a of AV) av[a.k] = h.get('av')!.includes(a.k);
    if (h.has('ms')) for (const m of MS) ms[m.k] = h.get('ms')!.includes(m.k);
    if (SORTS.some((s) => s.k === h.get('s'))) sort = h.get('s')!;
    const ww = (h.get('w') ?? '').split('-').map(Number);
    if (ww.length === 3 && ww.every((x) => Number.isInteger(x) && x >= 0) && ww[0] + ww[1] + ww[2] === 100)
      ui.weights = { sound: ww[0], hardware: ww[1], box: ww[2] };
    filtersOpen = activeFilters > 0 || matchMedia('(min-width: 900px)').matches;
    ready = true;
  });

  $effect(() => {
    const patch = {
      p: ui.plug === 'Type-C' ? 'c' : null,
      q: q.trim() || null,
      min: min > 0 ? String(min) : null,
      max: max < PRICE_MAX ? String(max) : null,
      av: AV.every((a) => av[a.k]) ? null : AV.filter((a) => av[a.k]).map((a) => a.k).join(''),
      ms: MS.every((m) => ms[m.k]) ? null : MS.filter((m) => ms[m.k]).map((m) => m.k).join(''),
      s: sort === 'score' ? null : sort,
      w: custom ? `${w.sound}-${w.hardware}-${w.box}` : null,
    };
    if (ready) writeHash(patch);
  });

  let copied = $state(false);
  async function share() {
    try {
      await navigator.clipboard.writeText(location.href);
      copied = true;
      setTimeout(() => (copied = false), 1800);
    } catch {}
  }
</script>

<div class="explorer">
  <div class="side">
    <div class="row1">
      <PlugToggle />
      <label class="search">
        <span class="sr-only">Search by name or brand</span>
        <input type="search" placeholder="Search name or brand" bind:value={q} />
      </label>
    </div>

    <section class="weights card" aria-labelledby="w-title">
      <div class="whead">
        <h2 id="w-title">Make your own ranking</h2>
        <button class="linkbtn" type="button" disabled={!custom} onclick={() => (ui.weights = { ...DEFAULT_W })}>Reset</button>
      </div>
      {#each WKEYS as { k, label }}
        <div class="slider {k}">
          <label for="w-{k}">{label}</label>
          <input
            id="w-{k}"
            type="range"
            min="0"
            max="100"
            step="1"
            value={w[k]}
            oninput={(e) => setW(k, +e.currentTarget.value)}
          />
          <output for="w-{k}">{w[k]}</output>
        </div>
      {/each}
      <div class="presets">
        {#each PRESETS as p}
          <button
            type="button"
            class="chip"
            aria-pressed={p.w.sound === w.sound && p.w.hardware === w.hardware && p.w.box === w.box}
            onclick={() => (ui.weights = { ...p.w })}>{p.label}</button
          >
        {/each}
      </div>
      <p class="finding small" class:idle={!custom} aria-live="polite">
        {#if custom}
          <strong>{keptTop20} of the default top 20</strong> are still in your top 20.
        {:else}
          The three always add up to 100. Move one and watch what moves.
        {/if}
      </p>
    </section>

    <details class="filters card" bind:open={filtersOpen}>
      <summary>Filters{#if activeFilters}<span class="count">{activeFilters} on</span>{/if}</summary>
      <div class="fbody">
        <fieldset>
          <legend>Price</legend>
          <div class="slider plain">
            <label for="f-min">From</label>
            <input id="f-min" type="range" min="0" max={PRICE_MAX} step="100" bind:value={min} oninput={() => (max = Math.max(max, min))} />
            <output for="f-min">{inr(min)}</output>
          </div>
          <div class="slider plain">
            <label for="f-max">Up to</label>
            <input id="f-max" type="range" min="0" max={PRICE_MAX} step="100" bind:value={max} oninput={() => (min = Math.min(min, max))} />
            <output for="f-max">{inr(max)}</output>
          </div>
        </fieldset>
        <fieldset>
          <legend>Availability</legend>
          {#each AV as a}
            <label class="check"><input type="checkbox" bind:checked={av[a.k]} /> {a.label}</label>
          {/each}
        </fieldset>
        <fieldset>
          <legend>Measurement</legend>
          {#each MS as m}
            <label class="check"><input type="checkbox" bind:checked={ms[m.k]} /> {m.label}</label>
          {/each}
        </fieldset>
        <button class="linkbtn" type="button" onclick={reset}>Clear filters</button>
      </div>
    </details>

    <div class="notes">
      <p class="note small"><strong>Scores are fuzzy.</strong> {meta.disclaimers[1]} A gap of a point or two is a tie.</p>
      <p class="note teal small">
        <strong>Like less bass?</strong> In the Harman research, {meta.key_numbers.harman_listener_split}. If that is you,
        favour IEMs with a slightly positive tilt. Each IEM's tilt is in its details.
      </p>
    </div>
  </div>

  <div class="main">
    <div class="listhead">
      <p aria-live="polite">
        <strong>{sorted.length}</strong> of {ranked.length}
        {plugLabel(ui.plug)} IEMs
      </p>
      <label class="sort">
        <span>Sort</span>
        <select bind:value={sort}>
          {#each SORTS as s}<option value={s.k}>{s.label}</option>{/each}
        </select>
      </label>
      <button class="linkbtn" type="button" onclick={share}>{copied ? 'Link copied' : 'Copy link to this view'}</button>
    </div>
    {#if sort === 'value'}
      <p class="small muted">Value is {meta.formulas.value_score}. It uses the default weights. IEMs without a value go last.</p>
    {/if}
    <ul class="key small" aria-label="What the score bar shows">
      <li><i class="sw sound"></i>Sound</li>
      <li><i class="sw hardware"></i>Hardware</li>
      <li><i class="sw box"></i>In the box</li>
      <li class="muted">Rank is within {plugLabel(ui.plug)}; filters hide rows but never change ranks.</li>
    </ul>

    {#if visible.length}
      <ol class="list">
        {#each visible as r (r.i.id)}
          {@const d = r.i.rank_default - r.rank}
          {@const inCmp = ui.compare.includes(r.i.id)}
          <li animate:flip={{ duration: prefersReducedMotion.current ? 0 : 420 }} class:moved={custom && d !== 0}>
            <div class="rank">
              <span class="num"><span class="sr-only">Rank </span>{r.rank}</span>
              {#if custom && d !== 0}
                <span class="delta" class:up={d > 0}>
                  <span aria-hidden="true">{d > 0 ? '▲' : '▼'}</span>
                  <span class="sr-only">{d > 0 ? 'up' : 'down'}</span>
                  {Math.abs(d)}
                </span>
              {/if}
            </div>
            <button class="open" type="button" onclick={() => (ui.detail = r.i.id)}>
              <span class="name">{r.i.name}</span>
              <span class="meta">
                <b>{inr(r.i.price_inr)}</b>
                {#if sort === 'value' && r.i.value_score != null}<span class="badge">value {r.i.value_score}</span>{/if}
                <Badges iem={r.i} />
              </span>
              <span class="bar" aria-hidden="true">
                <i class="sound" style="width:{w.sound * r.i.parts.sound_frac}%"></i>
                <i class="hardware" style="width:{w.hardware * r.i.parts.hardware_frac}%"></i>
                <i class="box" style="width:{w.box * r.i.parts.box_frac}%"></i>
              </span>
            </button>
            <div class="right">
              <span class="score"><span class="sr-only">Score </span>{r.s.toFixed(1)}</span>
              <button
                class="cmp"
                type="button"
                aria-pressed={inCmp}
                disabled={!inCmp && ui.compare.length >= MAX_COMPARE}
                aria-label="{inCmp ? 'Remove' : 'Add'} {r.i.name} {inCmp ? 'from' : 'to'} compare"
                onclick={() => toggleCompare(r.i.id)}
              >
                {inCmp ? '✓ Comparing' : '+ Compare'}
              </button>
            </div>
          </li>
        {/each}
      </ol>
      {#if sorted.length > limit}
        <p class="more">
          <button class="btn ghost" type="button" onclick={() => (limit += PAGE)}>
            Show {Math.min(PAGE, sorted.length - limit)} more
          </button>
          <span class="muted small">Showing {limit} of {sorted.length}</span>
        </p>
      {/if}
    {:else}
      <p class="note">Nothing matches. <button class="linkbtn" type="button" onclick={reset}>Clear the filters</button>.</p>
    {/if}
  </div>
</div>

<style>
  .explorer {
    display: grid;
    gap: 1rem;
  }
  .side {
    display: contents;
  }
  .row1 {
    display: grid;
    gap: 0.6rem;
  }
  .search input {
    width: 100%;
    min-height: 2.75rem;
    padding: 0 1rem;
    border-radius: 999px;
    border: 1px solid var(--line);
    background: var(--surface);
  }
  .weights {
    position: sticky;
    top: 3.5rem;
    z-index: 20;
    padding: 0.6rem 0.8rem 0.5rem;
    background: var(--raised);
    box-shadow: var(--shadow);
  }
  .whead {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
  }
  .weights h2 {
    font-size: 1.05rem;
    margin: 0 0 0.2rem;
  }
  .slider {
    display: grid;
    grid-template-columns: 5.2rem 1fr 2.4rem;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9rem;
  }
  .slider label {
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
  }
  .slider output {
    text-align: right;
    font-weight: 700;
  }
  .slider.plain {
    grid-template-columns: 3rem 1fr 4.2rem;
  }
  .slider.sound label::before,
  .slider.hardware label::before,
  .slider.box label::before,
  .sw {
    content: '';
    display: inline-block;
    flex: none;
    width: 0.7rem;
    height: 0.7rem;
    border-radius: 2px;
    background: var(--accent);
  }
  .slider.hardware label::before,
  .sw.hardware,
  .bar .hardware {
    background: repeating-linear-gradient(135deg, var(--teal) 0 3px, color-mix(in srgb, var(--teal) 50%, transparent) 3px 6px);
  }
  .slider.box label::before,
  .sw.box,
  .bar .box {
    background: var(--ink);
  }
  .presets {
    display: flex;
    gap: 0.3rem;
    overflow-x: auto;
    padding: 0.3rem 0 0.2rem;
    scrollbar-width: none;
  }
  .chip {
    flex: none;
    border: 1px solid var(--line);
    background: var(--surface);
    border-radius: 999px;
    padding: 0.25rem 0.7rem;
    min-height: 2rem;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--muted);
  }
  .chip[aria-pressed='true'] {
    background: var(--ink);
    border-color: var(--ink);
    color: var(--bg);
  }
  .finding {
    margin: 0.2rem 0 0;
    color: var(--muted);
  }
  .finding strong {
    color: var(--ink);
  }
  .linkbtn {
    border: 0;
    background: none;
    padding: 0.3rem 0;
    color: var(--accent-ink);
    text-decoration: underline;
    text-underline-offset: 0.18em;
    font-size: 0.875rem;
  }
  .linkbtn:disabled {
    opacity: 0.4;
    cursor: default;
  }
  .filters summary {
    padding: 0.7rem 0.9rem;
    font-weight: 600;
    cursor: pointer;
  }
  .count {
    margin-left: 0.5rem;
    font-size: 0.75rem;
    padding: 0.05rem 0.5rem;
    border-radius: 999px;
    background: var(--accent-soft);
    color: var(--accent-ink);
  }
  .fbody {
    display: grid;
    gap: 0.9rem;
    padding: 0 0.9rem 0.9rem;
  }
  fieldset {
    border: 0;
    padding: 0;
    margin: 0;
    min-width: 0;
  }
  legend {
    padding: 0;
    font-weight: 600;
    font-size: 0.85rem;
    color: var(--muted);
    margin-bottom: 0.2rem;
  }
  .check {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-height: 2.3rem;
    font-size: 0.92rem;
  }
  .notes {
    display: grid;
    gap: 0.6rem;
    order: 9;
  }
  .notes p {
    margin: 0;
  }
  .main {
    min-width: 0;
  }
  .listhead {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.3rem 1rem;
  }
  .listhead p {
    margin: 0;
    margin-right: auto;
  }
  .sort {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.875rem;
  }
  .sort select {
    min-height: 2.4rem;
    border-radius: 999px;
    border: 1px solid var(--line);
    background: var(--surface);
    padding: 0 0.7rem;
  }
  .key {
    list-style: none;
    display: flex;
    flex-wrap: wrap;
    gap: 0.2rem 0.9rem;
    padding: 0;
    margin: 0.5rem 0 0.6rem;
  }
  .key li {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
  }
  .list {
    list-style: none;
    padding: 0;
    margin: 0;
    border-top: 1px solid var(--line);
  }
  .list li {
    display: grid;
    grid-template-columns: 2.3rem 1fr auto;
    gap: 0.5rem;
    align-items: start;
    padding: 0.7rem 0;
    border-bottom: 1px solid var(--line);
    background: var(--bg);
  }
  .list li.moved {
    background: linear-gradient(90deg, var(--accent-soft), transparent 40%);
  }
  .rank {
    display: grid;
    justify-items: center;
    gap: 0.1rem;
    padding-top: 0.1rem;
  }
  .num {
    font-family: var(--display);
    font-size: 1.25rem;
    font-weight: 600;
    line-height: 1.1;
  }
  .delta {
    font-size: 0.7rem;
    font-weight: 700;
    color: var(--muted);
    white-space: nowrap;
  }
  .delta.up {
    color: var(--teal);
  }
  .open {
    display: grid;
    gap: 0.3rem;
    min-width: 0;
    border: 0;
    background: none;
    padding: 0;
    text-align: left;
  }
  .name {
    font-weight: 650;
    font-size: 1.02rem;
    line-height: 1.25;
  }
  .open:hover .name {
    text-decoration: underline;
    text-underline-offset: 0.18em;
  }
  .meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.25rem 0.4rem;
    font-size: 0.9rem;
  }
  .bar {
    display: flex;
    height: 0.5rem;
    border-radius: 999px;
    background: var(--grid);
    overflow: hidden;
    margin-top: 0.1rem;
  }
  .bar i {
    display: block;
    height: 100%;
    transition: width 0.35s ease;
  }
  .bar .sound {
    background: var(--accent);
  }
  .right {
    display: grid;
    justify-items: end;
    gap: 0.25rem;
  }
  .score {
    font-family: var(--display);
    font-size: 1.5rem;
    font-weight: 600;
    line-height: 1.1;
  }
  .cmp {
    border: 1px solid var(--line);
    background: var(--surface);
    border-radius: 999px;
    min-height: 2rem;
    padding: 0.15rem 0.6rem;
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap;
  }
  .cmp[aria-pressed='true'] {
    border-color: var(--teal);
    color: var(--teal);
  }
  .cmp:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  .more {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-top: 1.2rem;
  }
  @media (max-width: 899px) {
    .finding.idle {
      display: none;
    }
  }
  @media (min-width: 900px) {
    .explorer {
      grid-template-columns: 20rem 1fr;
      gap: 2.5rem;
      align-items: start;
    }
    .side {
      display: grid;
      gap: 1rem;
      position: sticky;
      top: 4.4rem;
      max-height: calc(100dvh - 5rem);
      overflow-y: auto;
      padding: 2px 4px 1rem 2px;
    }
    .weights {
      position: static;
      padding: 0.9rem 1rem;
      box-shadow: none;
      background: var(--surface);
    }
    .list li {
      grid-template-columns: 3rem 1fr auto;
      padding: 0.85rem 0.4rem 0.85rem 0;
    }
    .right {
      grid-auto-flow: column;
      align-items: center;
      gap: 1rem;
    }
    .right .score {
      order: 2;
      min-width: 3.6rem;
      text-align: right;
    }
  }
</style>
