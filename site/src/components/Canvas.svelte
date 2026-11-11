<script lang="ts">
  // The homepage: one full-screen scatter where the reader picks the plug and both axes.
  // Dots are positioned in percentages, so the server-rendered chart is right at any size.
  import { onMount } from 'svelte';
  import { AXIS_GROUPS, axisBy, niceTicks, VIEWS, type Axis } from '../lib/axes';
  import { iems, inr, inStock, median, meta, photo, PLUGS, plugLabel, r2Text, storeName, type Iem } from '../lib/data';
  import { MAX_COMPARE, readHash, toggleCompare, ui, writeHash } from '../lib/state.svelte';

  let xk = $state('price');
  let yk = $state('harman');
  let show = $state({ stock: true, sold: true, proxy: true, none: true });
  let view = $state<{ x0: number; x1: number; y0: number; y1: number } | null>(null);
  let active = $state<string | null>(null);
  let pinned = $state(false);
  let moving = $state(false);
  let find = $state('');
  let ready = $state(false);
  // null means 'follow the screen size': open on wide screens, tucked away on phones.
  let open = $state<boolean | null>(null);
  let plotEl: HTMLDivElement;
  // Plot size in pixels, known only in the browser. The fallback is a typical desktop plot.
  let pw = $state(0);
  let ph = $state(0);

  const X = $derived(axisBy.get(xk)!);
  const Y = $derived(axisBy.get(yk)!);
  const t = (a: Axis, v: number) => (a.fwd ? a.fwd(v) : v);
  const inv = (a: Axis, v: number) => (a.inv ? a.inv(v) : v);
  const cap = (s: string) => s[0].toUpperCase() + s.slice(1);
  const plugCount = Object.fromEntries(PLUGS.map((p) => [p, iems.filter((i) => i.plug === p).length]));

  // The scale is shared by both plugs, so switching plug compares like with like.
  function span(a: Axis) {
    const v = iems.map((i) => a.get(i)).filter((n) => n != null) as number[];
    let lo = t(a, Math.min(...v));
    let hi = t(a, Math.max(...v));
    const pad = (hi - lo) * 0.07;
    lo -= pad;
    hi += pad;
    return [lo, hi] as const;
  }
  const base = $derived.by(() => {
    const [x0, x1] = span(X);
    const [y0, y1] = span(Y);
    return { x0, x1, y0, y1 };
  });
  const v = $derived(view ?? base);
  const zoomed = $derived(view != null);

  const rows = $derived(iems.filter((i) => i.plug === ui.plug && X.get(i) != null && Y.get(i) != null));
  const left = $derived(plugCount[ui.plug] - rows.length);
  const kindOf = (i: Iem) =>
    i.measurement_status === 'proxy' ? 'proxy' : i.measurement_status === 'buyer_beware' ? 'none' : 'measured';
  const visible = (i: Iem) =>
    (inStock(i) ? show.stock : show.sold) && (kindOf(i) !== 'proxy' || show.proxy) && (kindOf(i) !== 'none' || show.none);
  const hasNone = $derived(rows.some((i) => kindOf(i) === 'none'));

  const xs = $derived(X.split ?? median(rows.map((i) => X.get(i)!)));
  const ys = $derived(Y.split ?? median(rows.map((i) => Y.get(i)!)));
  const good = (a: Axis) => (a.better === 'low' ? 0 : a.better === 'high' ? 1 : null);
  const gx = $derived(good(X));
  const gy = $derived(good(Y));
  const hasBest = $derived(gx != null && gy != null);
  // Which side of the split a value falls on: 0 is the low side, 1 the high side.
  const side = (a: Axis, val: number, split: number) => (a.better === 'high' ? (val >= split ? 1 : 0) : val <= split ? 0 : 1);

  const points = $derived(
    rows.filter(visible).map((i) => {
      const xv = X.get(i)!;
      const yv = Y.get(i)!;
      const sx = side(X, xv, xs);
      const sy = side(Y, yv, ys);
      const taste = X.better === 'mid' ? sx : Y.better === 'mid' ? sy : null;
      const tone = hasBest ? (sx === gx && sy === gy ? 'accent' : 'muted') : taste === 0 ? 'accent' : taste === 1 ? 'teal' : 'muted';
      return { i, id: i.id, xv, yv, tx: t(X, xv), ty: t(Y, yv), sx, sy, tone, kind: kindOf(i), hollow: !inStock(i) };
    }),
  );
  const px = (tx: number) => ((tx - v.x0) / (v.x1 - v.x0)) * 100;
  const py = (ty: number) => 100 - ((ty - v.y0) / (v.y1 - v.y0)) * 100;
  const pct = (n: number) => `${n.toFixed(2)}%`;
  const inView = (p: { tx: number; ty: number }) => p.tx >= v.x0 && p.tx <= v.x1 && p.ty >= v.y0 && p.ty <= v.y1;

  const quads = $derived(
    [
      { sy: 1, sx: 0, pos: 'tl' },
      { sy: 1, sx: 1, pos: 'tr' },
      { sy: 0, sx: 0, pos: 'bl' },
      { sy: 0, sx: 1, pos: 'br' },
    ].map((q) => ({
      ...q,
      label: cap(`${Y.words[q.sy]}, ${X.words[q.sx]}`),
      n: points.filter((p) => p.sx === q.sx && p.sy === q.sy).length,
      best: hasBest && q.sx === gx && q.sy === gy,
    })),
  );
  const bestQuad = $derived(quads.find((q) => q.best) ?? null);
  const clampPct = (n: number) => Math.max(0, Math.min(100, n));
  const shade = $derived.by(() => {
    if (!hasBest) return null;
    const sxp = clampPct(px(t(X, xs)));
    const syp = clampPct(py(t(Y, ys)));
    return {
      left: gx === 0 ? 0 : sxp,
      width: gx === 0 ? sxp : 100 - sxp,
      top: gy === 1 ? 0 : syp,
      height: gy === 1 ? syp : 100 - syp,
    };
  });
  // The "prefer less bass" zone from the Harman research, drawn whenever tone is on an axis.
  const band = $derived.by(() => {
    if (X.key === 'tilt') return { left: clampPct(px(0)), width: clampPct(px(0.5)) - clampPct(px(0)), top: 0, height: 100 };
    if (Y.key === 'tilt') return { left: 0, width: 100, top: clampPct(py(0.5)), height: clampPct(py(0)) - clampPct(py(0.5)) };
    return null;
  });

  const tickFmt = (a: Axis) => a.tick ?? ((n: number) => String(+n.toPrecision(6)));
  // Preferred ticks while enough of them are in view; round numbers once zoomed in tight.
  function ticks(a: Axis, lo: number, hi: number) {
    const own = (a.ticks ?? []).filter((n) => t(a, n) >= lo && t(a, n) <= hi);
    const use = own.length >= 3 ? own : niceTicks(inv(a, lo), inv(a, hi), a.fwd ? 5 : 6);
    return use.map((n) => ({ n, tv: t(a, n), label: tickFmt(a)(n) }));
  }
  const xt = $derived(ticks(X, v.x0, v.x1).map((k) => ({ ...k, p: px(k.tv) })).filter((k) => k.p >= 0 && k.p <= 100));
  const yt = $derived(ticks(Y, v.y0, v.y1).map((k) => ({ ...k, p: py(k.tv) })).filter((k) => k.p >= 0 && k.p <= 100));

  const insight = $derived.by(() => {
    const k = new Set([xk, yk]);
    if (k.has('price') && k.has('harman'))
      return `If money bought sound, the dots would climb as they get pricier. They do not: R² is ${r2Text(ui.plug)}, close to zero.`;
    if (k.has('tilt'))
      return `Warm or bright is taste. In the Harman research, ${meta.key_numbers.harman_listener_split}. If that sounds like you, look in the shaded band.`;
    return `${Y.label}: ${Y.help} ${X.label}: ${X.help}`;
  });

  const cur = $derived(active ? (points.find((p) => p.id === active) ?? null) : null);
  const order = $derived([...points].sort((a, b) => a.tx - b.tx || a.ty - b.ty).map((p) => p.id));
  // A few names written on the canvas: the best overall scorers, kept apart so they do not collide.
  const labels = $derived.by(() => {
    const out: (typeof points)[number][] = [];
    const ranked = [...points].filter(inView).sort((a, b) => b.i.score_default - a.i.score_default);
    const w = pw || 900;
    const h = ph || 560;
    const max = w < 500 ? 4 : 9;
    const width = (p: (typeof points)[number]) => p.i.name.length * 7.5 + 24;
    const placed: { x: number; y: number; w: number }[] = [];
    for (const p of ranked) {
      if (out.length >= max) break;
      const x = (px(p.tx) / 100) * w;
      const y = (py(p.ty) / 100) * h;
      if (y < 60 || y > h - 60) continue;
      const mine = width(p);
      // Leave room for a label on either side of the dot, so flipping never causes a collision.
      if (placed.every((o) => Math.abs(o.y - y) > 20 || Math.abs(o.x - x) > Math.max(o.w, mine))) {
        out.push(p);
        placed.push({ x, y, w: mine });
      }
    }
    return out.map((p) => ({ ...p, flip: (px(p.tx) / 100) * w + width(p) > w }));
  });
  const compared = $derived(points.filter((p) => ui.compare.includes(p.id)));
  const status = (i: Iem) =>
    `${inStock(i) ? 'In stock' : 'Sold out'} · ${
      kindOf(i) === 'proxy'
        ? 'proxy, base model measured'
        : kindOf(i) === 'none'
          ? 'not measured'
          : `${i.n_measurers} measurer${i.n_measurers === 1 ? '' : 's'}`
    }`;

  function setAxis(which: 'x' | 'y', key: string) {
    const other = which === 'x' ? yk : xk;
    const prev = which === 'x' ? xk : yk;
    if (key === other) {
      // Picking the axis already used on the other side swaps the two.
      if (which === 'x') yk = prev;
      else xk = prev;
    }
    if (which === 'x') xk = key;
    else yk = key;
    reset();
  }
  function setView(x: string, y: string) {
    xk = x;
    yk = y;
    reset();
  }
  function reset() {
    view = null;
    active = null;
    pinned = false;
  }

  // ---- zoom and pan -------------------------------------------------------
  let quiet: ReturnType<typeof setTimeout>;
  function settle() {
    moving = true;
    clearTimeout(quiet);
    quiet = setTimeout(() => (moving = false), 180);
  }
  function fit(n: { x0: number; x1: number; y0: number; y1: number }) {
    const b = base;
    const clamp1 = (lo: number, hi: number, blo: number, bhi: number) => {
      const w = Math.min(hi - lo, bhi - blo);
      const a = Math.max(blo, Math.min(bhi - w, lo));
      return [a, a + w] as const;
    };
    const [x0, x1] = clamp1(n.x0, n.x1, b.x0, b.x1);
    const [y0, y1] = clamp1(n.y0, n.y1, b.y0, b.y1);
    const full = x1 - x0 >= (b.x1 - b.x0) * 0.999 && y1 - y0 >= (b.y1 - b.y0) * 0.999;
    view = full ? null : { x0, x1, y0, y1 };
  }
  /** Zoom by a factor around a point given as fractions of the plot (0..1 from the top-left). */
  function zoom(f: number, fx = 0.5, fy = 0.5) {
    const b = base;
    const minF = Math.max(f, (b.x1 - b.x0) / 40 / (v.x1 - v.x0));
    const ax = v.x0 + fx * (v.x1 - v.x0);
    const ay = v.y1 - fy * (v.y1 - v.y0);
    settle();
    fit({
      x0: ax - (ax - v.x0) * minF,
      x1: ax + (v.x1 - ax) * minF,
      y0: ay - (ay - v.y0) * minF,
      y1: ay + (v.y1 - ay) * minF,
    });
  }
  function pan(dx: number, dy: number, r: DOMRect) {
    const mx = (dx / r.width) * (v.x1 - v.x0);
    const my = (dy / r.height) * (v.y1 - v.y0);
    settle();
    fit({ x0: v.x0 - mx, x1: v.x1 - mx, y0: v.y0 + my, y1: v.y1 + my });
  }

  // ---- pointer ------------------------------------------------------------
  const ptrs = new Map<number, { x: number; y: number }>();
  let down: { x: number; y: number; moved: boolean } | null = null;
  let pinch = 0;

  function nearest(e: PointerEvent, reach: number) {
    const r = plotEl.getBoundingClientRect();
    let best: string | null = null;
    let bd = reach * reach;
    for (const p of points) {
      const dx = (px(p.tx) / 100) * r.width - (e.clientX - r.left);
      const dy = (py(p.ty) / 100) * r.height - (e.clientY - r.top);
      const d = dx * dx + dy * dy;
      if (d < bd) {
        bd = d;
        best = p.id;
      }
    }
    return best;
  }
  function pdown(e: PointerEvent) {
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
    plotEl.setPointerCapture(e.pointerId);
    if (ptrs.size === 1) down = { x: e.clientX, y: e.clientY, moved: false };
    else {
      const [a, b] = [...ptrs.values()];
      pinch = Math.hypot(a.x - b.x, a.y - b.y);
      if (down) down.moved = true;
    }
  }
  function pmove(e: PointerEvent) {
    const prev = ptrs.get(e.pointerId);
    if (!prev) {
      if (e.pointerType === 'mouse' && !pinned) active = nearest(e, 26);
      return;
    }
    const r = plotEl.getBoundingClientRect();
    if (ptrs.size === 2) {
      ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
      const [a, b] = [...ptrs.values()];
      const d = Math.hypot(a.x - b.x, a.y - b.y);
      if (pinch > 0 && d > 0)
        zoom(pinch / d, ((a.x + b.x) / 2 - r.left) / r.width, ((a.y + b.y) / 2 - r.top) / r.height);
      pinch = d;
      return;
    }
    if (!down) return;
    if (!down.moved && Math.hypot(e.clientX - down.x, e.clientY - down.y) < 6) return;
    down.moved = true;
    if (zoomed) pan(e.clientX - prev.x, e.clientY - prev.y, r);
    ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
  }
  function pup(e: PointerEvent) {
    if (!ptrs.delete(e.pointerId)) return;
    const was = down;
    if (ptrs.size === 0) down = null;
    if (!was || was.moved || ptrs.size > 0) return;
    const touch = e.pointerType !== 'mouse';
    const id = nearest(e, touch ? 40 : 26);
    if (!id) {
      active = null;
      pinned = false;
    } else if (touch) {
      active = id;
      pinned = true;
    } else ui.detail = id;
  }
  function pleave(e: PointerEvent) {
    if (e.pointerType === 'mouse' && !pinned && !ptrs.size) active = null;
  }
  function key(e: KeyboardEvent) {
    if (e.target !== plotEl) return;
    const at = active ? order.indexOf(active) : -1;
    let next = at;
    if (e.key === 'ArrowRight') next = Math.min(order.length - 1, at + 1);
    else if (e.key === 'ArrowLeft') next = Math.max(0, at - 1);
    else if (e.key === 'ArrowUp') next = Math.min(order.length - 1, at + 10);
    else if (e.key === 'ArrowDown') next = Math.max(0, at - 10);
    else if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = order.length - 1;
    else if (e.key === '+' || e.key === '=') return zoom(0.7);
    else if (e.key === '-') return zoom(1 / 0.7);
    else if (e.key === '0') return reset();
    else if (e.key === 'Escape') {
      active = null;
      pinned = false;
      return;
    } else if ((e.key === 'Enter' || e.key === ' ') && cur) {
      e.preventDefault();
      ui.detail = cur.id;
      return;
    } else return;
    e.preventDefault();
    if (!order.length) return;
    active = order[Math.max(0, next)];
    pinned = true;
    const p = points.find((q) => q.id === active)!;
    if (!inView(p)) view = null;
  }
  function locate() {
    const q = find.trim().toLowerCase();
    if (!q) return;
    const hit = points.find((p) => p.i.name.toLowerCase() === q) ?? points.find((p) => p.i.name.toLowerCase().includes(q));
    if (!hit) return;
    if (!inView(hit)) view = null;
    active = hit.id;
    pinned = true;
  }

  onMount(() => {
    const fromHash = () => {
      const h = readHash();
      ui.plug = h.get('p') === 'c' ? 'Type-C' : '3.5mm';
      const hx = h.get('x') ?? 'price';
      const hy = h.get('y') ?? 'harman';
      if (axisBy.has(hx) && axisBy.has(hy) && hx !== hy && (hx !== xk || hy !== yk)) setView(hx, hy);
    };
    fromHash();
    ready = true;
    addEventListener('hashchange', fromHash);
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      const r = plotEl.getBoundingClientRect();
      zoom(Math.exp(e.deltaY * 0.0016), (e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height);
    };
    plotEl.addEventListener('wheel', wheel, { passive: false });
    return () => {
      plotEl.removeEventListener('wheel', wheel);
      removeEventListener('hashchange', fromHash);
    };
  });
  $effect(() => {
    const patch = {
      p: ui.plug === 'Type-C' ? 'c' : null,
      x: xk === 'price' ? null : xk,
      y: yk === 'harman' ? null : yk,
    };
    if (ready) writeHash(patch);
  });
  $effect(() => {
    // A plug switch keeps the axes and zoom but drops the highlighted IEM.
    ui.plug;
    active = null;
    pinned = false;
  });
</script>

{#snippet axisEnds(a: Axis)}
  <span class="end" class:good={a.better === 'low'} class:bad={a.better === 'high'}>
    <span aria-hidden="true">←</span>
    {#if a.better !== 'mid'}<b>{a.better === 'low' ? 'Better' : 'Worse'}</b>{/if}
    <span class="word">{a.ends[0]}</span>
  </span>
  <span class="axname">{a.label}{a.scaleNote ? ` · ${a.scaleNote}` : ''}{a.better === 'mid' ? ' · taste, neither side is better' : ''}</span>
  <span class="end" class:good={a.better === 'high'} class:bad={a.better === 'low'}>
    <span class="word">{a.ends[1]}</span>
    {#if a.better !== 'mid'}<b>{a.better === 'high' ? 'Better' : 'Worse'}</b>{/if}
    <span aria-hidden="true">→</span>
  </span>
{/snippet}

{#snippet axisOptions()}
  {#each AXIS_GROUPS as g}
    <optgroup label={g.group}>
      {#each g.axes as a}<option value={a.key}>{a.label}</option>{/each}
    </optgroup>
  {/each}
{/snippet}

<section class="canvas" class:open={open === true} class:closed={open === false} aria-label="Chart of every IEM">
  <h1 class="sr-only">IEM India: every wired IEM under ₹10,000 in India, on one chart</h1>

  <div class="stage">
    <div class="ydir" aria-hidden="true">{@render axisEnds(Y)}</div>
    <div class="yaxis" aria-hidden="true">
      {#each yt as k (k.n)}<span style="top:{pct(k.p)}">{k.label}</span>{/each}
    </div>

    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div
      class="plot"
      class:moving
      class:zoomed
      bind:this={plotEl}
      bind:clientWidth={pw}
      bind:clientHeight={ph}
      role="group"
      tabindex="0"
      aria-label="Scatter chart of {X.label} against {Y.label} for {points.length} {plugLabel(ui.plug)} IEMs. {bestQuad
        ? `${bestQuad.n} are in the best corner: ${bestQuad.label}.`
        : ''} Arrow keys move between IEMs, Enter opens one, plus and minus zoom. The same data is on the See the data page as a table."
      onpointerdown={pdown}
      onpointermove={pmove}
      onpointerup={pup}
      onpointercancel={pup}
      onpointerleave={pleave}
      onkeydown={key}
    >
      <div class="clip">
        {#if shade}
          <div class="shade" style="left:{pct(shade.left)};top:{pct(shade.top)};width:{pct(shade.width)};height:{pct(shade.height)}"></div>
        {/if}
        {#if band}
          <div class="band" style="left:{pct(band.left)};top:{pct(band.top)};width:{pct(band.width)};height:{pct(band.height)}">
            <span>Prefer less bass? Look here</span>
          </div>
        {/if}
        <svg width="100%" height="100%" aria-hidden="true" focusable="false">
          <line class="split" x1={pct(px(t(X, xs)))} x2={pct(px(t(X, xs)))} y1="0" y2="100%" />
          <line class="split" x1="0" x2="100%" y1={pct(py(t(Y, ys)))} y2={pct(py(t(Y, ys)))} />
        </svg>
        {#each points as p (p.id)}
          <i class="d {p.kind} {p.tone}" class:hollow={p.hollow} style="left:{pct(px(p.tx))};top:{pct(py(p.ty))}"></i>
        {/each}
        <span class="splitlabel sx" style="left:{pct(px(t(X, xs)))}">{X.split != null ? 'target' : `median ${X.fmt(xs)}`}</span>
        <span class="splitlabel sy" style="top:{pct(py(t(Y, ys)))}">{Y.split != null ? 'target' : `median ${Y.fmt(ys)}`}</span>
        {#each labels as p, k (p.id)}
          <span class="name n{Math.min(k, 3)}" class:flip={p.flip} style="left:{pct(px(p.tx))};top:{pct(py(p.ty))}">{p.i.name}</span>
        {/each}
        {#each compared as p (p.id)}
          <i class="ring cmp" style="left:{pct(px(p.tx))};top:{pct(py(p.ty))}"></i>
        {/each}
        {#if cur}
          <i class="ring" style="left:{pct(px(cur.tx))};top:{pct(py(cur.ty))}"></i>
        {/if}
      </div>

      {#each quads as q (q.pos)}
        <span class="q {q.pos}" class:best={q.best}>
          {q.label}
          <b>{q.n}</b>
          {#if q.best}<em>Best corner</em>{/if}
        </span>
      {/each}

      {#if cur && inView(cur)}
        {@const src = photo(cur.i, 240)}
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
          class="tip card"
          class:right={px(cur.tx) > 52}
          class:below={py(cur.ty) < 48}
          style="left:{pct(px(cur.tx))};top:{pct(py(cur.ty))}"
          onpointerdown={(e) => e.stopPropagation()}
          onpointerup={(e) => e.stopPropagation()}
        >
          {#key cur.id}
            <span class="ph">
              {#if src}
                <img {src} alt="Product photo of {cur.i.name}" width="104" height="104" onerror={(e) => (e.currentTarget.style.display = 'none')} />
              {:else}
                <span class="noph">No photo</span>
              {/if}
            </span>
          {/key}
          <span class="tx">
            <strong>{cur.i.name}</strong>
            <span class="price">{inr(cur.i.price_inr)}</span>
            {#if yk !== 'price'}<span>{Y.label}: <b>{Y.fmt(cur.yv)}</b></span>{/if}
            {#if xk !== 'price'}<span>{X.label}: <b>{X.fmt(cur.xv)}</b></span>{/if}
            <span class="muted">{status(cur.i)}</span>
            {#if src}<span class="muted credit">Photo: {storeName(cur.i.cheapest_store)}</span>{/if}
          </span>
          {#if pinned}
            <span class="acts">
              <button class="btn sm" type="button" onclick={() => (ui.detail = cur.id)}>Details</button>
              <button
                class="btn sm ghost"
                type="button"
                aria-pressed={ui.compare.includes(cur.id)}
                disabled={!ui.compare.includes(cur.id) && ui.compare.length >= MAX_COMPARE}
                onclick={() => toggleCompare(cur.id)}>{ui.compare.includes(cur.id) ? 'Remove' : 'Compare'}</button
              >
            </span>
          {:else}
            <span class="hint muted">Click the dot for details</span>
          {/if}
        </div>
      {/if}
    </div>

    <div class="xaxis" aria-hidden="true">
      {#each xt as k (k.n)}<span style="left:{pct(k.p)}">{k.label}</span>{/each}
    </div>
    <div class="xdir" aria-hidden="true">{@render axisEnds(X)}</div>
  </div>

  <p class="sr-only" aria-live="polite">
    {cur ? `${cur.i.name}. ${inr(cur.i.price_inr)}. ${Y.label} ${Y.fmt(cur.yv)}. ${X.label} ${X.fmt(cur.xv)}. ${status(cur.i)}.` : ''}
  </p>

  <button class="handle" type="button" aria-label="{plugLabel(ui.plug)}, open the controls" onclick={() => (open = true)}>
    <svg viewBox="0 0 16 16" width="18" height="18" aria-hidden="true"><path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" /></svg>
    <span>{plugLabel(ui.plug)}</span>
  </button>

  <aside class="panel" aria-label="Chart controls">
    <div class="phead">
      <button class="back" type="button" aria-label="Hide the controls" onclick={() => (open = false)}>
        <svg viewBox="0 0 16 16" width="20" height="20" aria-hidden="true"><path d="M10 3 5 8l5 5" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" /></svg>
      </button>
      <span class="count"><b>{points.length}</b> IEMs on the chart</span>
    </div>

    <div class="plugs" role="group" aria-label="Plug type">
      {#each PLUGS as p}
        <button type="button" aria-pressed={ui.plug === p} onclick={() => (ui.plug = p)}>
          {plugLabel(p)} <span class="n">{plugCount[p]}</span>
        </button>
      {/each}
    </div>

    <form
      class="find"
      role="search"
      onsubmit={(e) => {
        e.preventDefault();
        locate();
      }}
    >
      <label class="sr-only" for="cv-find">Find an IEM on the chart</label>
      <input id="cv-find" type="search" list="cv-names" placeholder="Find an IEM" bind:value={find} onchange={locate} autocomplete="off" />
      <datalist id="cv-names">
        {#if ready}{#each points as p (p.id)}<option value={p.i.name}></option>{/each}{/if}
      </datalist>
    </form>

    <div class="group">
      <h2>Axes</h2>
      <label class="pick">
        <span>Up the side</span>
        <select value={yk} onchange={(e) => setAxis('y', e.currentTarget.value)}>{@render axisOptions()}</select>
      </label>
      <button class="swap" type="button" onclick={() => setView(yk, xk)}>
        <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true"
          ><path d="M7 4v11l-3-3M13 16V5l3 3" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg
        >
        Swap the two
      </button>
      <label class="pick">
        <span>Along the bottom</span>
        <select value={xk} onchange={(e) => setAxis('x', e.currentTarget.value)}>{@render axisOptions()}</select>
      </label>
    </div>

    <div class="group">
      <h2>Ready-made views</h2>
      <div class="views" role="group" aria-label="Ready-made views">
        {#each VIEWS as w}
          <button type="button" class="chip" aria-pressed={xk === w.x && yk === w.y} onclick={() => setView(w.x, w.y)}>{w.label}</button>
        {/each}
      </div>
    </div>

    <div class="group">
      <h2>Show</h2>
      <div class="legend" role="group" aria-label="Show or hide kinds of IEM">
        <button type="button" aria-pressed={show.stock} onclick={() => (show.stock = !show.stock)}><i class="d measured muted"></i>In stock</button>
        <button type="button" aria-pressed={show.sold} onclick={() => (show.sold = !show.sold)}><i class="d measured muted hollow"></i>Sold out</button>
        <button type="button" aria-pressed={show.proxy} onclick={() => (show.proxy = !show.proxy)}><i class="d proxy muted"></i>Proxy</button>
        {#if hasNone}
          <button type="button" aria-pressed={show.none} onclick={() => (show.none = !show.none)}><i class="d none muted"></i>Not measured</button>
        {/if}
      </div>
      <p class="fine muted">Proxy means only the base model was measured.</p>
    </div>

    <div class="group read">
      <h2>Reading this view</h2>
      <p>{insight}</p>
      <p class="muted">{meta.disclaimers[1]}</p>
      {#if left > 0}
        <p class="muted">{left} {plugLabel(ui.plug)} IEMs have no value for these axes, so they are not drawn.</p>
      {/if}
      <p><a href="/data">See the data as a table</a></p>
    </div>
  </aside>

  <div class="zoom" role="group" aria-label="Zoom">
    <button type="button" aria-label="Zoom in" onclick={() => zoom(0.6)}>+</button>
    <button type="button" aria-label="Zoom out" disabled={!zoomed} onclick={() => zoom(1 / 0.6)}>−</button>
    {#if zoomed}<button type="button" class="txt" onclick={() => (view = null)}>Reset</button>{/if}
  </div>
</section>

<style>
  .canvas {
    --panel: 19rem;
    --inset: 0.5rem;
    position: relative;
    height: calc(100dvh - 3.45rem);
    min-height: 30rem;
    overflow: hidden;
    background: var(--surface);
  }
  @media (min-width: 900px) {
    .canvas:not(.closed) {
      --inset: calc(var(--panel) + 0.75rem);
    }
  }
  /* Room for the handle that reopens the controls. */
  @media (max-width: 899px) {
    .canvas .stage {
      top: 3.9rem;
    }
  }
  .canvas.closed .stage {
    top: 3.9rem;
  }

  /* The chart fills the whole area; the controls float over it. */
  .stage {
    position: absolute;
    inset: 0.6rem 0.75rem 0.4rem var(--inset);
    display: grid;
    grid-template-columns: 1.35rem 2.3rem minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr) 1.25rem 1.5rem;
    transition: left 0.3s ease;
  }
  .ydir,
  .xdir {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.75rem;
    color: var(--muted);
    white-space: nowrap;
    min-width: 0;
    min-height: 0;
  }
  .ydir {
    flex-direction: column-reverse;
  }
  .ydir > :global(*) {
    writing-mode: vertical-rl;
    transform: rotate(180deg);
  }
  .xdir {
    grid-column: 3;
  }
  .end {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-weight: 500;
  }
  .end b {
    font-weight: 700;
  }
  .end.good {
    color: var(--accent-ink);
  }
  .end.good b {
    padding: 0 0.35rem;
    border-radius: 4px;
    background: var(--accent-soft);
  }
  .ydir .end.good b {
    padding: 0.35rem 0;
  }
  .axname {
    display: none;
    font-weight: 700;
    color: var(--ink);
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .yaxis,
  .xaxis {
    position: relative;
    font-size: 0.7rem;
    color: var(--muted);
  }
  .yaxis span {
    position: absolute;
    right: 0.3rem;
    transform: translateY(-50%);
  }
  .xaxis {
    grid-column: 3;
  }
  .xaxis span {
    position: absolute;
    top: 0.15rem;
    transform: translateX(-50%);
    white-space: nowrap;
  }

  .plot {
    position: relative;
    min-height: 0;
    cursor: crosshair;
    touch-action: none;
    user-select: none;
    -webkit-user-select: none;
    -webkit-tap-highlight-color: transparent;
  }
  .plot.zoomed {
    cursor: grab;
  }
  .plot.moving {
    cursor: grabbing;
  }
  .clip {
    position: absolute;
    inset: 0;
    overflow: hidden;
    border-left: 1.5px solid var(--line);
    border-bottom: 1.5px solid var(--line);
  }
  .clip svg {
    position: absolute;
    inset: 0;
    display: block;
  }
  .shade,
  .band {
    position: absolute;
    pointer-events: none;
  }
  .shade {
    background: var(--accent);
    opacity: 0.12;
    transition: all 0.4s ease;
  }
  .band {
    background: color-mix(in srgb, var(--teal) 13%, transparent);
    display: grid;
    place-items: end center;
    overflow: hidden;
  }
  .band span {
    margin: 0 0 28%;
    writing-mode: vertical-rl;
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--teal);
    white-space: nowrap;
  }
  .split {
    stroke: var(--ink);
    stroke-width: 1;
    stroke-dasharray: 2 5;
    opacity: 0.6;
  }
  .splitlabel {
    position: absolute;
    padding: 0 0.3rem;
    border-radius: 4px;
    font-size: 0.68rem;
    font-weight: 600;
    white-space: nowrap;
    color: var(--muted);
    background: color-mix(in srgb, var(--surface) 85%, transparent);
    pointer-events: none;
  }
  .splitlabel.sx {
    bottom: 12%;
    transform: translateX(-50%) rotate(180deg);
    writing-mode: vertical-rl;
    padding: 0.3rem 0;
  }
  .splitlabel.sy {
    right: 4rem;
    transform: translateY(-50%);
  }

  /* Dots. Shape carries the measurement status, fill carries stock, so colour is never alone. */
  .d {
    position: absolute;
    width: 9px;
    height: 9px;
    margin: -4.5px 0 0 -4.5px;
    border-radius: 50%;
    border: 1px solid var(--surface);
    background: var(--dot);
    opacity: 0.88;
    pointer-events: none;
    transition:
      left 0.55s cubic-bezier(0.3, 0.7, 0.2, 1),
      top 0.55s cubic-bezier(0.3, 0.7, 0.2, 1),
      background-color 0.3s;
  }
  .moving .d,
  .moving .name {
    transition: none;
  }
  .d.accent {
    background: var(--accent);
    border-color: var(--accent-ink);
  }
  .d.teal {
    background: var(--teal);
  }
  .d.hollow {
    background: var(--surface);
    border: 1.6px solid var(--dot);
  }
  .d.hollow.accent {
    border-color: var(--accent-ink);
  }
  .d.hollow.teal {
    border-color: var(--teal);
  }
  .d.proxy {
    border-radius: 1px;
    transform: rotate(45deg) scale(0.92);
  }
  .d.none {
    width: 11px;
    height: 10px;
    margin: -5px 0 0 -5.5px;
    border: 0;
    border-radius: 0;
    clip-path: polygon(50% 0, 100% 100%, 0 100%);
  }
  .d.none.hollow {
    background: linear-gradient(var(--surface), var(--surface)) center 70% / 5px 4px no-repeat, var(--dot);
    border: 0;
  }
  /* Names of a few standout IEMs, written straight onto the canvas. */
  .name {
    position: absolute;
    transform: translate(9px, -50%);
    font-size: 0.74rem;
    font-weight: 600;
    line-height: 1;
    white-space: nowrap;
    color: var(--ink);
    text-shadow:
      0 0 3px var(--surface),
      0 0 3px var(--surface),
      0 0 6px var(--surface);
    pointer-events: none;
    transition:
      left 0.55s cubic-bezier(0.3, 0.7, 0.2, 1),
      top 0.55s cubic-bezier(0.3, 0.7, 0.2, 1);
  }
  .name.flip {
    transform: translate(calc(-100% - 9px), -50%);
  }
  .name.n0 {
    font-size: 1.05rem;
  }
  .name.n1,
  .name.n2 {
    font-size: 0.9rem;
  }
  .ring {
    position: absolute;
    width: 20px;
    height: 20px;
    margin: -10px 0 0 -10px;
    border: 2.4px solid var(--ink);
    border-radius: 50%;
    pointer-events: none;
  }
  .ring.cmp {
    width: 17px;
    height: 17px;
    margin: -8.5px 0 0 -8.5px;
    border: 2px dashed var(--teal);
  }

  .q {
    position: absolute;
    max-width: 44%;
    padding: 0.15rem 0.4rem;
    font-size: 0.72rem;
    font-weight: 600;
    line-height: 1.25;
    color: var(--muted);
    background: color-mix(in srgb, var(--surface) 78%, transparent);
    border-radius: 4px;
    pointer-events: none;
  }
  .q b {
    display: block;
    font-family: var(--display);
    font-size: 1.15rem;
    color: var(--ink);
  }
  .q em {
    display: inline-block;
    margin-top: 0.1rem;
    padding: 0 0.4rem;
    border-radius: 999px;
    background: var(--ink);
    color: var(--bg);
    font-style: normal;
    font-size: 0.68rem;
  }
  .q.best {
    color: var(--accent-ink);
  }
  .q.tl {
    top: 5px;
    left: 7px;
  }
  .q.tr {
    top: 5px;
    right: 5px;
    text-align: right;
  }
  .q.bl {
    bottom: 7px;
    left: 7px;
  }
  .q.br {
    bottom: 7px;
    right: 5px;
    text-align: right;
  }

  .tip {
    position: absolute;
    z-index: 5;
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 0.5rem 0.65rem;
    width: max-content;
    max-width: min(20rem, 78vw);
    padding: 0.55rem;
    font-size: 0.8rem;
    line-height: 1.35;
    background: var(--raised);
    box-shadow: var(--shadow);
    transform: translate(14px, calc(-100% - 12px));
    cursor: default;
    user-select: text;
    -webkit-user-select: text;
  }
  .tip.right {
    transform: translate(calc(-100% - 14px), calc(-100% - 12px));
  }
  .tip.below {
    transform: translate(14px, 14px);
  }
  .tip.right.below {
    transform: translate(calc(-100% - 14px), 14px);
  }
  .ph {
    display: grid;
    place-items: center;
    width: 104px;
    height: 104px;
    border-radius: 6px;
    background: #fff;
    border: 1px solid var(--line);
    overflow: hidden;
  }
  .ph img {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }
  .noph {
    font-size: 0.7rem;
    color: #645c50;
  }
  .tx {
    display: grid;
    align-content: start;
    gap: 0.1rem;
    min-width: 0;
  }
  .tx strong {
    font-size: 0.9rem;
    line-height: 1.2;
  }
  .tx .price {
    font-family: var(--display);
    font-size: 1.05rem;
    font-weight: 600;
  }
  .credit {
    font-size: 0.68rem;
  }
  .acts,
  .hint {
    grid-column: 1 / -1;
    display: flex;
    gap: 0.4rem;
  }
  .hint {
    font-size: 0.72rem;
  }

  /* Controls: fixed to the left wall, floating on the right edge. */
  .panel {
    position: absolute;
    z-index: 8;
    left: 0;
    top: 0.75rem;
    bottom: 0.75rem;
    width: min(var(--panel), 88vw);
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 0.8rem 1rem 1rem;
    overflow-y: auto;
    overscroll-behavior: contain;
    background: var(--raised);
    border: 1px solid var(--line);
    border-left: 0;
    border-radius: 0 16px 16px 0;
    box-shadow: var(--shadow), 10px 0 30px rgb(0 0 0 / 0.12);
    transition:
      transform 0.3s ease,
      visibility 0.3s;
    transform: translateX(-102%);
    visibility: hidden;
  }
  .handle {
    position: absolute;
    z-index: 7;
    left: 0;
    top: 0.75rem;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    min-height: 2.75rem;
    padding: 0 0.8rem 0 0.5rem;
    border: 1px solid var(--line);
    border-left: 0;
    border-radius: 0 999px 999px 0;
    background: var(--raised);
    box-shadow: var(--shadow);
    font-family: var(--display);
    font-weight: 650;
  }
  .canvas.open .panel {
    transform: none;
    visibility: visible;
  }
  .canvas.open .handle {
    visibility: hidden;
  }
  @media (min-width: 900px) {
    .canvas:not(.closed) .panel {
      transform: none;
      visibility: visible;
    }
    .canvas:not(.closed) .handle {
      visibility: hidden;
    }
  }
  .phead {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin: -0.2rem 0 -0.3rem -0.5rem;
  }
  .back {
    display: grid;
    place-items: center;
    width: 2.75rem;
    height: 2.75rem;
    border: 0;
    border-radius: 999px;
    background: none;
  }
  .count {
    font-size: 0.85rem;
    color: var(--muted);
  }
  .count b {
    font-family: var(--display);
    font-size: 1.2rem;
    color: var(--ink);
  }
  .plugs {
    display: flex;
    padding: 3px;
    gap: 2px;
    border: 1.5px solid var(--ink);
    border-radius: 999px;
    background: var(--surface);
  }
  .plugs button {
    flex: 1;
    border: 0;
    background: none;
    border-radius: 999px;
    min-height: 2.6rem;
    padding: 0.3rem 0.5rem;
    font-family: var(--display);
    font-size: 1.1rem;
    font-weight: 650;
    white-space: nowrap;
    color: var(--muted);
  }
  .plugs button[aria-pressed='true'] {
    background: var(--accent);
    color: #1d1a16;
  }
  .plugs .n {
    font-family: var(--body);
    font-size: 0.78rem;
    font-weight: 500;
    opacity: 0.8;
  }
  .group {
    display: grid;
    gap: 0.45rem;
    padding-top: 0.9rem;
    border-top: 1px solid var(--line);
  }
  .group h2 {
    margin: 0;
    font-family: var(--body);
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent-ink);
  }
  .pick {
    display: grid;
    gap: 0.15rem;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--muted);
  }
  select,
  .find input {
    width: 100%;
    min-height: 2.6rem;
    padding: 0.3rem 0.6rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface);
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--ink);
  }
  .find input {
    font-weight: 500;
  }
  .swap {
    justify-self: start;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    min-height: 2.25rem;
    padding: 0 0.7rem 0 0.5rem;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: none;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--muted);
  }
  .views {
    display: grid;
    gap: 0.3rem;
  }
  .chip {
    min-height: 2.5rem;
    padding: 0.2rem 0.8rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: none;
    font-size: 0.9rem;
    font-weight: 600;
    text-align: left;
    color: var(--muted);
  }
  .chip[aria-pressed='true'] {
    border-color: var(--ink);
    background: var(--ink);
    color: var(--bg);
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
  }
  .legend button {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    min-height: 2.25rem;
    padding: 0.1rem 0.65rem;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface);
    font-size: 0.8rem;
    font-weight: 600;
  }
  .legend button[aria-pressed='false'] {
    background: none;
    border-style: dashed;
    color: var(--muted);
    text-decoration: line-through;
  }
  .legend .d {
    position: static;
    margin: 0;
    flex: none;
  }
  .fine,
  .read p {
    margin: 0;
    font-size: 0.8rem;
    line-height: 1.45;
  }
  .read a {
    font-weight: 600;
  }

  .zoom {
    position: absolute;
    z-index: 6;
    right: 0.75rem;
    top: 50%;
    transform: translateY(-50%);
    display: grid;
    gap: 4px;
    justify-items: end;
  }
  .zoom button {
    width: 2.6rem;
    height: 2.6rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--raised);
    box-shadow: var(--shadow);
    font-weight: 700;
    font-size: 1.2rem;
  }
  .zoom .txt {
    width: auto;
    padding: 0 0.6rem;
    font-size: 0.8rem;
  }
  .zoom button:disabled {
    opacity: 0.45;
    cursor: default;
  }
  @media (max-width: 699px) {
    /* On a phone the card docks to the half of the chart the dot is not in. */
    .tip,
    .tip.right,
    .tip.below,
    .tip.right.below {
      left: 6px !important;
      right: 6px;
      top: 6px !important;
      bottom: auto;
      width: auto;
      max-width: none;
      transform: none;
    }
    .tip.below,
    .tip.right.below {
      top: auto !important;
      bottom: 6px;
    }
    .end.good .word,
    .end.bad .word {
      display: none;
    }
    .name.n0 {
      font-size: 0.9rem;
    }
    .name.n1,
    .name.n2 {
      font-size: 0.8rem;
    }
  }
  @media (min-width: 700px) {
    .axname {
      display: block;
    }
    .q {
      font-size: 0.82rem;
    }
    .q b {
      font-size: 1.5rem;
    }
    .stage {
      grid-template-columns: 1.5rem 2.6rem minmax(0, 1fr);
    }
  }
</style>
