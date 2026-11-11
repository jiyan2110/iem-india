<script lang="ts">
  import { inStock, type Iem } from '../lib/data';
  let { iem, stock = true }: { iem: Iem; stock?: boolean } = $props();
</script>

{#if iem.measurement_status === 'buyer_beware'}
  <span class="badge warn" title="No public measurement was found for this IEM">
    <svg viewBox="0 0 12 12" width="11" height="11" aria-hidden="true"
      ><path d="M6 1 11.5 11H.5Z" fill="none" stroke="currentColor" stroke-width="1.4" /><path
        d="M6 4.6v3M6 8.8v.6"
        stroke="currentColor"
        stroke-width="1.4"
      /></svg
    >
    Buyer beware: not measured
  </span>
{:else if iem.measurement_status === 'proxy'}
  <span class="badge proxy" title="A collab edition. Only the base model has been measured">
    <svg viewBox="0 0 12 12" width="10" height="10" aria-hidden="true"><path d="M6 .8 11.2 6 6 11.2.8 6Z" fill="currentColor" /></svg>
    Proxy: base model measured
  </span>
{:else}
  <span class="badge">{iem.n_measurers} measurer{iem.n_measurers === 1 ? '' : 's'}</span>
{/if}
{#if stock}
  {#if inStock(iem)}
    <span class="badge ok">In stock</span>
  {:else}
    <span class="badge sold" title={iem.availability_note || undefined}>
      <svg viewBox="0 0 12 12" width="10" height="10" aria-hidden="true"
        ><circle cx="6" cy="6" r="4.6" fill="none" stroke="currentColor" stroke-width="1.4" /><path
          d="M2.8 9.2 9.2 2.8"
          stroke="currentColor"
          stroke-width="1.4"
        /></svg
      >
      {iem.availability}
    </span>
  {/if}
{/if}

<style>
  .sold {
    color: var(--ink);
    border-color: var(--ink);
  }
</style>
