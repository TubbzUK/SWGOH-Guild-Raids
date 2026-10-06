/* Theme switcher, starfield and raid banner art, shared by the dashboard and the upload page.
   All artwork here is original and drawn in code - no game or film assets. */
(function () {
  const root = document.documentElement;
  const KEY = "raidTheme";
  const store = {
    get() { try { return localStorage.getItem(KEY); } catch (e) { return null; } },
    set(v) { try { v ? localStorage.setItem(KEY, v) : localStorage.removeItem(KEY); } catch (e) {} },
  };
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const darkQuery = matchMedia("(prefers-color-scheme: dark)");
  const isDark = () => root.dataset.theme ? root.dataset.theme === "dark" : darkQuery.matches;
  const announce = () => { window.dispatchEvent(new Event("themechange")); drawStars(); };

  // ---------------- theme toggle: System -> Light -> Dark ----------------
  const ICON = {
    system: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M8 1.8a6.2 6.2 0 0 1 0 12.4z" fill="currentColor"/></svg>',
    light: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="3.2" fill="currentColor"/><path d="M8 .8v2.2M8 13v2.2M.8 8H3M13 8h2.2M2.9 2.9l1.6 1.6M11.5 11.5l1.6 1.6M2.9 13.1l1.6-1.6M11.5 4.5l1.6-1.6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
    dark: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M13.6 10.4A6.2 6.2 0 0 1 5.6 2.4a6.2 6.2 0 1 0 8 8z" fill="currentColor"/></svg>',
  };
  const MODES = [
    { id: "system", ic: ICON.system, label: "System" },
    { id: "light", ic: ICON.light, label: "Light" },
    { id: "dark", ic: ICON.dark, label: "Dark" },
  ];
  function apply(mode) {
    if (mode === "light" || mode === "dark") root.dataset.theme = mode; else delete root.dataset.theme;
  }
  apply(store.get());
  function mountToggle(el) {
    if (!el) return;
    const btn = document.createElement("button");
    btn.type = "button"; btn.className = "theme-toggle";
    const paint = () => {
      const cur = MODES.find(m => m.id === (store.get() || "system")) || MODES[0];
      btn.innerHTML = `${cur.ic}<span>${cur.label}</span>`;
      btn.setAttribute("aria-label", `Theme: ${cur.label}. Click to change.`);
      btn.title = "Change theme (System / Light / Dark)";
    };
    btn.onclick = () => {
      const i = MODES.findIndex(m => m.id === (store.get() || "system"));
      const next = MODES[(i + 1) % MODES.length].id;
      store.set(next === "system" ? null : next); apply(next); paint(); announce();
    };
    paint(); el.appendChild(btn);
  }
  darkQuery.addEventListener?.("change", () => { if (!store.get()) announce(); });

  // ---------------- starfield ----------------
  let canvas, ctx, stars = [], twinklers = [], raf = 0, lastT = 0;
  function seeded(seed) { let s = seed >>> 0 || 1; return () => (s = (s * 1664525 + 1013904223) >>> 0) / 4294967296; }
  function buildStars() {
    const w = innerWidth, h = innerHeight, rnd = seeded(20260706);
    const n = Math.round((w * h) / 1700);
    stars = Array.from({ length: n }, () => {
      const r = rnd();
      return { x: rnd() * w, y: rnd() * h, s: r < 0.92 ? 0.35 + rnd() * 0.7 : 1 + rnd() * 0.9, a: 0.25 + rnd() * 0.75,
               tint: r > 0.975 ? "255,190,120" : r > 0.95 ? "150,220,255" : "255,255,255", ph: rnd() * 6.28 };
    });
    twinklers = stars.filter(st => st.s > 0.9).slice(0, 60);
  }
  function paintStars(t) {
    if (!ctx) return;
    const dpr = Math.min(devicePixelRatio || 1, 2);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, innerWidth, innerHeight);
    for (const st of stars) {
      const tw = twinklers.includes(st) && !reduceMotion ? 0.55 + 0.45 * Math.sin(t / 900 + st.ph) : 1;
      ctx.fillStyle = `rgba(${st.tint},${(st.a * tw).toFixed(3)})`;
      ctx.beginPath(); ctx.arc(st.x, st.y, st.s, 0, 6.2832); ctx.fill();
      if (st.s > 1.4) { ctx.fillStyle = `rgba(${st.tint},${(0.08 * tw).toFixed(3)})`; ctx.beginPath(); ctx.arc(st.x, st.y, st.s * 4, 0, 6.2832); ctx.fill(); }
    }
  }
  function loop(t) {
    raf = 0;
    if (!isDark() || document.hidden) return;
    if (t - lastT > 66) { paintStars(t); lastT = t; }   // ~15 fps is plenty for a gentle twinkle
    raf = requestAnimationFrame(loop);
  }
  function drawStars() {
    if (!canvas) return;
    const dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.round(innerWidth * dpr); canvas.height = Math.round(innerHeight * dpr);
    if (!isDark()) { ctx.clearRect(0, 0, canvas.width, canvas.height); return; }
    paintStars(performance.now());
    if (!reduceMotion && !raf) raf = requestAnimationFrame(loop);
  }
  function mountSky() {
    const sky = document.createElement("div"); sky.className = "sky"; sky.setAttribute("aria-hidden", "true");
    canvas = document.createElement("canvas"); sky.appendChild(canvas); document.body.prepend(sky);
    ctx = canvas.getContext("2d"); buildStars(); drawStars();
    let rt; addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => { buildStars(); drawStars(); }, 150); });
    document.addEventListener("visibilitychange", () => { if (!document.hidden) drawStars(); });
  }

  // ---------------- banner art (SVG, 1200 x 260, cropped to fit) ----------------
  function starsSVG(rnd, n, h) {
    let s = "";
    for (let i = 0; i < n; i++) {
      const r = rnd() < 0.9 ? 0.4 + rnd() * 0.8 : 1.2 + rnd() * 1.1;
      s += `<circle cx="${(rnd() * 1200).toFixed(1)}" cy="${(rnd() * h).toFixed(1)}" r="${r.toFixed(2)}" fill="#fff" opacity="${(0.25 + rnd() * 0.75).toFixed(2)}"/>`;
    }
    return s;
  }
  function skyline(rnd, base, fill, lights) {
    let x = 0, d = `M0 ${base + 40}`, win = "";
    while (x < 1200) {
      const w = 18 + rnd() * 46, h = 20 + rnd() * (rnd() < 0.15 ? 120 : 60);
      d += ` L${x.toFixed(0)} ${base - h} L${(x + w).toFixed(0)} ${base - h}`;
      if (rnd() < 0.18) { const sx = x + w / 2; d += ` L${sx.toFixed(0)} ${base - h} L${sx.toFixed(0)} ${base - h - 30 - rnd() * 40} L${(sx + 2).toFixed(0)} ${base - h}`; }
      for (let k = 0; k < 3; k++) if (rnd() < 0.5) win += `<rect x="${(x + 4 + rnd() * (w - 8)).toFixed(0)}" y="${(base - h + 6 + rnd() * (h - 10)).toFixed(0)}" width="2" height="2" fill="${lights}" opacity="${(0.4 + rnd() * 0.6).toFixed(2)}"/>`;
      x += w;
    }
    return `<path d="${d} L1200 ${base + 40} Z" fill="${fill}"/>${win}`;
  }
  function cog(cx, cy, r, teeth, color, width) {
    let d = "";
    for (let i = 0; i < teeth * 2; i++) {
      const a0 = (i / (teeth * 2)) * Math.PI * 2, a1 = ((i + 1) / (teeth * 2)) * Math.PI * 2;
      const rr = i % 2 ? r : r + r * 0.12;
      d += `${i ? "L" : "M"}${(cx + rr * Math.cos(a0)).toFixed(1)} ${(cy + rr * Math.sin(a0)).toFixed(1)} L${(cx + rr * Math.cos(a1)).toFixed(1)} ${(cy + rr * Math.sin(a1)).toFixed(1)} `;
    }
    return `<path d="${d}Z" fill="none" stroke="${color}" stroke-width="${width}"/><circle cx="${cx}" cy="${cy}" r="${(r * 0.55).toFixed(1)}" fill="none" stroke="${color}" stroke-width="${width}"/><circle cx="${cx}" cy="${cy}" r="${(r * 0.18).toFixed(1)}" fill="${color}"/>`;
  }
  const ART = {
    "order-66"(rnd) {
      const bolts = [[640, 40, 780, 120, "#ff3b5c"], [700, 150, 880, 70, "#5ec8ff"], [560, 110, 690, 190, "#ff3b5c"], [860, 30, 990, 110, "#5ec8ff"], [930, 170, 1060, 120, "#ff3b5c"]]
        .map(([x1, y1, x2, y2, c]) => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${c}" stroke-width="3" stroke-linecap="round" filter="url(#g)"/><line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#fff" stroke-width="1" stroke-linecap="round" opacity=".85"/>`).join("");
      return `<defs>
        <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0a0206"/><stop offset=".55" stop-color="#26050f"/><stop offset="1" stop-color="#0b0309"/></linearGradient>
        <radialGradient id="pl" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#3a1220"/><stop offset=".7" stop-color="#14060b"/><stop offset="1" stop-color="#050104"/></radialGradient>
        <filter id="b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="40"/></filter>
        <filter id="g" x="-20%" y="-200%" width="140%" height="500%"><feGaussianBlur stdDeviation="3"/></filter></defs>
        <rect width="1200" height="260" fill="url(#bg)"/>
        <ellipse cx="820" cy="70" rx="360" ry="110" fill="#d0163a" opacity=".45" filter="url(#b)"/>
        <ellipse cx="1080" cy="200" rx="220" ry="90" fill="#6a2bd8" opacity=".35" filter="url(#b)"/>
        <ellipse cx="320" cy="30" rx="260" ry="70" fill="#2a4cc8" opacity=".25" filter="url(#b)"/>
        ${starsSVG(rnd, 170, 260)}
        <circle cx="1030" cy="330" r="230" fill="url(#pl)"/>
        <circle cx="1030" cy="330" r="230" fill="none" stroke="#ff5470" stroke-width="2" opacity=".55"/>
        <circle cx="1030" cy="330" r="236" fill="none" stroke="#ff5470" stroke-width="10" opacity=".12" filter="url(#g)"/>
        ${bolts}
        ${skyline(rnd, 238, "#070207", "#ffb35c")}`;
    },
    "droid-destruction"(rnd) {
      let hex = "";
      for (let row = 0; row < 7; row++) for (let col = 0; col < 26; col++) {
        const x = col * 52 + (row % 2) * 26, y = row * 45;
        hex += `<path d="M${x} ${y - 26}l22.5 13v26L${x} ${y + 26}l-22.5-13v-26z"/>`;
      }
      let sparks = "";
      for (let i = 0; i < 40; i++) { const a = -Math.PI * (0.15 + rnd() * 0.7), len = 10 + rnd() * 60, x = 720 + Math.cos(a) * (20 + rnd() * 90), y = 200 + Math.sin(a) * (20 + rnd() * 90);
        sparks += `<line x1="${x.toFixed(0)}" y1="${y.toFixed(0)}" x2="${(x + Math.cos(a) * len * 0.3).toFixed(0)}" y2="${(y + Math.sin(a) * len * 0.3).toFixed(0)}" stroke="${rnd() < 0.5 ? "#ffd27a" : "#ff8a2b"}" stroke-width="${(1 + rnd() * 1.5).toFixed(1)}" stroke-linecap="round" opacity="${(0.5 + rnd() * 0.5).toFixed(2)}"/>`; }
      let stacks = "M0 300 L0 230";
      for (let x = 0; x < 1200;) { const w = 30 + rnd() * 70, h = 20 + rnd() * 50, t = rnd() < 0.35;
        stacks += ` L${x.toFixed(0)} ${230 - h} L${(x + w).toFixed(0)} ${230 - h}`;
        if (t) stacks += ` L${(x + w).toFixed(0)} ${230 - h - 50 - rnd() * 40} L${(x + w + 12).toFixed(0)} ${230 - h - 50 - rnd() * 40} L${(x + w + 12).toFixed(0)} ${230 - h}`;
        x += w + (t ? 12 : 0); }
      return `<defs>
        <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0c0603"/><stop offset=".6" stop-color="#2b1205"/><stop offset="1" stop-color="#0a0503"/></linearGradient>
        <filter id="b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="38"/></filter>
        <linearGradient id="fade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity=".4"/></linearGradient>
        <mask id="m"><rect width="1200" height="260" fill="url(#fade)"/></mask></defs>
        <rect width="1200" height="260" fill="url(#bg)"/>
        <ellipse cx="760" cy="190" rx="380" ry="120" fill="#ff6a12" opacity=".42" filter="url(#b)"/>
        <ellipse cx="1050" cy="60" rx="200" ry="80" fill="#ffb347" opacity=".22" filter="url(#b)"/>
        ${starsSVG(rnd, 70, 150)}
        <g mask="url(#m)" fill="none" stroke="#ffae55" stroke-width="1" opacity=".16">${hex}</g>
        <g opacity=".75">${cog(990, 120, 92, 14, "rgba(255,170,80,.55)", 3)}${cog(1118, 40, 54, 10, "rgba(255,170,80,.4)", 2.5)}${cog(870, 34, 40, 8, "rgba(255,170,80,.3)", 2)}</g>
        ${sparks}
        <path d="${stacks} L1200 230 L1200 300 Z" fill="#090402"/>
        <rect x="0" y="236" width="1200" height="3" fill="#ff8a2b" opacity=".35"/>`;
    },
    default(rnd) {
      return `<defs>
        <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#03060f"/><stop offset=".6" stop-color="#0b1a3a"/><stop offset="1" stop-color="#04070f"/></linearGradient>
        <radialGradient id="pl" cx=".3" cy=".3" r=".9"><stop offset="0" stop-color="#2f5ea8"/><stop offset=".6" stop-color="#0e2246"/><stop offset="1" stop-color="#04070f"/></radialGradient>
        <filter id="b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="40"/></filter></defs>
        <rect width="1200" height="260" fill="url(#bg)"/>
        <ellipse cx="800" cy="80" rx="380" ry="120" fill="#2f7bff" opacity=".35" filter="url(#b)"/>
        <ellipse cx="1050" cy="210" rx="220" ry="80" fill="#22c4d6" opacity=".25" filter="url(#b)"/>
        ${starsSVG(rnd, 180, 260)}
        <ellipse cx="980" cy="150" rx="210" ry="34" fill="none" stroke="#9fd4ff" stroke-width="2" opacity=".45" transform="rotate(-12 980 150)"/>
        <circle cx="980" cy="150" r="96" fill="url(#pl)"/>
        <path d="M772 172 A210 34 -12 0 0 1188 128" fill="none" stroke="#9fd4ff" stroke-width="2" opacity=".55" transform="rotate(-12 980 150)"/>`;
    },
  };
  function hash(s) { let h = 2166136261; for (const c of String(s)) h = Math.imul(h ^ c.charCodeAt(0), 16777619); return h >>> 0; }
  function banner(el, raid) {
    if (!el) return;
    if (raid && raid.banner) {
      el.innerHTML = `<img src="${raid.banner}" alt="" loading="eager">`;
      return;
    }
    const slug = raid && raid.slug, draw = ART[slug] || ART.default;
    el.innerHTML = `<svg viewBox="0 0 1200 260" preserveAspectRatio="xMidYMid slice" aria-hidden="true">${draw(seeded(hash(slug || "raid")))}</svg>`;
  }

  // wordmark emblem (generic targeting reticle)
  const emblem = `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="12" r="4.5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M12 0v6M12 18v6M0 12h6M18 12h6" stroke="currentColor" stroke-width="1.5"/></svg>`;

  window.RaidTheme = { banner, isDark, emblem };
  const ready = () => { mountSky(); document.querySelectorAll("[data-theme-toggle]").forEach(mountToggle); document.querySelectorAll("[data-emblem]").forEach(e => e.innerHTML = emblem); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready); else ready();
})();
