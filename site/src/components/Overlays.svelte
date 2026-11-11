<script lang="ts">
  // The IEM detail sheet, the compare tray and the compare table. One copy per page.
  import { onMount } from 'svelte';
  import Badges from './Badges.svelte';
  import {
    BEWARE_LEVEL,
    BOX_LABELS,
    byId,
    f1,
    HARDWARE_LABELS,
    HARMAN,
    inr,
    margin,
    meta,
    photo,
    plugLabel,
    PROXY_PENALTY,
    rankPlug,
    score,
    storeName,
    tiltWord,
    type Iem,
    type Tri,
  } from '../lib/data';
  import { MAX_COMPARE, readHash, toggleCompare, ui, writeHash } from '../lib/state.svelte';

  let detailEl: HTMLDialogElement;
  let compareEl: HTMLDialogElement;
  let ready = $state(false);

  const iem = $derived(ui.detail ? (byId.get(ui.detail) ?? null) : null);
  const picked = $derived(ui.compare.map((id) => byId.get(id)).filter(Boolean) as Iem[]);
  const w = $derived(ui.weights);

  const rankOf = (i: Iem) => {
    const all = rankPlug(i.plug, w);
    return { rank: all.find((r) => r.i.id === i.id)!.rank, of: all.length };
  };
  const rank = $derived(iem ? rankOf(iem) : null);
  const parts = (i: Iem) => [
    { key: 'sound', label: 'Sound', frac: i.parts.sound_frac, w: w.sound },
    { key: 'hardware', label: 'Hardware', frac: i.parts.hardware_frac, w: w.hardware },
    { key: 'box', label: 'In the box', frac: i.parts.box_frac, w: w.box },
  ];
  const tri = (v: Tri) => (v === true ? 'Yes' : v === false ? 'No' : 'Not stated');
  const signed = (n: number) => (n > 0 ? '+' : n < 0 ? '−' : '') + Math.abs(n).toFixed(2);

  onMount(() => {
    const h = readHash();
    const id = h.get('iem');
    if (id && byId.has(id)) ui.detail = id;
    const c = (h.get('c') ?? '').split(',').filter((x) => byId.has(x));
    if (c.length) ui.compare = c.slice(0, MAX_COMPARE);
    ready = true;
  });

  $effect(() => {
    const d = ui.detail;
    const c = ui.compare.join(',');
    if (ready) writeHash({ iem: d, c });
  });

  $effect(() => {
    if (!detailEl) return;
    if (iem && !detailEl.open) detailEl.showModal();
    else if (!iem && detailEl.open) detailEl.close();
  });
  $effect(() => {
    if (!compareEl) return;
    const want = ui.compareOpen && picked.length >= 2;
    if (want && !compareEl.open) compareEl.showModal();
    else if (!want && compareEl.open) compareEl.close();
  });

  const best = (vals: (number | null)[], dir: 'max' | 'min') => {
    const v = vals.filter((x) => x != null) as number[];
    if (v.length < 2) return null;
    const b = dir === 'max' ? Math.max(...v) : Math.min(...v);
    return v.filter((x) => x === b).length === 1 ? b : null;
  };
  const hwKeys = $derived([...new Set(picked.flatMap((i) => Object.keys(i.hardware)))]);
</script>

{#snippet triCell(v: Tri)}
  <span class="tri" class:yes={v === true} class:no={v === false}>
    <svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true">
      {#if v === true}<path d="M2 6.5 5 9.5 10.5 3" fill="none" stroke="currentColor" stroke-width="1.8" />
      {:else if v === false}<path d="M3 3l6 6M9 3l-6 6" stroke="currentColor" stroke-width="1.6" />
      {:else}<circle cx="6" cy="6" r="4.3" fill="none" stroke="currentColor" stroke-width="1.3" stroke-dasharray="2 2" />{/if}
    </svg>
    {tri(v)}
  </span>
{/snippet}

<dialog
  class="sheet"
  bind:this={detailEl}
  aria-labelledby="detail-title"
  onclose={() => (ui.detail = null)}
  onclick={(e) => e.target === detailEl && (ui.detail = null)}
>
  {#if iem}
    <div class="inner">
      <header>
        <div>
          <p class="eyebrow">{plugLabel(iem.plug)} · rank {rank!.rank} of {rank!.of}</p>
          <h2 id="detail-title">{iem.name}</h2>
        </div>
        <button class="close" type="button" aria-label="Close details" onclick={() => (ui.detail = null)}>
          <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"
            ><path d="M3 3l10 10M13 3 3 13" stroke="currentColor" stroke-width="2" /></svg
          >
        </button>
      </header>

      {#if photo(iem)}
        {#key iem.id}
          <figure class="photo">
            <img
              src={photo(iem, 480)}
              alt="Product photo of {iem.name}"
              width="240"
              height="240"
              loading="lazy"
              onerror={(e) => ((e.currentTarget.parentElement as HTMLElement).style.display = 'none')}
            />
            <figcaption class="small muted">Photo: {storeName(iem.cheapest_store)}</figcaption>
          </figure>
        {/key}
      {/if}

      <p class="badges"><Badges {iem} /></p>
      {#if iem.availability_note}
        <p class="small muted">Why it is flagged: {iem.availability_note}.</p>
      {/if}
      {#if iem.availability === 'Sold out, status unclear'}
        <p class="small muted">{meta.disclaimers[2]}</p>
      {/if}

      <section class="buy card">
        <div>
          <span class="price">{inr(iem.price_inr)}</span>
          {#if iem.mrp_inr > iem.price_inr}<span class="muted small">store MRP {inr(iem.mrp_inr)}</span>{/if}
        </div>
        <a class="btn sm" href={iem.url} target="_blank" rel="noopener noreferrer">
          See it at {storeName(iem.cheapest_store)}
          <span class="sr-only">(opens in a new tab)</span>
        </a>
        {#if iem.stores.length > 1}
          <p class="small muted">
            Also listed at {iem.stores
              .filter((s) => s !== iem.cheapest_store)
              .map(storeName)
              .join(' and ')}. This was the lowest price on {meta.built}.
          </p>
        {/if}
      </section>

      <section>
        <h3>Score: {score(iem, w).toFixed(1)} out of 100</h3>
        <p class="small muted">With weights {w.sound} / {w.hardware} / {w.box} (sound / hardware / box).</p>
        <ul class="parts">
          {#each parts(iem) as p}
            <li>
              <span class="plabel">{p.label}</span>
              <span class="pbar {p.key}" aria-hidden="true"><i style="width:{p.frac * 100}%"></i></span>
              <span class="pval">{(p.frac * p.w).toFixed(1)} <span class="muted">of {p.w}</span></span>
            </li>
          {/each}
        </ul>
      </section>

      <section>
        <h3>Sound, from measurements</h3>
        {#if iem.harman_score == null}
          <p class="note">
            Nobody in the public databases has measured this IEM. It is scored at the bottom-quarter level of measured
            IEMs, {BEWARE_LEVEL}, so it cannot rank high on hope alone. Treat it as unknown, not as bad.
          </p>
        {:else}
          <dl class="math">
            <div><dt>Harman score, median across measurers</dt><dd>{f1(iem.harman_score)}</dd></div>
            <div>
              <dt>Margin of error for {iem.n_measurers} measurer{iem.n_measurers === 1 ? '' : 's'}</dt>
              <dd>−{margin(iem.n_measurers).toFixed(1)}</dd>
            </div>
            {#if iem.measurement_status === 'proxy'}
              <div><dt>Proxy penalty: only the base model is measured</dt><dd>−{PROXY_PENALTY}</dd></div>
            {/if}
            <div class="total"><dt>Score used for ranking</dt><dd>{f1(iem.harman_adjusted)}</dd></div>
          </dl>

          <h4>Tilt: {tiltWord(iem.tilt_slope)}</h4>
          <div class="tilt" role="img" aria-label="Tilt {signed(iem.tilt_slope!)}. {tiltWord(iem.tilt_slope)}.">
            <span class="track"><i style="left:{Math.max(0, Math.min(100, ((iem.tilt_slope! + 2) / 4) * 100))}%"></i></span>
            <span class="ends"><span>Warmer</span><span>Target</span><span>Brighter</span></span>
          </div>

          <h4>What the formula saw</h4>
          <table class="small">
            <thead><tr><th>Part</th><th>Measured</th><th>Points lost</th></tr></thead>
            <tbody>
              <tr><td>Unevenness (SD)</td><td>{iem.sd_db} dB</td><td>{(HARMAN.sd * iem.sd_db!).toFixed(1)}</td></tr>
              <tr
                ><td>Tilt (slope)</td><td>{signed(iem.tilt_slope!)}</td><td
                  >{(HARMAN.slope * Math.abs(iem.tilt_slope!)).toFixed(1)}</td
                ></tr
              >
              <tr
                ><td>Average distance from target</td><td>{iem.mean_error_db} dB</td><td
                  >{(HARMAN.err * iem.mean_error_db!).toFixed(1)}</td
                ></tr
              >
            </tbody>
          </table>
          {#if iem.score_spread != null}
            <p class="small muted">Measurers disagree by {iem.score_spread} points on this one.</p>
          {/if}

          <h4>Measured by</h4>
          <ul class="chips">
            {#each iem.measurers as m}
              <li><a href="https://{m}" target="_blank" rel="noopener noreferrer">{m}</a></li>
            {/each}
          </ul>
        {/if}
        <p class="small muted">{meta.disclaimers[1]}</p>
      </section>

      <section>
        <h3>Hardware <span class="claimed">as claimed by the store</span></h3>
        <ul class="facts">
          {#each Object.entries(iem.hardware) as [k, v]}
            <li><span>{HARDWARE_LABELS[k] ?? k}</span>{@render triCell(v)}</li>
          {/each}
        </ul>
      </section>

      <section>
        <h3>In the box <span class="claimed">as claimed by the store</span></h3>
        <ul class="facts">
          {#each Object.entries(iem.box) as [k, v]}
            <li><span>{BOX_LABELS[k] ?? k}</span>{@render triCell(v)}</li>
          {/each}
        </ul>
      </section>

      <section>
        <h3>Specs <span class="claimed">as claimed by the store</span></h3>
        <ul class="facts">
          <li><span>Impedance</span><span>{iem.specs_as_claimed.impedance_ohm != null ? `${iem.specs_as_claimed.impedance_ohm} Ω` : 'Not stated'}</span></li>
          <li><span>Sensitivity</span><span>{iem.specs_as_claimed.sensitivity_db_mw != null ? `${iem.specs_as_claimed.sensitivity_db_mw} dB/mW` : 'Not stated'}</span></li>
          <li><span>Eartip pairs</span><span>{iem.specs_as_claimed.eartip_pairs ?? 'Not stated'}</span></li>
          <li><span>Warranty</span><span>{iem.specs_as_claimed.warranty_months != null ? `${iem.specs_as_claimed.warranty_months} months` : 'Not stated'}</span></li>
        </ul>
        <p class="small muted">{meta.disclaimers[0]}</p>
      </section>

      <div class="actions">
        <button
          class="btn ghost"
          type="button"
          aria-pressed={ui.compare.includes(iem.id)}
          disabled={!ui.compare.includes(iem.id) && ui.compare.length >= MAX_COMPARE}
          onclick={() => toggleCompare(iem.id)}
        >
          {ui.compare.includes(iem.id) ? 'Remove from compare' : 'Add to compare'}
        </button>
      </div>
    </div>
  {/if}
</dialog>

{#if picked.length && !ui.compareOpen}
  <aside class="tray card" aria-label="Compare list">
    <ul>
      {#each picked as i (i.id)}
        <li>
          <span>{i.name}</span>
          <button type="button" aria-label="Remove {i.name} from compare" onclick={() => toggleCompare(i.id)}>
            <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"
              ><path d="M3 3l10 10M13 3 3 13" stroke="currentColor" stroke-width="2" /></svg
            >
          </button>
        </li>
      {/each}
    </ul>
    <button class="btn sm" type="button" disabled={picked.length < 2} onclick={() => (ui.compareOpen = true)}>
      {picked.length < 2 ? 'Pick one more' : `Compare ${picked.length}`}
    </button>
  </aside>
{/if}

<dialog
  class="compare"
  bind:this={compareEl}
  aria-labelledby="compare-title"
  onclose={() => (ui.compareOpen = false)}
  onclick={(e) => e.target === compareEl && (ui.compareOpen = false)}
>
  {#if ui.compareOpen && picked.length >= 2}
    {@const scores = picked.map((i) => score(i, w))}
    {@const bScore = best(scores, 'max')}
    {@const bPrice = best(picked.map((i) => i.price_inr), 'min')}
    {@const bHarman = best(picked.map((i) => i.harman_score), 'max')}
    <div class="inner">
      <header>
        <h2 id="compare-title">Side by side</h2>
        <button class="close" type="button" aria-label="Close comparison" onclick={() => (ui.compareOpen = false)}>
          <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"
            ><path d="M3 3l10 10M13 3 3 13" stroke="currentColor" stroke-width="2" /></svg
          >
        </button>
      </header>
      <div class="scroll">
        <table style="--cols:{picked.length}">
          <thead>
            <tr>
              <td></td>
              {#each picked as i}
                <th scope="col">{i.name}<span class="muted plug">{plugLabel(i.plug)}</span></th>
              {/each}
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">Price</th>
              {#each picked as i}
                <td>{inr(i.price_inr)}{#if i.price_inr === bPrice}<em>lowest</em>{/if}</td>
              {/each}
            </tr>
            <tr>
              <th scope="row">Score</th>
              {#each picked as i, k}
                <td><strong>{scores[k].toFixed(1)}</strong>{#if scores[k] === bScore}<em>highest</em>{/if}</td>
              {/each}
            </tr>
            <tr>
              <th scope="row">Rank in its plug type</th>
              {#each picked as i}
                {@const r = rankOf(i)}
                <td>{r.rank} of {r.of}</td>
              {/each}
            </tr>
            <tr>
              <th scope="row">Harman score</th>
              {#each picked as i}
                <td>{f1(i.harman_score)}{#if i.harman_score != null && i.harman_score === bHarman}<em>highest</em>{/if}</td>
              {/each}
            </tr>
            <tr>
              <th scope="row">Measurement</th>
              {#each picked as i}<td class="wrapb"><Badges iem={i} stock={false} /></td>{/each}
            </tr>
            <tr>
              <th scope="row">Tilt</th>
              {#each picked as i}
                <td>{i.tilt_slope == null ? 'n/a' : signed(i.tilt_slope)}<span class="muted sub">{tiltWord(i.tilt_slope)}</span></td>
              {/each}
            </tr>
            <tr class="group"><th colspan={picked.length + 1}>Hardware, as claimed by the store</th></tr>
            {#each hwKeys as k}
              <tr>
                <th scope="row">{HARDWARE_LABELS[k] ?? k}</th>
                {#each picked as i}
                  <td>{#if k in i.hardware}{@render triCell(i.hardware[k])}{:else}<span class="muted">n/a</span>{/if}</td>
                {/each}
              </tr>
            {/each}
            <tr class="group"><th colspan={picked.length + 1}>In the box, as claimed by the store</th></tr>
            {#each Object.keys(BOX_LABELS) as k}
              <tr>
                <th scope="row">{BOX_LABELS[k]}</th>
                {#each picked as i}<td>{@render triCell(i.box[k])}</td>{/each}
              </tr>
            {/each}
            <tr class="group"><th colspan={picked.length + 1}>Buying</th></tr>
            <tr>
              <th scope="row">Availability</th>
              {#each picked as i}<td>{i.availability}</td>{/each}
            </tr>
            <tr>
              <th scope="row">Store</th>
              {#each picked as i}
                <td><a href={i.url} target="_blank" rel="noopener noreferrer">{storeName(i.cheapest_store)}</a></td>
              {/each}
            </tr>
          </tbody>
        </table>
      </div>
      <p class="small muted">
        Scores use your current weights ({w.sound} / {w.hardware} / {w.box}). Type-C and 3.5 mm are ranked separately.
        {meta.disclaimers[1]}
      </p>
    </div>
  {/if}
</dialog>

<style>
  dialog {
    border: 0;
    padding: 0;
    color: var(--ink);
    background: var(--bg);
    box-shadow: var(--shadow);
    overscroll-behavior: contain;
  }
  dialog::backdrop {
    background: rgb(20 15 8 / 0.55);
  }
  .sheet {
    width: 100%;
    max-width: 100%;
    max-height: 92dvh;
    margin: auto 0 0;
    border-radius: 18px 18px 0 0;
  }
  .compare {
    width: min(100%, 860px);
    max-width: 100%;
    max-height: 92dvh;
    margin: auto 0 0;
    border-radius: 18px 18px 0 0;
  }
  dialog[open] {
    animation: rise 0.28s cubic-bezier(0.2, 0.8, 0.2, 1);
  }
  @keyframes rise {
    from {
      transform: translateY(24px);
      opacity: 0;
    }
  }
  @media (min-width: 820px) {
    .sheet {
      width: 480px;
      height: 100dvh;
      max-height: 100dvh;
      margin: 0 0 0 auto;
      border-radius: 0;
      border-left: 1px solid var(--line);
    }
    .sheet[open] {
      animation-name: slide;
    }
    .compare {
      margin: auto;
      border-radius: 14px;
    }
    @keyframes slide {
      from {
        transform: translateX(32px);
        opacity: 0;
      }
    }
  }
  .inner {
    padding: 1.1rem 1.1rem 2rem;
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: start;
    gap: 0.75rem;
    position: sticky;
    top: 0;
    background: var(--bg);
    padding: 0.5rem 0 0.4rem;
    z-index: 2;
  }
  header h2 {
    font-size: 1.6rem;
    margin: 0;
  }
  header .eyebrow {
    margin-bottom: 0.2rem;
  }
  .close {
    flex: none;
    width: 2.75rem;
    height: 2.75rem;
    display: grid;
    place-items: center;
    border-radius: 999px;
    border: 1px solid var(--line);
    background: var(--surface);
  }
  .photo {
    margin: 0 0 0.8rem;
    display: grid;
    justify-items: center;
    gap: 0.2rem;
  }
  .photo img {
    width: min(15rem, 70%);
    height: auto;
    aspect-ratio: 1;
    object-fit: contain;
    background: #fff;
    border: 1px solid var(--line);
    border-radius: var(--r);
  }
  .badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin: 0.4rem 0 0.6rem;
  }
  section {
    margin-top: 1.4rem;
  }
  h3 {
    margin-bottom: 0.4rem;
  }
  h4 {
    margin: 1.1rem 0 0.4rem;
    font-size: 0.95rem;
  }
  .claimed {
    font-family: var(--body);
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--muted);
    border: 1px dashed var(--line);
    border-radius: 999px;
    padding: 0.1rem 0.5rem;
    margin-left: 0.3rem;
    white-space: nowrap;
    vertical-align: middle;
  }
  .buy {
    display: grid;
    grid-template-columns: 1fr auto;
    align-items: center;
    gap: 0.4rem 0.8rem;
    padding: 0.8rem 0.9rem;
    margin-top: 0.8rem;
  }
  .buy p {
    grid-column: 1 / -1;
    margin: 0;
  }
  .price {
    font-family: var(--display);
    font-size: 1.6rem;
    font-weight: 600;
    margin-right: 0.4rem;
  }
  .parts,
  .facts,
  .chips {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .parts li {
    display: grid;
    grid-template-columns: 5.4rem 1fr 5.6rem;
    align-items: center;
    gap: 0.6rem;
    padding: 0.3rem 0;
  }
  .pval {
    text-align: right;
    font-weight: 600;
  }
  .pval .muted {
    font-weight: 400;
  }
  .pbar {
    height: 0.8rem;
    border-radius: 999px;
    background: var(--grid);
    overflow: hidden;
  }
  .pbar i {
    display: block;
    height: 100%;
    border-radius: 999px;
    background: var(--accent);
  }
  .pbar.hardware i {
    background: repeating-linear-gradient(135deg, var(--teal) 0 4px, color-mix(in srgb, var(--teal) 55%, transparent) 4px 7px);
  }
  .pbar.box i {
    background: var(--ink);
  }
  .math {
    margin: 0;
  }
  .math div {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.35rem 0;
    border-bottom: 1px solid var(--line);
  }
  .math dd {
    margin: 0;
    font-weight: 600;
    white-space: nowrap;
  }
  .math .total {
    border-bottom: 0;
    font-weight: 700;
  }
  .tilt .track {
    display: block;
    position: relative;
    height: 0.7rem;
    border-radius: 999px;
    background: linear-gradient(90deg, var(--accent), var(--grid) 50%, var(--teal));
  }
  .tilt .track::after {
    content: '';
    position: absolute;
    left: 50%;
    top: -3px;
    bottom: -3px;
    width: 1px;
    background: var(--ink);
  }
  .tilt i {
    position: absolute;
    top: 50%;
    width: 1rem;
    height: 1rem;
    border-radius: 999px;
    background: var(--bg);
    border: 3px solid var(--ink);
    transform: translate(-50%, -50%);
    z-index: 1;
  }
  .tilt .ends {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: var(--muted);
    margin-top: 0.3rem;
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
  }
  .chips a {
    display: inline-block;
    padding: 0.25rem 0.6rem;
    border: 1px solid var(--line);
    border-radius: 999px;
    font-size: 0.8rem;
    text-decoration: none;
    background: var(--surface);
  }
  .facts li {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.4rem 0;
    border-bottom: 1px solid var(--line);
  }
  .tri {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    color: var(--muted);
    white-space: nowrap;
  }
  .tri.yes {
    color: var(--teal);
    font-weight: 600;
  }
  .tri.no {
    color: var(--ink);
  }
  .actions {
    margin-top: 1.4rem;
  }

  .tray {
    position: fixed;
    left: 50%;
    bottom: max(0.75rem, env(safe-area-inset-bottom));
    transform: translateX(-50%);
    z-index: 40;
    width: min(100% - 1.5rem, 640px);
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.5rem 0.6rem;
    background: var(--raised);
    box-shadow: var(--shadow);
  }
  .tray ul {
    list-style: none;
    display: flex;
    gap: 0.3rem;
    padding: 0;
    margin: 0;
    flex: 1;
    min-width: 0;
    overflow-x: auto;
  }
  .tray li {
    display: inline-flex;
    align-items: center;
    gap: 0.1rem;
    padding-left: 0.6rem;
    border: 1px solid var(--line);
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
    white-space: nowrap;
  }
  .tray li span {
    max-width: 8.5rem;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .tray li button {
    width: 2rem;
    height: 2rem;
    border: 0;
    background: none;
    display: grid;
    place-items: center;
    border-radius: 999px;
  }
  .tray .btn {
    flex: none;
  }

  .scroll {
    overflow-x: auto;
  }
  .compare table {
    table-layout: fixed;
    font-size: 0.82rem;
    min-width: calc(5.5rem + var(--cols) * 5.6rem);
  }
  .compare td:first-child,
  .compare tbody th[scope='row'] {
    width: 5.5rem;
    font-weight: 500;
    color: var(--muted);
  }
  .compare thead th {
    font-family: var(--display);
    font-size: 0.95rem;
    line-height: 1.2;
    vertical-align: bottom;
  }
  .compare .plug,
  .compare .sub {
    display: block;
    font-family: var(--body);
    font-size: 0.72rem;
    font-weight: 400;
  }
  .compare em {
    display: block;
    width: fit-content;
    font-style: normal;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--teal);
    border: 1px solid var(--teal);
    border-radius: 999px;
    padding: 0 0.4rem;
    margin-top: 0.15rem;
  }
  .compare .group th {
    padding-top: 1rem;
    font-size: 0.72rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--accent-ink);
  }
  .compare .wrapb :global(.badge) {
    white-space: normal;
  }
  .compare .tri {
    white-space: normal;
  }
  @media (min-width: 700px) {
    .compare table {
      font-size: 0.92rem;
    }
    .compare td:first-child,
    .compare tbody th[scope='row'] {
      width: 9rem;
    }
    .inner {
      padding: 1.2rem 1.5rem 2rem;
    }
  }
</style>
