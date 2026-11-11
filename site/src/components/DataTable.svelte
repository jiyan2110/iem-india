<script lang="ts">
  // The whole dataset as one sortable, searchable table.
  import { iems, PLUGS, plugLabel, type Plug } from '../lib/data';
  import { COLUMNS } from '../lib/table';
  import { ui } from '../lib/state.svelte';

  const cols = COLUMNS.filter((c) => c.show);
  let plug = $state<Plug | 'all'>('all');
  let q = $state('');
  let sortKey = $state('score_default');
  let desc = $state(true);

  const rows = $derived.by(() => {
    const needle = q.trim().toLowerCase();
    const col = cols.find((c) => c.key === sortKey)!;
    return iems
      .filter((i) => (plug === 'all' || i.plug === plug) && (!needle || i.name.toLowerCase().includes(needle)))
      .map((i) => ({ i, v: col.get(i) }))
      .sort((a, b) => {
        // Empty cells always sink to the bottom, whichever way the column is sorted.
        if (a.v == null || b.v == null) return a.v == null ? (b.v == null ? 0 : 1) : -1;
        const d = typeof a.v === 'number' && typeof b.v === 'number' ? a.v - b.v : String(a.v).localeCompare(String(b.v));
        return desc ? -d : d;
      })
      .map((r) => r.i);
  });

  function sortBy(key: string, num?: boolean) {
    if (sortKey === key) desc = !desc;
    else {
      sortKey = key;
      desc = !!num;
    }
  }
  const show = (v: string | number | null, digits?: number) =>
    v == null ? '' : typeof v === 'number' ? (digits != null ? v.toFixed(digits) : v.toLocaleString('en-IN')) : v;
</script>

<div class="tools">
  <div class="seg" role="group" aria-label="Plug type">
    <button type="button" aria-pressed={plug === 'all'} onclick={() => (plug = 'all')}>All</button>
    {#each PLUGS as p}
      <button type="button" aria-pressed={plug === p} onclick={() => (plug = p)}>{plugLabel(p)}</button>
    {/each}
  </div>
  <label class="search">
    <span class="sr-only">Search by name</span>
    <input type="search" placeholder="Search by name" bind:value={q} />
  </label>
  <p class="count muted small" aria-live="polite">{rows.length} of {iems.length} rows</p>
</div>

<div class="scroll" tabindex="0" role="region" aria-label="Table of every IEM. Scroll sideways for more columns.">
  <table>
    <thead>
      <tr>
        {#each cols as c}
          <th scope="col" class:num={c.num} aria-sort={sortKey === c.key ? (desc ? 'descending' : 'ascending') : 'none'}>
            <button type="button" onclick={() => sortBy(c.key, c.num)}>
              {c.label}
              <span aria-hidden="true">{sortKey === c.key ? (desc ? '↓' : '↑') : ''}</span>
            </button>
          </th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each rows as i (i.id)}
        <tr>
          {#each cols as c, k}
            {#if k === 0}
              <th scope="row"><button class="link" type="button" onclick={() => (ui.detail = i.id)}>{i.name}</button></th>
            {:else}
              <td class:num={c.num}>{show(c.get(i), c.digits)}</td>
            {/if}
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .tools {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.6rem 1rem;
    margin-bottom: 0.7rem;
  }
  .search input {
    min-height: 2.6rem;
    width: min(16rem, 70vw);
    padding: 0.3rem 0.8rem;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface);
  }
  .count {
    margin: 0 0 0 auto;
  }
  .scroll {
    overflow: auto;
    max-height: min(75vh, 48rem);
    border: 1px solid var(--line);
    border-radius: var(--r);
    background: var(--surface);
  }
  table {
    font-size: 0.82rem;
    width: max-content;
    min-width: 100%;
  }
  th,
  td {
    padding: 0.4rem 0.7rem;
    white-space: nowrap;
    vertical-align: middle;
  }
  thead th {
    position: sticky;
    top: 0;
    z-index: 2;
    background: var(--raised);
    padding: 0;
    max-width: 9rem;
  }
  thead button {
    width: 100%;
    min-height: 2.75rem;
    padding: 0.4rem 0.7rem;
    border: 0;
    background: none;
    font-weight: 600;
    text-align: left;
    white-space: normal;
    line-height: 1.2;
  }
  thead th[aria-sort='ascending'] button,
  thead th[aria-sort='descending'] button {
    color: var(--accent-ink);
  }
  .num,
  th.num button {
    text-align: right;
  }
  tbody th {
    position: sticky;
    left: 0;
    z-index: 1;
    background: var(--surface);
    max-width: 46vw;
    overflow: hidden;
    text-overflow: ellipsis;
    font-weight: 600;
    box-shadow: 1px 0 0 var(--line);
  }
  thead th:first-child {
    left: 0;
    z-index: 3;
    box-shadow: 1px 0 0 var(--line);
  }
  .link {
    border: 0;
    background: none;
    padding: 0.3rem 0;
    text-align: left;
    font-weight: 600;
    text-decoration: underline;
    text-underline-offset: 0.18em;
    color: var(--accent-ink);
  }
</style>
