<script lang="ts">
  // A scrolling story. One set of dots stays on screen and rearranges itself as the reader scrolls.
  // Two colours only: ink for everything, red for the one thing each step is about.
  import { onMount } from 'svelte';
  import { charted, headlinePair, inr, inStock, median, photo, PLUGS, plugLabel, PRICE_BANDS, r2Text, type Plug } from '../lib/data';
  import { axisBy } from '../lib/axes';

  const P = axisBy.get('price')!;
  const H = axisBy.get('harman')!;
  const all = [...charted('3.5mm'), ...charted('Type-C')];
  type Row = (typeof all)[number];
  const story = all.filter((i) => i.plug === '3.5mm');
  const N = story.length;
  const lo = Math.min(...story.map((i) => i.price_inr));
  const hi = Math.max(...story.map((i) => i.price_inr));
  const mPrice = median(story.map((i) => i.price_inr));
  const mScore = median(story.map((i) => i.harman_score!));
  // The four corners of the price-vs-sound chart, split at the middle price and middle score.
  type Quad = 'buy' | 'treat' | 'backup' | 'skip';
  const quadOf = (i: Row): Quad => {
    const cheap = i.price_inr <= mPrice;
    const great = i.harman_score! >= mScore;
    return great ? (cheap ? 'buy' : 'treat') : cheap ? 'backup' : 'skip';
  };
  const qCount = (q: Quad) => story.filter((i) => quadOf(i) === q).length;
  const QUADS: { q: Quad; step: number; stamp: string; cheap: boolean; great: boolean }[] = [
    { q: 'buy', step: 5, stamp: 'Buy first', cheap: true, great: true },
    { q: 'treat', step: 6, stamp: 'If money is spare', cheap: false, great: true },
    { q: 'backup', step: 7, stamp: 'Backup pair', cheap: true, great: false },
    { q: 'skip', step: 8, stamp: 'Skip', cheap: false, great: false },
  ];
  const nBest = qCount('buy');
  const pair = headlinePair('3.5mm');
  const r2 = r2Text('3.5mm');
  const r2pct = `${+(Number(r2) * 100).toFixed(1)}%`;
  const bandOf = (p: number) => PRICE_BANDS.findIndex((b) => p >= b.lo && p < b.hi);
  const bands = PRICE_BANDS.map((b, k) => {
    const r = story.filter((i) => bandOf(i.price_inr) === k);
    return { ...b, n: r.length, med: median(r.map((i) => i.harman_score!)) };
  });

  // A fixed, repeatable scatter for the opening screen.
  const seeded = (k: number) => {
    const x = Math.sin(k * 12.9898 + 78.233) * 43758.5453;
    return x - Math.floor(x);
  };

  let w = $state(390);
  let h = $state(760);
  let step = $state(0);
  let reduce = $state(false);
  // Dots stay hidden until the real screen size is known, so they never fly in from a guessed layout.
  let ready = $state(false);

  // The playground at the end.
  let plug = $state<Plug>('3.5mm');
  let budget = $state(3000);
  let taste = $state<'any' | 'bass' | 'less'>('any');
  const TASTES = [
    { k: 'any', label: 'Any sound' },
    { k: 'bass', label: 'More bass' },
    { k: 'less', label: 'Less bass' },
  ] as const;

  const wide = $derived(w >= 900);
  const r = $derived(wide ? 5 : 3.6);
  const play = $derived(step === 11);
  const curQuad = $derived(QUADS.find((q) => q.step === step) ?? null);
  const box = $derived(
    wide
      ? { l: w * 0.44, r: w - 56, t: 100, b: h - 80 }
      : { l: 44, r: w - 20, t: 78, b: Math.round(h * (play ? 0.47 : 0.55)) },
  );

  const tx = (p: number) => P.fwd!(p);
  const ty = (s: number) => H.fwd!(s);
  const allP = all.map((i) => i.price_inr);
  const xd = [tx(Math.min(...allP) * 0.9), tx(Math.max(...allP) * 1.08)];
  const ydVals = all.map((i) => ty(i.harman_score!));
  const yd = [Math.min(...ydVals) - 0.08, Math.max(...ydVals) + 0.08];
  const X = (p: number) => box.l + ((tx(p) - xd[0]) / (xd[1] - xd[0])) * (box.r - box.l);
  const Y = (s: number) => box.b - ((ty(s) - yd[0]) / (yd[1] - yd[0])) * (box.b - box.t);

  /** Push dots apart along one axis so none overlap; the other axis keeps its true value. */
  function swarm(pts: { id: string; fix: number }[], gap: number) {
    const placed: { fix: number; off: number }[] = [];
    const out = new Map<string, number>();
    for (const p of [...pts].sort((a, b) => a.fix - b.fix)) {
      let off = 0;
      for (let n = 0; n < 400; n++) {
        off = n === 0 ? 0 : (n % 2 ? 1 : -1) * Math.ceil(n / 2) * gap * 0.55;
        if (placed.every((q) => Math.abs(q.fix - p.fix) >= gap || (q.fix - p.fix) ** 2 + (q.off - off) ** 2 >= gap * gap)) break;
      }
      placed.push({ fix: p.fix, off });
      out.set(p.id, off);
    }
    return out;
  }

  const lineUp = $derived.by(() => swarm(story.map((i) => ({ id: i.id, fix: X(i.price_inr) })), r * 2.1));
  const colW = $derived((box.r - box.l) / 3);
  const columns = $derived.by(() => {
    const out = new Map<string, number>();
    for (let b = 0; b < 3; b++) {
      const s = swarm(
        story.filter((i) => bandOf(i.price_inr) === b).map((i) => ({ id: i.id, fix: Y(i.harman_score!) })),
        r * 2.1,
      );
      for (const [id, off] of s) out.set(id, box.l + colW * (b + 0.5) + Math.max(-colW * 0.46, Math.min(colW * 0.46, off)));
    }
    return out;
  });

  const fits = (i: Row) =>
    i.plug === plug &&
    inStock(i) &&
    i.measurement_status === 'measured' &&
    i.price_inr <= budget &&
    (taste === 'any' || (taste === 'bass' ? i.tilt_slope! < -0.1 : i.tilt_slope! > 0.1));
  const matches = $derived(all.filter(fits));
  const picks = $derived([...matches].sort((a, b) => b.score_default - a.score_default).slice(0, 3));
  const rankOf = $derived(new Map(picks.map((i, k) => [i.id, k + 1])));

  const INK = 'var(--ink)';
  const RED = 'var(--red)';
  const FAINT = 'var(--faint)';

  const dots = $derived(
    all.map((i, k) => {
      const inStory = i.plug === '3.5mm';
      let x = X(i.price_inr);
      let y = Y(i.harman_score!);
      let c = INK;
      let o = inStory ? 0.72 : 0;
      let s = 1;
      if (step === 0) {
        x = 16 + seeded(k) * (w - 32);
        y = 16 + seeded(k + 999) * (h - 32);
        o = inStory ? 0.12 + seeded(k + 3) * 0.3 : 0;
        s = 1.3;
      } else if (step === 1 || step === 2) {
        if (inStory) y = (box.t + box.b) / 2 + (lineUp.get(i.id) ?? 0);
        if (step === 2) o = 0;
      } else if (step === 4) {
        o = inStory ? 0.28 : 0;
      } else if (curQuad) {
        const mine = inStory && quadOf(i) === curQuad.q;
        c = mine ? RED : FAINT;
        o = inStory ? 1 : 0;
      } else if (step === 9) {
        const hit = i.id === pair.cheap.id || i.id === pair.pricey.id;
        c = i.id === pair.cheap.id ? RED : hit ? INK : FAINT;
        s = hit ? 2.6 : 1;
        o = inStory ? 1 : 0;
      } else if (step === 10) {
        if (inStory) x = columns.get(i.id) ?? x;
      } else if (step === 11) {
        const ok = fits(i);
        c = rankOf.has(i.id) ? RED : ok ? INK : FAINT;
        s = rankOf.has(i.id) ? 2.4 : 1;
        o = i.plug === plug ? (ok ? 0.9 : 1) : 0;
      }
      // Dots set off left to right, so each change ripples across the screen.
      const delay = reduce ? 0 : Math.round(((x - box.l) / Math.max(1, w)) * 450 + seeded(k + 7) * 150);
      return { id: i.id, x, y, c, o, s, delay };
    }),
  );

  const xTicks = [500, 1000, 2000, 5000, 10000];
  const yTicks = [40, 60, 70, 80, 90];
  const showX = $derived(step >= 1 && step !== 2 && step !== 10);
  const showY = $derived(step >= 3);
  const showMid = $derived(step >= 5 && step <= 8);
  const quadRect = (q: (typeof QUADS)[number]) => {
    const mx = X(mPrice);
    const my = Y(mScore);
    return {
      x: q.cheap ? box.l : mx,
      y: q.great ? box.t : my,
      w: Math.max(0, q.cheap ? mx - box.l : box.r - mx),
      h: Math.max(0, q.great ? my - box.t : box.b - my),
    };
  };

  // A made-up frequency response, only to show what the score looks at. Not data.
  const target = (t: number) =>
    0.42 + 0.16 / (1 + Math.exp((t - 0.22) * 22)) + 0.17 * Math.exp(-(((t - 0.68) / 0.09) ** 2)) - 0.5 * Math.max(0, t - 0.86);
  const earphone = (t: number) => target(t) + 0.2 * (0.5 - t) + 0.06 * Math.sin(t * 26) * t * 1.3 + 0.03;
  const curve = (f: (t: number) => number) =>
    Array.from({ length: 80 }, (_, k) => k / 79)
      .map((t, k) => `${k ? 'L' : 'M'}${(box.l + t * (box.r - box.l)).toFixed(1)} ${cy(f(t)).toFixed(1)}`)
      .join(' ');
  const cx = (t: number) => box.l + t * (box.r - box.l);
  const cy = (v: number) => box.b - ((v - 0.18) / 0.72) * (box.b - box.t);

  // Least-squares line of score on ln(price), sampled so it bends with the axis scale.
  const fit = (() => {
    const a = story.map((i) => Math.log(i.price_inr));
    const b = story.map((i) => i.harman_score!);
    const ma = a.reduce((s, v) => s + v, 0) / a.length;
    const mb = b.reduce((s, v) => s + v, 0) / b.length;
    let sab = 0;
    let saa = 0;
    for (let k = 0; k < a.length; k++) {
      sab += (a[k] - ma) * (b[k] - mb);
      saa += (a[k] - ma) ** 2;
    }
    return (p: number) => mb + (sab / saa) * (Math.log(p) - ma);
  })();
  const path = (f: (p: number) => number) =>
    Array.from({ length: 24 }, (_, k) => lo * (hi / lo) ** (k / 23))
      .map((p, k) => `${k ? 'L' : 'M'}${X(p).toFixed(1)} ${Y(f(p)).toFixed(1)}`)
      .join(' ');
  const expectPath = $derived(path((p) => 52 + (40 * Math.log(p / lo)) / Math.log(hi / lo)));
  const fitPath = $derived(path(fit));
  const at = (i: Row) => ({ x: X(i.price_inr), y: Y(i.harman_score!) });

  let stepsEl: HTMLDivElement;
  onMount(() => {
    reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    // The active step is the last section whose top has passed a line across the screen.
    // Reading positions on every scroll keeps it right even after a jump (a link, a refresh mid-page).
    const sections = [...stepsEl.querySelectorAll<HTMLElement>('[data-step]')];
    const update = () => {
      const line = innerHeight * (innerWidth >= 900 ? 0.5 : 0.7);
      let cur = 0;
      for (const el of sections) if (el.getBoundingClientRect().top <= line) cur = Number(el.dataset.step);
      step = cur;
    };
    update();
    addEventListener('scroll', update, { passive: true });
    addEventListener('resize', update);
    requestAnimationFrame(() => requestAnimationFrame(() => (ready = true)));
    return () => {
      removeEventListener('scroll', update);
      removeEventListener('resize', update);
    };
  });
</script>

<div class="story" class:wide class:play class:ready>
  <div class="stage" bind:clientWidth={w} bind:clientHeight={h} aria-hidden="true">
    <svg class="lines" width={w} height={h}>
      {#if showY}
        {#each yTicks as t}
          <line class="grid" x1={box.l} x2={box.r} y1={Y(t)} y2={Y(t)} />
        {/each}
      {/if}
      {#each QUADS as q}
        {@const rr = quadRect(q)}
        <rect class="best" class:on={curQuad?.q === q.q} x={rr.x} y={rr.y} width={rr.w} height={rr.h} />
      {/each}
      <line class="mid" class:on={showMid} x1={X(mPrice)} x2={X(mPrice)} y1={box.t} y2={box.b} />
      <line class="mid" class:on={showMid} x1={box.l} x2={box.r} y1={Y(mScore)} y2={Y(mScore)} />
      <path class="expect" class:on={step === 4} d={expectPath} />
      <path class="fit" class:on={step === 4} d={fitPath} pathLength="1" />

      <g class="explain" class:on={step === 2}>
        <line class="ax" x1={box.l} x2={box.r} y1={box.b} y2={box.b} />
        <path class="tgt" d={curve(target)} />
        <path class="ear" d={curve(earphone)} pathLength="1" />
        <line class="gap" x1={cx(0.45)} x2={cx(0.45)} y1={cy(target(0.45))} y2={cy(earphone(0.45))} />
      </g>
      {#each bands as b, k}
        <line class="med" class:on={step === 10} x1={box.l + colW * k + 6} x2={box.l + colW * (k + 1) - 6} y1={Y(b.med)} y2={Y(b.med)} />
      {/each}
    </svg>

    {#each dots as d (d.id)}
      <i
        class="dot"
        class:float={step === 0}
        style="width:{r * 2}px;height:{r * 2}px;margin:{-r}px 0 0 {-r}px;transform:translate({d.x}px,{d.y}px) scale({d.s});background:{d.c};opacity:{d.o};transition-delay:{d.delay}ms"
      ></i>
    {/each}

    <div class="axis x" class:on={showX}>
      {#each xTicks as t}<span style="left:{X(t)}px;top:{box.b + 10}px">{t >= 1000 ? `₹${t / 1000}k` : `₹${t}`}</span>{/each}
      <b style="left:{box.r}px;top:{box.b + 28}px">Pricier →</b>
    </div>
    <div class="axis y" class:on={showY}>
      {#each yTicks as t}<span style="left:{box.l - 8}px;top:{Y(t)}px">{t}</span>{/each}
      <b style="left:{box.l}px;top:{box.t - 26}px">↑ Better sound</b>
    </div>

    <div class="note" class:on={step === 4} style="left:{X(hi * 0.5)}px;top:{Y(91)}px">What you'd expect</div>
    <div class="note red fitnote" class:on={step === 4} style="left:{X(hi)}px;top:{Y(fit(hi)) + 10}px">What actually happens</div>

    {#each QUADS as q}
      {@const rr = quadRect(q)}
      <div
        class="stamp"
        class:on={curQuad?.q === q.q}
        class:r={!q.cheap}
        class:b={!q.great}
        style="left:{q.cheap ? rr.x + 10 : rr.x + rr.w - 10}px;top:{q.great ? rr.y + 10 : rr.y + rr.h - 10}px"
      >
        <b>{qCount(q.q)}</b><span>{q.stamp}</span>
      </div>
    {/each}
    <span class="midlab" class:on={showMid} style="left:{X(mPrice)}px;top:{box.t + 2}px">middle price {inr(mPrice)}</span>
    <span class="midlab y" class:on={showMid} style="left:{box.r}px;top:{Y(mScore)}px">middle score {mScore.toFixed(1)}</span>

    <div class="xlabels" class:on={step === 2}>
      <span class="lab" style="left:{cx(0.02)}px;top:{box.b + 8}px">Bass</span>
      <span class="lab rt" style="left:{cx(0.98)}px;top:{box.b + 8}px">Treble</span>
      <span class="lab tag" style="left:{cx(0.98)}px;top:{cy(target(0.68)) - 34}px">The target most people like</span>
      <span class="lab tag red" style="left:{cx(0.1)}px;top:{cy(earphone(0.1)) - 26}px">One earphone</span>
      <span class="call c1" style="left:{cx(0.02)}px;top:{cy(target(0.2)) + 36}px"><b>1</b> Leans warm or bright</span>
      <span class="call c2" style="left:{cx(0.98)}px;top:{box.b - 34}px"><b>2</b> Bumps and dips</span>
      <span class="call c3" style="left:{cx(0.47)}px;top:{(cy(target(0.45)) + cy(earphone(0.45))) / 2}px"><b>3</b> How far off overall</span>
    </div>

    {#each [{ i: pair.cheap, cls: 'cheap' }, { i: pair.pricey, cls: 'pricey' }] as c}
      {@const p = at(c.i)}
      <div class="callout {c.cls}" class:on={step === 9} class:flip={p.x > w * 0.6} style="left:{p.x}px;top:{p.y}px">
        {#if photo(c.i, 160)}<img src={photo(c.i, 160)} alt="" width="52" height="52" loading="lazy" />{/if}
        <span><strong>{c.i.name}</strong>{inr(c.i.price_inr)} · scores {c.i.harman_score!.toFixed(1)}</span>
      </div>
    {/each}

    {#each bands as b, k}
      <div class="bandlab" class:on={step === 10} style="left:{box.l + colW * (k + 0.5)}px;top:{box.b + 10}px">
        <span>{b.label}</span><b>{b.med.toFixed(1)}</b>
      </div>
    {/each}

    {#each picks as i (i.id)}
      {@const p = at(i)}
      <span class="rank" class:on={play} style="left:{p.x}px;top:{p.y}px">{rankOf.get(i.id)}</span>
    {/each}
  </div>

  <header class="hero" class:gone={step > 0}>
    <p class="kicker">IEM India · a story in {N} dots</p>
    <h1>Does paying more buy better sound?</h1>
    <p class="dek">I scored every beginner wired earphone sold in India under ₹10,000 from lab measurements. Scroll to see what the money buys.</p>
    <p class="cue" aria-hidden="true">Scroll ↓</p>
  </header>

  <div class="steps" bind:this={stepsEl}>
    <section data-step="0" class="spacer"></section>
    <section data-step="1">
      <div class="card">
        <h2>Meet {N} earphones.</h2>
        <p>Each dot is one wired IEM for a 3.5 mm jack, measured by at least one independent person. Lined up by price, {inr(lo)} to {inr(hi)}.</p>
      </div>
    </section>
    <section data-step="2">
      <div class="card">
        <h2>First, what is "good sound"?</h2>
        <p>
          In blind tests, researchers at Harman found most people like one shape of sound, the <em>target</em>. An earphone
          loses points for three things: <b>1</b> leaning too warm or too bright, <b>2</b> bumps and dips, <b>3</b> sitting
          far from the target overall. The drawing is made up, just to show the idea.
        </p>
      </div>
    </section>
    <section data-step="3">
      <div class="card">
        <h2>So every earphone gets a sound score.</h2>
        <p>Start at about 100, lose points for those three. Higher means closer to what most people like. Within about 3 points is a tie, so do not sweat small gaps.</p>
      </div>
    </section>
    <section data-step="4">
      <div class="card">
        <h2>If money bought sound, they would climb.</h2>
        <p>They stay <em>flat</em>. Price explains <em>{r2pct}</em> of the difference in sound. Pricier is not better, it is just pricier.</p>
      </div>
    </section>
    <section data-step="5">
      <div class="card">
        <p class="eyebrow">Corner 1 of 4</p>
        <h2>Great sound, small price. <em>Buy from here.</em></h2>
        <p>{qCount('buy')} earphones sound better than most and cost less than {inr(mPrice)}. If this is your first pair, start here and stop worrying.</p>
      </div>
    </section>
    <section data-step="6">
      <div class="card">
        <p class="eyebrow">Corner 2 of 4</p>
        <h2>Great sound, bigger price. <em>Only if money is spare.</em></h2>
        <p>{qCount('treat')} sound just as good as corner 1, they just cost more. Nothing wrong with them. You are paying extra for things that are not the sound.</p>
      </div>
    </section>
    <section data-step="7">
      <div class="card">
        <p class="eyebrow">Corner 3 of 4</p>
        <h2>Cheap, sound is behind. <em>A backup pair.</em></h2>
        <p>{qCount('backup')} cost little and sound so-so. Fine for the gym bag or the commute, where losing them will not hurt. Not your main pair.</p>
      </div>
    </section>
    <section data-step="8">
      <div class="card">
        <p class="eyebrow">Corner 4 of 4</p>
        <h2>Pricey and behind on sound. <em>Skip.</em></h2>
        <p>{qCount('skip')} ask for more money and give you less sound. However nice the box looks, walk past these.</p>
      </div>
    </section>
    <section data-step="9">
      <div class="card">
        <h2>Corner 1 against corner 4.</h2>
        <p>
          The <em>{pair.cheap.name}</em> costs {inr(pair.cheap.price_inr)}. The {pair.pricey.name} costs
          {inr(pair.pricey.price_inr - pair.cheap.price_inr)} more and scores {(pair.cheap.harman_score! - pair.pricey.harman_score!).toFixed(1)}
          points less. Same shop, same week.
        </p>
      </div>
    </section>
    <section data-step="10">
      <div class="card">
        <h2>Split by budget, the middle barely moves.</h2>
        <p>The typical score goes <em>{bands.map((b) => b.med.toFixed(1)).join(' → ')}</em> from cheapest to dearest. Smaller than the measurement noise.</p>
      </div>
    </section>
    <section data-step="11" class="finale">
      <div class="panel">
        <h2>Now find yours.</h2>
        <div class="ctl">
          <div class="seg" role="group" aria-label="Plug">
            {#each PLUGS as p}
              <button type="button" aria-pressed={plug === p} onclick={() => (plug = p)}>{plugLabel(p)}</button>
            {/each}
          </div>
          <div class="seg" role="group" aria-label="Sound">
            {#each TASTES as t}
              <button type="button" aria-pressed={taste === t.k} onclick={() => (taste = t.k)}>{t.label}</button>
            {/each}
          </div>
          <label class="budget">
            <span>Up to <b>{inr(budget)}</b></span>
            <input type="range" min="1000" max="10000" step="250" bind:value={budget} />
          </label>
        </div>
        <p class="count"><b>{matches.length}</b> in stock and measured. The best three:</p>
        {#if picks.length}
          <ol class="picks">
            {#each picks as i, k (i.id)}
              <li>
                <span class="n">{k + 1}</span>
                {#if photo(i, 120)}<img src={photo(i, 120)} alt="" width="40" height="40" loading="lazy" />{/if}
                <a href="/chart#iem={i.id}"><strong>{i.name}</strong>{inr(i.price_inr)} · score {i.score_default.toFixed(1)}</a>
              </li>
            {/each}
          </ol>
        {:else}
          <p class="count">Nothing fits yet. Try a higher budget or any sound.</p>
        {/if}
        <p class="more"><a href="/chart">Full chart</a><a href="/explore">Rank them your way</a><a href="/data">Get the data</a></p>
      </div>
    </section>
  </div>
</div>

<style>
  .story {
    --paper: #f6f1e7;
    --ink: #161616;
    --muted: #5f5a52;
    --red: #e8432c;
    /* Darker red for text, so small words stay readable on the paper. */
    --red-text: #b9301c;
    --faint: #d8d0c2;
    position: relative;
    background: var(--paper);
    color: var(--ink);
    font-family: 'Instrument Sans Variable', system-ui, sans-serif;
  }
  .stage {
    position: sticky;
    top: 0;
    height: 100dvh;
    overflow: hidden;
  }
  .lines {
    position: absolute;
    inset: 0;
  }
  .grid {
    stroke: var(--faint);
    stroke-width: 1;
  }
  .best {
    fill: var(--red);
    opacity: 0;
    transition: opacity 0.6s;
  }
  .best.on {
    opacity: 0.08;
  }
  .expect {
    fill: none;
    stroke: var(--ink);
    stroke-width: 2;
    stroke-dasharray: 6 6;
    opacity: 0;
    transition: opacity 0.6s;
  }
  .expect.on {
    opacity: 0.8;
  }
  .fit {
    fill: none;
    stroke: var(--red);
    stroke-width: 3.5;
    stroke-linecap: round;
    stroke-dasharray: 1;
    stroke-dashoffset: 1;
    transition: stroke-dashoffset 1.2s cubic-bezier(0.6, 0, 0.3, 1);
  }
  .fit.on {
    stroke-dashoffset: 0;
    transition-delay: 0.7s;
  }
  .mid {
    stroke: var(--ink);
    stroke-width: 1;
    stroke-dasharray: 2 4;
    opacity: 0;
    transition: opacity 0.5s;
  }
  .mid.on {
    opacity: 0.6;
  }
  .explain {
    opacity: 0;
    transition: opacity 0.6s;
  }
  .explain.on {
    opacity: 1;
  }
  .explain .ax {
    stroke: var(--ink);
    stroke-width: 1;
  }
  .explain .tgt {
    fill: none;
    stroke: var(--ink);
    stroke-width: 2.5;
    stroke-dasharray: 6 6;
  }
  .explain .ear {
    fill: none;
    stroke: var(--red);
    stroke-width: 3;
    stroke-linecap: round;
    stroke-dasharray: 1;
    stroke-dashoffset: 1;
    transition: stroke-dashoffset 1.4s cubic-bezier(0.6, 0, 0.3, 1) 0.3s;
  }
  .explain.on .ear {
    stroke-dashoffset: 0;
  }
  .explain .gap {
    stroke: var(--ink);
    stroke-width: 1.5;
  }
  .med {
    stroke: var(--red);
    stroke-width: 3;
    stroke-linecap: round;
    opacity: 0;
    transition: opacity 0.5s 0.7s;
  }
  .med.on {
    opacity: 1;
  }

  .dot {
    position: absolute;
    left: 0;
    top: 0;
    border-radius: 50%;
    will-change: transform;
    transition:
      transform 1s cubic-bezier(0.55, 0, 0.2, 1),
      background-color 0.6s,
      opacity 0.6s;
  }
  .story:not(.ready) .dot {
    visibility: hidden;
    transition: none;
  }
  .dot.float {
    animation: bob 3.4s ease-in-out infinite alternate;
  }
  .dot.float:nth-child(3n) {
    animation-duration: 4.3s;
  }
  .dot.float:nth-child(5n) {
    animation-duration: 2.8s;
  }
  @keyframes bob {
    to {
      translate: 0 -10px;
    }
  }

  .axis span,
  .axis b,
  .stamp,
  .midlab,
  .xlabels,
  .note,
  .big,
  .callout,
  .bandlab,
  .rank {
    position: absolute;
    opacity: 0;
    transition: opacity 0.5s;
    pointer-events: none;
  }
  .axis.on span,
  .axis.on b,
  .on {
    opacity: 1;
  }
  .axis span {
    font-size: 0.72rem;
    color: var(--muted);
  }
  .axis.x span {
    transform: translateX(-50%);
  }
  .axis.y span {
    transform: translate(-100%, -50%);
  }
  .axis b {
    font-size: 0.75rem;
    font-weight: 700;
    white-space: nowrap;
  }
  .axis.x b {
    transform: translateX(-100%);
  }
  .note {
    padding: 0.05rem 0.4rem;
    background: var(--paper);
    font-family: 'Bricolage Grotesque Variable', sans-serif;
    font-weight: 700;
    font-size: 0.85rem;
    white-space: nowrap;
    transform: translate(-100%, -50%);
  }
  .note.red {
    color: var(--red-text);
    transform: translateX(-100%);
  }
  .fitnote.on {
    transition-delay: 1.3s;
  }
  .stamp {
    display: grid;
    line-height: 0.9;
    font-family: 'Bricolage Grotesque Variable', sans-serif;
    color: var(--red-text);
    transition:
      opacity 0.4s,
      transform 0.4s;
    transform: scale(0.92);
  }
  .stamp.on {
    transform: none;
    transition-delay: 0.5s;
  }
  .stamp.r {
    justify-items: end;
    translate: -100% 0;
  }
  .stamp.b {
    translate: 0 -100%;
  }
  .stamp.r.b {
    translate: -100% -100%;
  }
  .stamp b {
    font-size: clamp(2.6rem, 8vw, 4.6rem);
    font-weight: 800;
    letter-spacing: -0.04em;
  }
  .stamp span {
    margin-top: 0.2rem;
    padding: 0.1rem 0.45rem;
    border: 2px solid var(--red-text);
    font-size: 0.8rem;
    font-weight: 800;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    white-space: nowrap;
    rotate: -3deg;
    background: var(--paper);
  }
  .midlab {
    z-index: 1;
    padding: 0 0.3rem;
    font-size: 0.68rem;
    color: var(--muted);
    background: var(--paper);
    white-space: nowrap;
    transform: translate(-50%, -100%);
  }
  .midlab.y {
    transform: translate(-100%, -120%);
  }
  .xlabels {
    inset: 0;
    transition-delay: 0.2s;
  }
  .xlabels .lab,
  .xlabels .call {
    position: absolute;
    white-space: nowrap;
  }
  .xlabels .lab {
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--muted);
  }
  .xlabels .rt {
    transform: translateX(-100%);
  }
  .xlabels .tag {
    font-family: 'Bricolage Grotesque Variable', sans-serif;
    font-size: 0.85rem;
    color: var(--ink);
    transform: translateX(-100%);
  }
  .xlabels .tag.red {
    color: var(--red-text);
    transform: none;
  }
  .xlabels .call {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.15rem 0.5rem 0.15rem 0.2rem;
    background: #fff;
    border: 1px solid var(--ink);
    font-size: 0.75rem;
    font-weight: 600;
  }
  .xlabels .call b,
  .card b {
    display: inline-grid;
    place-items: center;
    width: 1.15rem;
    height: 1.15rem;
    border-radius: 50%;
    background: var(--red-text);
    color: #fff;
    font-size: 0.7rem;
    font-weight: 800;
    vertical-align: 0.1em;
  }
  .xlabels .c2 {
    transform: translateX(-100%);
  }
  .xlabels .c3 {
    transform: translateY(-50%);
  }
  .eyebrow {
    margin: 0 0 0.3rem !important;
    font-size: 0.72rem !important;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
  }
  .big {
    display: grid;
    line-height: 0.88;
    font-family: 'Bricolage Grotesque Variable', sans-serif;
    color: var(--red-text);
  }
  .big b {
    font-size: clamp(3.4rem, 10vw, 6rem);
    font-weight: 800;
    letter-spacing: -0.04em;
  }
  .big span {
    font-weight: 700;
    font-size: 0.95rem;
  }
  .callout {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: max-content;
    max-width: 13rem;
    padding: 0.35rem 0.6rem 0.35rem 0.35rem;
    background: #fff;
    border: 1px solid var(--ink);
    font-size: 0.75rem;
    line-height: 1.3;
    transform: translate(16px, -50%);
    transition: opacity 0.4s 0.6s;
  }
  .callout.flip {
    transform: translate(calc(-100% - 16px), -50%);
  }
  .callout:not(.on) {
    transition-delay: 0s;
  }
  .callout img {
    width: 3rem;
    height: 3rem;
    object-fit: contain;
    background: #fff;
  }
  .callout strong {
    display: block;
    font-size: 0.85rem;
  }
  .callout.cheap {
    border-color: var(--red);
    border-width: 2px;
  }
  .callout.cheap strong {
    color: var(--red-text);
  }
  .bandlab {
    display: grid;
    justify-items: center;
    transform: translateX(-50%);
    text-align: center;
    font-size: 0.7rem;
    color: var(--muted);
  }
  .bandlab b {
    font-family: 'Bricolage Grotesque Variable', sans-serif;
    font-size: 1.2rem;
    color: var(--red-text);
  }
  .rank {
    transform: translate(10px, -50%);
    font-family: 'Bricolage Grotesque Variable', sans-serif;
    font-weight: 800;
    font-size: 1rem;
    color: var(--red);
    text-shadow:
      0 0 3px var(--paper),
      0 0 3px var(--paper);
    transition:
      opacity 0.4s,
      left 0.6s,
      top 0.6s;
  }

  .hero {
    position: absolute;
    inset: 0 0 auto;
    height: 100dvh;
    display: grid;
    align-content: center;
    padding: 0 1.25rem;
    max-width: 54rem;
    margin: 0 auto;
    transition: opacity 0.5s;
  }
  .hero.gone {
    opacity: 0;
  }
  .kicker {
    margin: 0 0 1rem;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--red-text);
  }
  h1 {
    margin: 0;
    font-family: 'Bricolage Grotesque Variable', sans-serif;
    font-weight: 800;
    font-size: clamp(2.8rem, 11vw, 6.8rem);
    line-height: 0.9;
    letter-spacing: -0.045em;
    text-wrap: balance;
  }
  .dek {
    max-width: 30rem;
    margin: 1.4rem 0 0;
    font-size: clamp(1.05rem, 2.6vw, 1.3rem);
    line-height: 1.45;
  }
  .cue {
    margin: 2.5rem 0 0;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    animation: nudge 1.4s ease-in-out infinite alternate;
  }
  @keyframes nudge {
    to {
      transform: translateY(6px);
    }
  }

  .steps {
    position: relative;
    margin-top: -100dvh;
    pointer-events: none;
  }
  .steps section {
    min-height: 100dvh;
    display: flex;
    align-items: flex-end;
  }
  .steps .spacer {
    min-height: 110dvh;
  }
  /* On a phone the text sits on a soft fade under the chart, never on top of the dots. */
  .card {
    pointer-events: auto;
    width: 100%;
    padding: 2.2rem 1.25rem 5dvh;
    background: linear-gradient(to bottom, transparent, var(--paper) 1.6rem);
  }
  .card h2,
  .panel h2 {
    margin: 0 0 0.4rem;
    font-family: 'Bricolage Grotesque Variable', sans-serif;
    font-weight: 800;
    font-size: 1.55rem;
    line-height: 1.02;
    letter-spacing: -0.03em;
    text-wrap: balance;
  }
  .card p {
    margin: 0;
    font-size: 0.98rem;
    line-height: 1.45;
    max-width: 30rem;
  }
  em {
    font-style: normal;
    font-weight: 700;
    color: var(--red-text);
  }

  .finale {
    min-height: 100dvh;
  }
  .panel {
    pointer-events: auto;
    width: 100%;
    max-height: 52dvh;
    overflow-y: auto;
    padding: 1rem 1.25rem 1.2rem;
    background: var(--paper);
    border-top: 1px solid var(--ink);
  }
  .ctl {
    display: grid;
    gap: 0.5rem;
    margin: 0.6rem 0 0.5rem;
  }
  .seg {
    display: flex;
    border: 1px solid var(--ink);
  }
  .seg button {
    flex: 1;
    min-height: 2.4rem;
    padding: 0 0.4rem;
    border: 0;
    border-left: 1px solid var(--ink);
    background: none;
    font: inherit;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--ink);
    cursor: pointer;
  }
  .seg button:first-child {
    border-left: 0;
  }
  .seg button[aria-pressed='true'] {
    background: var(--ink);
    color: var(--paper);
  }
  .budget {
    display: grid;
    gap: 0.1rem;
    font-size: 0.9rem;
  }
  .budget b {
    font-family: 'Bricolage Grotesque Variable', sans-serif;
    font-size: 1.15rem;
    color: var(--red-text);
  }
  .budget input {
    width: 100%;
    accent-color: var(--red);
    height: 1.8rem;
    margin: 0;
  }
  .count {
    margin: 0.3rem 0 0.5rem;
    font-size: 0.85rem;
    color: var(--muted);
  }
  .count b {
    color: var(--ink);
  }
  .picks {
    list-style: none;
    padding: 0;
    margin: 0 0 0.8rem;
    display: grid;
    gap: 0.45rem;
  }
  .picks li {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 0.8rem;
    line-height: 1.3;
  }
  .picks .n {
    width: 1rem;
    font-family: 'Bricolage Grotesque Variable', sans-serif;
    font-weight: 800;
    font-size: 1.2rem;
    color: var(--red-text);
  }
  .picks img {
    width: 2.5rem;
    height: 2.5rem;
    object-fit: contain;
    background: #fff;
    border: 1px solid var(--faint);
  }
  .picks a {
    color: var(--ink);
    text-decoration: none;
  }
  .picks strong {
    display: block;
    font-size: 0.92rem;
    text-decoration: underline;
    text-decoration-color: var(--faint);
    text-underline-offset: 0.2em;
  }
  .more {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem 1rem;
    margin: 0;
    font-size: 0.85rem;
  }
  .more a {
    color: var(--ink);
    font-weight: 700;
    text-decoration-color: var(--red);
    text-decoration-thickness: 2px;
    text-underline-offset: 0.22em;
  }

  /* Desktop: text in a column on the left, chart on the right. */
  .wide .steps section {
    align-items: center;
  }
  .wide .card {
    max-width: 30rem;
    padding: 0 0 0 6vw;
    background: none;
  }
  .wide .card h2 {
    font-size: 2.3rem;
  }
  .wide .card p {
    font-size: 1.08rem;
  }
  .wide .finale {
    align-items: stretch;
  }
  .wide .panel {
    width: calc(44vw - 3rem);
    max-height: none;
    padding: 6rem 2rem 2rem 6vw;
    border-top: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  .wide .panel h2 {
    font-size: 2.3rem;
  }

  @media (prefers-reduced-motion: reduce) {
    .dot,
    .fit,
    .callout {
      transition: none !important;
    }
    .dot.float,
    .cue {
      animation: none;
    }
  }
</style>
