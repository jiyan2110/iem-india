<script lang="ts">
  import PlugToggle from './PlugToggle.svelte';
  import { HARDWARE_LABELS, iems, inr, inStock, tiltWord } from '../lib/data';
  import { ui } from '../lib/state.svelte';

  let budget = $state(5000);
  let mic = $state(false);
  let taste = $state<'harman' | 'bright'>('harman');

  const matches = $derived(
    iems
      .filter(
        (i) =>
          i.plug === ui.plug &&
          inStock(i) &&
          i.measurement_status === 'measured' &&
          i.price_inr <= budget &&
          (!mic || i.hardware.mic === true) &&
          (taste === 'harman' || i.tilt_slope! > 0),
      )
      .sort((a, b) => b.score_default - a.score_default),
  );
  const picks = $derived(matches.slice(0, 3));
  const href = $derived(`/explore#p=${ui.plug === 'Type-C' ? 'c' : '35'}&max=${budget}&av=i&ms=m`);

  const perks = (i: (typeof iems)[number]) =>
    Object.entries(i.hardware)
      .filter(([, v]) => v === true)
      .map(([k]) => HARDWARE_LABELS[k].toLowerCase());
</script>

<div class="picker">
  <div class="qs">
    <fieldset>
      <legend>1. Which plug does your phone or laptop have?</legend>
      <PlugToggle />
    </fieldset>
    <fieldset>
      <legend>2. What is your budget?</legend>
      <div class="seg" role="group" aria-label="Budget">
        {#each [2000, 5000, 10000] as b}
          <button type="button" aria-pressed={budget === b} onclick={() => (budget = b)}>Up to {inr(b)}</button>
        {/each}
      </div>
    </fieldset>
    <fieldset>
      <legend>3. Anything else?</legend>
      <label class="check"><input type="checkbox" bind:checked={mic} /> I need a microphone</label>
      <label class="check">
        <input type="checkbox" checked={taste === 'bright'} onchange={(e) => (taste = e.currentTarget.checked ? 'bright' : 'harman')} />
        I usually find earphones too bassy
      </label>
    </fieldset>
  </div>

  <div class="out" aria-live="polite">
    {#if picks.length}
      <ol>
        {#each picks as i, k (i.id)}
          <li>
            <button type="button" class="pick card" onclick={() => (ui.detail = i.id)}>
              <span class="no" aria-hidden="true">{k + 1}</span>
              <span class="name">{i.name}</span>
              <span class="line"><b>{inr(i.price_inr)}</b> · score {i.score_default.toFixed(1)}</span>
              <span class="why">
                Harman {i.harman_score!.toFixed(1)} from {i.n_measurers} measurer{i.n_measurers === 1 ? '' : 's'}.
                {tiltWord(i.tilt_slope)}.
                {#if perks(i).length}Store says: {perks(i).join(', ')}.{/if}
              </span>
              <span class="more">Open details</span>
            </button>
          </li>
        {/each}
      </ol>
      <p class="small muted">
        In stock, measured, ranked with the default weights. {matches.length} IEM{matches.length === 1 ? '' : 's'} fit.
        <a {href}>See everything in this budget</a>
        {#if picks.length > 1}
          or
          <button
            class="linkbtn"
            type="button"
            onclick={() => {
              ui.compare = picks.map((p) => p.id);
              ui.compareOpen = true;
            }}>compare these side by side</button
          >.
        {/if}
      </p>
    {:else}
      <p class="note">Nothing in stock fits all of that. Try a higher budget or drop one of the extras.</p>
    {/if}
  </div>
</div>

<style>
  .picker {
    display: grid;
    gap: 1.5rem;
  }
  .qs {
    display: grid;
    gap: 1rem;
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
    margin-bottom: 0.45rem;
  }
  .check {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-height: 2.5rem;
  }
  ol {
    list-style: none;
    padding: 0;
    margin: 0 0 0.8rem;
    display: grid;
    gap: 0.7rem;
  }
  .pick {
    display: grid;
    grid-template-columns: 2.4rem 1fr;
    gap: 0.1rem 0.7rem;
    width: 100%;
    height: 100%;
    padding: 0.9rem;
    text-align: left;
    align-content: start;
    transition: transform 0.15s, box-shadow 0.15s;
  }
  .pick:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow);
  }
  .no {
    grid-row: 1 / span 4;
    font-family: var(--display);
    font-size: 2.4rem;
    line-height: 1;
    color: var(--accent-ink);
  }
  .name {
    font-family: var(--display);
    font-size: 1.2rem;
    font-weight: 600;
    line-height: 1.2;
  }
  .why {
    font-size: 0.85rem;
    color: var(--muted);
  }
  .more {
    font-size: 0.85rem;
    font-weight: 600;
    text-decoration: underline;
    text-underline-offset: 0.18em;
    color: var(--accent-ink);
    margin-top: 0.3rem;
  }
  .linkbtn {
    border: 0;
    background: none;
    padding: 0;
    color: var(--accent-ink);
    text-decoration: underline;
    text-underline-offset: 0.18em;
  }
  @media (min-width: 820px) {
    .picker {
      grid-template-columns: 19rem 1fr;
      gap: 2.5rem;
    }
    ol {
      grid-template-columns: repeat(3, 1fr);
    }
    .pick {
      grid-template-columns: 1fr;
    }
    .no {
      grid-row: auto;
    }
  }
</style>
