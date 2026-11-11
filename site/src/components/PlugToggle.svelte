<script lang="ts">
  import { iems, PLUGS, plugLabel } from '../lib/data';
  import { ui } from '../lib/state.svelte';

  const counts = Object.fromEntries(PLUGS.map((p) => [p, iems.filter((i) => i.plug === p).length]));
</script>

<div class="seg" role="group" aria-label="Plug type">
  {#each PLUGS as p}
    <button type="button" aria-pressed={ui.plug === p} onclick={() => (ui.plug = p)}>
      {plugLabel(p)} <span class="n">{counts[p]}</span>
    </button>
  {/each}
</div>

<style>
  .seg {
    width: fit-content;
  }
  .n {
    font-weight: 400;
    opacity: 0.75;
    font-size: 0.85em;
  }
</style>
