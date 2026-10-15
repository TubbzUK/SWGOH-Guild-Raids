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

  // ---------------- side menu: every page, officer tools, uploads and the theme, down the left ----------------
  // Pages mark controls to move into it with data-menu="officer" or data-menu="upload"; RaidTheme.menuItem() adds more.
  // Desktop: expanded (labels) or collapsed (icon rail), remembered per device. Phones: slides in from the ☰ button.
  let menuPanel = null;
  const SB_KEY = "gsSidebar", G_KEY = "gsGuild";
  const ls = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) {} } };
  const PAGES = [
    { id: "raidLink", file: "./", match: /(^|\/)(index\.html)?$/, ic: "⚔", label: "Raids" },
    { id: "playerLink", file: "player.html", match: /player\.html$/, ic: "◉", label: "Player status" },
    { id: "tbLink", file: "tb.html", match: /tb\.html$/, ic: "◈", label: "Territory battles" },
    { id: "rankLink", file: "ranking.html", match: /ranking\.html$/, ic: "★", label: "TB contribution" },
    { id: "twLink", file: "tw.html", match: /tw\.html$/, ic: "✦", label: "Territory wars" },
    { id: "effLink", file: "effectiveness.html", match: /effectiveness\.html$/, ic: "◎", label: "Guild effectiveness" },
    { id: "platoonLink", file: "platoons.html", match: /platoons\.html$/, ic: "⚑", label: "RotE platoons" },
  ];
  const SB_CSS = `
  :root { --sbw: 248px; }
  body.sb-on { padding-left: var(--sbw); transition: padding-left .18s ease; }
  body.sb-on.sb-min { --sbw: 68px; }
  body.sb-on .topbar { display: none; }
  body.sb-on .wrap { padding-top: 22px; }
  .sb { position: fixed; left: 0; top: 0; bottom: 0; width: var(--sbw); z-index: 50; display: flex; flex-direction: column;
    background: color-mix(in srgb, var(--surface-solid) 92%, transparent); border-right: 1px solid var(--border);
    backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); transition: width .18s ease, transform .2s ease; overflow: hidden; }
  .sb-head { display: flex; align-items: center; gap: 8px; padding: 16px 12px 12px 18px; min-height: 58px; box-sizing: border-box; }
  .sb-head .wordmark { flex: 1; min-width: 0; font-size: 11.5px; letter-spacing: .22em; white-space: nowrap; overflow: hidden; }
  .sb-iconbtn { flex: none; width: 34px; height: 34px; display: inline-flex; align-items: center; justify-content: center; border-radius: 9px;
    border: 1px solid var(--border); background: var(--surface); color: var(--text-2); cursor: pointer; padding: 0; }
  .sb-iconbtn:hover { color: var(--accent); border-color: var(--accent); }
  .sb-iconbtn svg { width: 15px; height: 15px; }
  .sb-body { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 4px 10px 10px; display: flex; flex-direction: column; }
  .sb-sec + .sb-sec { border-top: 1px solid var(--border); margin-top: 8px; padding-top: 4px; }
  .sb-sec.empty, .sb-sec:empty { display: none; }
  .sb-h { font: 700 10px var(--font-display); letter-spacing: .16em; text-transform: uppercase; color: var(--text-2); padding: 12px 10px 6px; white-space: nowrap; }
  .sb a.sb-item, .sb button.sb-item, .sb [data-menu] { display: flex !important; align-items: center; gap: 12px; width: 100%; text-align: left; box-sizing: border-box;
    background: none !important; border: 0 !important; border-radius: 9px !important; padding: 9px 10px !important; margin: 1px 0 !important; box-shadow: none !important;
    font: 600 13.5px var(--font-ui) !important; letter-spacing: 0 !important; text-transform: none !important; color: var(--text) !important;
    text-decoration: none; cursor: pointer; white-space: nowrap; min-height: 38px; position: relative; }
  .sb .sb-item:hover, .sb [data-menu]:hover { background: var(--surface-2) !important; color: var(--accent) !important; }
  .sb .sb-item[aria-current="page"] { background: color-mix(in srgb, var(--accent) 16%, transparent) !important; color: var(--accent) !important; }
  .sb .sb-item[aria-current="page"]::before { content: ""; position: absolute; left: -10px; top: 8px; bottom: 8px; width: 3px; border-radius: 0 3px 3px 0; background: var(--accent); }
  .sb .sb-item[hidden], .sb [data-menu][hidden] { display: none !important; }
  .sb .ic { flex: none; width: 24px; text-align: center; font-size: 15px; line-height: 1; }
  .sb .tx { min-width: 0; overflow: hidden; text-overflow: ellipsis; }
  .sb-foot { border-top: 1px solid var(--border); padding: 8px 10px 12px; }
  .sb-themes { display: flex; gap: 4px; padding: 0 0 2px; }
  .sb-themes button { flex: 1; display: inline-flex; align-items: center; justify-content: center; gap: 6px; border: 1px solid var(--border); background: var(--surface);
    color: var(--text-2); border-radius: 8px; padding: 7px 4px; font: 600 12px var(--font-ui); cursor: pointer; min-width: 0; }
  .sb-themes button svg { width: 14px; height: 14px; flex: none; }
  .sb-themes button[aria-pressed="true"] { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }
  .sb .sb-foot .sb-cycle { display: none !important; }
  /* collapsed: icon rail */
  body.sb-min .sb .tx, body.sb-min .sb .sb-h, body.sb-min .sb-head .wordmark, body.sb-min .sb-themes { display: none !important; }
  body.sb-min .sb-head { padding: 16px 0 12px; justify-content: center; }
  body.sb-min .sb .sb-item, body.sb-min .sb [data-menu] { justify-content: center; padding: 9px 0 !important; }
  body.sb-min .sb .sb-foot .sb-cycle { display: flex !important; }
  body.sb-min .sb-sec + .sb-sec { margin-top: 6px; padding-top: 6px; }
  body.sb-min .sb-foot { padding: 8px 10px 12px; }
  .sb-flip svg { transition: transform .18s ease; } body.sb-min .sb-flip svg { transform: rotate(180deg); }
  /* phones and small tablets: slide-in drawer */
  .sb-open-btn { display: none; }
  .sb-scrim { position: fixed; inset: 0; z-index: 49; background: rgba(0,0,0,.5); opacity: 0; pointer-events: none; transition: opacity .2s ease; }
  @media (max-width: 899px) {
    body.sb-on, body.sb-on.sb-min { padding-left: 0; --sbw: 272px; }
    body.sb-on .topbar { display: flex; justify-content: flex-start; flex-wrap: nowrap; }
    body.sb-on .topbar .top-actions { display: none; }
    body.sb-on .wrap { padding-top: 0; }
    .sb-open-btn { display: inline-flex; }
    .sb { transform: translateX(-102%); box-shadow: 0 0 40px rgba(0,0,0,.5); }
    body.sb-drawer .sb { transform: none; }
    body.sb-drawer .sb-scrim { opacity: 1; pointer-events: auto; }
    body.sb-min .sb .tx, body.sb-min .sb .sb-h, body.sb-min .sb-head .wordmark { display: initial !important; }
    body.sb-min .sb-themes { display: flex !important; } body.sb-min .sb .sb-foot .sb-cycle { display: none !important; }
    body.sb-min .sb-head { padding: 16px 12px 12px 18px; justify-content: flex-start; }
    body.sb-min .sb .sb-item, body.sb-min .sb [data-menu] { justify-content: flex-start; padding: 9px 10px !important; }
    .sb-flip { display: none !important; }
  }
  html.cardmode .sb, html.cardmode .sb-scrim, html.cardmode .sb-open-btn { display: none !important; }
  html.cardmode body.sb-on { padding-left: 0 !important; }`;
  const CHEV = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M10 3 5 8l5 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const BARS = '<svg viewBox="0 0 18 14" aria-hidden="true"><path d="M0 1h18M0 7h18M0 13h18" stroke="currentColor" stroke-width="2"/></svg>';
  const CLOSE = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 3l10 10M13 3 3 13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>';
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  // "📣 Post this raid" -> icon "📣", text "Post this raid"
  function iconise(el, label) {
    const t = (label ?? el.textContent).trim(), m = /^([^\p{L}\p{N}\s]+)\s*(.*)$/u.exec(t);
    const ic = m ? m[1] : "•", tx = m ? m[2] : t;
    el.innerHTML = `<span class="ic" aria-hidden="true">${esc(ic)}</span><span class="tx">${esc(tx)}</span>`;
    el.title = tx; el.setAttribute("aria-label", tx);
  }
  const guildNow = () => {
    const g = /[?&]guild=([^&#]*)/.exec(location.search);
    if (g && g[1]) { ls.set(G_KEY, decodeURIComponent(g[1])); return decodeURIComponent(g[1]); }
    return ls.get(G_KEY);
  };
  function mountMenu(el) {
    if (!el || menuPanel || root.classList.contains("cardmode")) { if (el) el.remove(); return; }
    const st = document.createElement("style"); st.textContent = SB_CSS; document.head.appendChild(st);
    el.remove();
    const body = document.body;
    if (ls.get(SB_KEY) === "min") body.classList.add("sb-min");
    const sb = document.createElement("aside"); sb.className = "sb"; sb.id = "siteNav"; sb.setAttribute("role", "navigation"); sb.setAttribute("aria-label", "Site");
    sb.innerHTML = `<div class="sb-head"><a class="wordmark" href="./"><span data-emblem></span>Guild Statistics</a>
        <button type="button" class="sb-iconbtn sb-flip" title="Collapse the menu" aria-label="Collapse the menu" aria-controls="siteNav">${CHEV}</button>
        <button type="button" class="sb-iconbtn sb-x" title="Close the menu" aria-label="Close the menu" hidden>${CLOSE}</button></div>
      <div class="sb-body">
        <div class="sb-sec" data-sec="pages"><div class="sb-h">Pages</div></div>
        <div class="sb-sec" data-sec="officer"><div class="sb-h">Officers</div></div>
        <div class="sb-sec" data-sec="upload"><div class="sb-h">Upload</div></div>
      </div>
      <div class="sb-foot"><div class="sb-h" style="padding-top:4px">Theme</div><div class="sb-themes"></div>
        <button type="button" class="sb-item sb-cycle"></button></div>`;
    const scrim = document.createElement("div"); scrim.className = "sb-scrim";
    body.prepend(scrim); body.prepend(sb); body.classList.add("sb-on");
    menuPanel = sb;

    // pages
    const here = location.pathname, pagesSec = sb.querySelector('[data-sec="pages"]');
    PAGES.forEach(p => {
      const a = document.createElement("a"); a.className = "sb-item"; iconise(a, `${p.ic} ${p.label}`);
      const own = document.getElementById(p.id);   // the page's own link (it knows the guild and hides pages a guild has no data for)
      const href = () => { if (own && own.getAttribute("href")) return own.href; const g = guildNow(); return p.file + (g ? "?guild=" + encodeURIComponent(g) : ""); };
      a.href = href(); ["pointerdown", "focus", "click"].forEach(ev => a.addEventListener(ev, () => { a.href = href(); }));
      if (p.match.test(here)) a.setAttribute("aria-current", "page");
      if (own) {
        const sync = () => { a.hidden = own.hidden && !p.match.test(here); a.href = href(); };
        sync(); if (window.MutationObserver) new MutationObserver(sync).observe(own, { attributes: true, attributeFilter: ["hidden", "href"] });
      }
      pagesSec.appendChild(a);
    });

    // theme
    const themes = sb.querySelector(".sb-themes"), cycle = sb.querySelector(".sb-cycle");
    const paint = () => {
      const cur = store.get() || "system";
      themes.querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", b.dataset.mode === cur));
      const m = MODES.find(x => x.id === cur) || MODES[0];
      cycle.innerHTML = `<span class="ic">${m.ic}</span>`; cycle.title = `Theme: ${m.label} (click to change)`; cycle.setAttribute("aria-label", cycle.title);
    };
    const setMode = id => { store.set(id === "system" ? null : id); apply(id); paint(); announce(); };
    MODES.forEach(m => {
      const b = document.createElement("button"); b.type = "button"; b.dataset.mode = m.id; b.innerHTML = `${m.ic}<span>${m.label}</span>`;
      b.onclick = () => setMode(m.id); themes.appendChild(b);
    });
    cycle.onclick = () => { const i = MODES.findIndex(m => m.id === (store.get() || "system")); setMode(MODES[(i + 1) % MODES.length].id); };
    paint();

    // collapse (desktop) and drawer (phones)
    const flip = sb.querySelector(".sb-flip"), x = sb.querySelector(".sb-x");
    const flipLabel = () => { const t = body.classList.contains("sb-min") ? "Expand the menu" : "Collapse the menu"; flip.title = t; flip.setAttribute("aria-label", t); flip.setAttribute("aria-expanded", String(!body.classList.contains("sb-min"))); };
    flip.onclick = () => { body.classList.toggle("sb-min"); ls.set(SB_KEY, body.classList.contains("sb-min") ? "min" : null); flipLabel(); window.dispatchEvent(new Event("resize")); };
    flipLabel();
    const openBtn = document.createElement("button"); openBtn.type = "button"; openBtn.className = "sb-iconbtn sb-open-btn";
    openBtn.innerHTML = BARS; openBtn.title = "Menu"; openBtn.setAttribute("aria-label", "Open the menu"); openBtn.setAttribute("aria-controls", "siteNav");
    const tb = document.querySelector(".topbar"); if (tb) tb.prepend(openBtn);
    const drawer = v => { body.classList.toggle("sb-drawer", v); x.hidden = !v; openBtn.setAttribute("aria-expanded", String(v)); if (v) (sb.querySelector('[aria-current="page"]') || x).focus(); };
    openBtn.onclick = () => drawer(true); x.onclick = () => { drawer(false); openBtn.focus(); }; scrim.onclick = () => drawer(false);
    document.addEventListener("keydown", e => { if (e.key === "Escape" && body.classList.contains("sb-drawer")) { drawer(false); openBtn.focus(); } });
    sb.addEventListener("click", e => { if (e.target.closest(".sb-body .sb-item, .sb-body [data-menu]") && body.classList.contains("sb-drawer")) setTimeout(() => drawer(false), 0); });
    matchMedia("(min-width: 900px)").addEventListener?.("change", e => { if (e.matches) drawer(false); });

    // move the page's officer and upload controls in
    document.querySelectorAll("[data-menu]").forEach(n => { const sec = sb.querySelector(`[data-sec="${n.dataset.menu}"]`); if (sec) { iconise(n); sec.appendChild(n); } });
    if (!sb.querySelector('[data-sec="upload"] [data-menu]')) {
      const g = guildNow(), up = menuItem("upload", "⬆ Upload a WookieeBot file", "upload.html" + (g ? "?guild=" + encodeURIComponent(g) : ""));
      if (/upload\.html$/.test(here)) up.setAttribute("aria-current", "page");
    }
    menuItem("upload", "＋ Add a new guild", "upload.html#newguild");
    menuItem("upload", "🔗 Connect a guild to the game", "upload.html" + (guildNow() ? "?guild=" + encodeURIComponent(guildNow()) : "") + "#connect");
    if (document.querySelector('script[src*="officer.js"]')) menuItem("officer", "🔄 Pull from the game now", pullNow);
    menuItem("officer", "🔒 Forget my officer login", () => {
      try { localStorage.removeItem("raidTrackerPassword"); localStorage.removeItem("raidTrackerToken"); } catch (e) {}
      alertish("Officer login forgotten on this device.");
    }, true);
    tidy();
  }
  // ask the next site update to pull rosters, raid scores and TW results from the game straight away
  async function pullNow() {
    if (!window.Officer) { alertish("Officer tools are still loading - try again in a moment."); return; }
    let g = guildNow();
    if (!g) { try { g = ((await (await fetch("guilds.json", { cache: "no-store" })).json())[0] || {}).slug; } catch (e) {} }
    if (!g) { alertish("No guild found."); return; }
    Officer.form({ title: "Pull from the game now",
      html: `Fetch the latest roster, raid scores and territory war results for this guild from the game now, instead of waiting for the next 4-hourly check. The site updates in about 3 minutes.<br><br>The guild needs an ally code set (Upload → Connect a guild to the game).`,
      button: "Pull now",
      run: async ({ putFile }) => {
        const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\..*/, "").replace("T", "-");
        await putFile(`guilds/${g}/sync-now-${stamp}.json`, "{}", "Pull from the game now");
      },
      done: "🔄 Pulling from the game - the site updates in about 3 minutes." });
  }
  function alertish(text) {
    const t = document.createElement("div"); t.textContent = text;
    t.style.cssText = "position:fixed;left:50%;bottom:22px;transform:translateX(-50%);z-index:9999;background:var(--surface-solid);color:var(--text);border:1px solid var(--accent);border-radius:12px;padding:10px 16px;font:14px var(--font-ui);box-shadow:0 10px 30px rgba(0,0,0,.4)";
    document.body.appendChild(t); setTimeout(() => t.remove(), 4000);
  }
  function tidy() {
    if (!menuPanel) return;
    menuPanel.querySelectorAll('.sb-sec:not([data-sec="pages"])').forEach(sec => sec.classList.toggle("empty", !sec.querySelector("[data-menu]:not([hidden]), .sb-item:not([hidden])")));
  }
  /** Add an item to the side menu: section "officer" or "upload"; action is a URL or a function. */
  function menuItem(section, label, action, last) {
    if (!menuPanel) { if (!root.classList.contains("cardmode")) pending.push([section, label, action, last]); return null; }
    const sec = menuPanel.querySelector(`[data-sec="${section}"]`); if (!sec) return null;
    const it = typeof action === "string" ? Object.assign(document.createElement("a"), { href: action }) : Object.assign(document.createElement("button"), { type: "button", onclick: action });
    it.className = "sb-item"; iconise(it, label);
    const tail = sec.querySelector("[data-last]");
    if (last || !tail) sec.appendChild(it); else sec.insertBefore(it, tail);
    if (last) it.dataset.last = "1";
    tidy(); return it;
  }
  const pending = [];

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
    tb(rnd) {
      // six planets along an arc - one per phase - joined by a hyperspace route
      const pts = [[640, 210, 14], [730, 168, 18], [830, 132, 22], [940, 104, 27], [1055, 86, 32], [1160, 78, 38]];
      const cols = [["#7ad1ff", "#1b4f8a"], ["#ffd27a", "#8a4b12"], ["#b9f27a", "#2e6a1c"], ["#ff9ab0", "#7a1e3a"], ["#c9b6ff", "#3b2a7a"], ["#9ff0ff", "#145a66"]];
      let defs = "", planets = "", route = "M" + pts.map(p => p[0] + " " + p[1]).join(" L");
      pts.forEach(([x, y, r], i) => {
        defs += `<radialGradient id="pl${i}" cx=".35" cy=".3" r=".9"><stop offset="0" stop-color="${cols[i][0]}"/><stop offset=".65" stop-color="${cols[i][1]}"/><stop offset="1" stop-color="#05070f"/></radialGradient>`;
        planets += `<circle cx="${x}" cy="${y}" r="${r * 1.9}" fill="${cols[i][0]}" opacity=".10"/><circle cx="${x}" cy="${y}" r="${r}" fill="url(#pl${i})"/>`;
      });
      return `<defs>
        <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#03060f"/><stop offset=".6" stop-color="#0d1430"/><stop offset="1" stop-color="#05070f"/></linearGradient>
        <filter id="b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="40"/></filter>${defs}</defs>
        <rect width="1200" height="260" fill="url(#bg)"/>
        <ellipse cx="900" cy="120" rx="380" ry="120" fill="#3a5cff" opacity=".28" filter="url(#b)"/>
        <ellipse cx="620" cy="230" rx="240" ry="80" fill="#ffb347" opacity=".14" filter="url(#b)"/>
        ${starsSVG(rnd, 170, 260)}
        <path d="${route}" fill="none" stroke="#9fd4ff" stroke-width="1.6" stroke-dasharray="2 7" stroke-linecap="round" opacity=".7"/>
        ${planets}`;
    },
    tw(rnd) {
      // two fleets facing off across the map: red banners on the left, blue on the right, crossing fire
      const flag = (x, y, c, flip) => `<g transform="translate(${x} ${y})${flip ? " scale(-1 1)" : ""}"><rect x="-1" y="-46" width="3" height="58" fill="#cfd6e6" opacity=".8"/><path d="M2 -46 L40 -38 L2 -28 Z" fill="${c}" opacity=".9"/></g>`;
      let flags = "";
      [[650, 205], [720, 190], [790, 212], [860, 196]].forEach(([x, y]) => flags += flag(x, y, "#ff4d6a", false));
      [[960, 200], [1030, 186], [1100, 208], [1165, 192]].forEach(([x, y]) => flags += flag(x, y, "#4cc9f0", true));
      let shots = "";
      for (let i = 0; i < 10; i++) {
        const y = 60 + rnd() * 100, x = 700 + rnd() * 380, len = 40 + rnd() * 60, red = i % 2 === 0;
        shots += `<line x1="${x.toFixed(0)}" y1="${y.toFixed(0)}" x2="${(x + (red ? len : -len)).toFixed(0)}" y2="${(y + (rnd() - .5) * 20).toFixed(0)}" stroke="${red ? "#ff4d6a" : "#5ec8ff"}" stroke-width="2.5" stroke-linecap="round" opacity=".85" filter="url(#g)"/>`;
      }
      return `<defs>
        <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#05040c"/><stop offset=".55" stop-color="#140b26"/><stop offset="1" stop-color="#04070f"/></linearGradient>
        <filter id="b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="40"/></filter>
        <filter id="g" x="-20%" y="-200%" width="140%" height="500%"><feGaussianBlur stdDeviation="2"/></filter></defs>
        <rect width="1200" height="260" fill="url(#bg)"/>
        <ellipse cx="760" cy="120" rx="260" ry="110" fill="#d0163a" opacity=".32" filter="url(#b)"/>
        <ellipse cx="1060" cy="120" rx="260" ry="110" fill="#2a7cf0" opacity=".32" filter="url(#b)"/>
        ${starsSVG(rnd, 170, 260)}
        ${shots}
        <path d="M560 260 L640 214 L900 222 L1200 206 L1200 260 Z" fill="#07060d"/>
        ${flags}`;
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

  // card mode: once a page has drawn, size it to its widest table, label each section, then say it's ready
  async function cardReady() {
    if (!document.documentElement.classList.contains("cardmode")) return;
    document.querySelectorAll("section.tab.card-show").forEach(sec => {
      const t = sec.dataset.cardTitle; if (t && !sec.querySelector(":scope > .cardtitle")) sec.insertAdjacentHTML("afterbegin", `<div class="cardtitle">${t}</div>`);
    });
    const widest = Math.max(0, ...[...document.querySelectorAll(".tablewrap table, .scroll table")].filter(t => t.offsetParent).map(t => t.scrollWidth));
    const w = Math.max(1100, Math.ceil(widest + 52));
    document.documentElement.style.setProperty("--cardw", w + "px");
    try { await document.fonts.ready; } catch (e) {}
    window.dispatchEvent(new Event("resize"));
    await new Promise(r => setTimeout(r, 700));
    document.body.dataset.cardw = w;
    document.body.dataset.ready = "1";
  }
  window.RaidTheme = { banner, isDark, emblem, cardReady, menuItem, mountToggle };
  // card mode: no chart animations, and a small footer with the site address
  const cardMode = document.documentElement.classList.contains("cardmode");
  if (cardMode && window.Chart) Chart.defaults.animation = false;
  function cardFoot() {
    if (!cardMode || document.querySelector(".cardfoot")) return;
    let site = ""; try { site = new URLSearchParams(location.search).get("site") || ""; } catch (e) {}
    const f = document.createElement("div"); f.className = "cardfoot";
    f.innerHTML = `<span class="wordmark"><span data-emblem></span>Guild Statistics</span><span>${site.replace(/^https?:\/\//, "").replace(/\?.*$/, "").replace(/[<>&"]/g, "")}</span>`;
    document.body.appendChild(f);
  }
  const ready = () => { cardFoot(); mountSky(); document.querySelectorAll("[data-theme-toggle], [data-site-menu]").forEach(mountMenu); pending.splice(0).forEach(a => menuItem(...a)); if (window.MutationObserver && menuPanel) new MutationObserver(tidy).observe(menuPanel, { subtree: true, attributes: true, attributeFilter: ["hidden"] }); document.querySelectorAll("[data-emblem]").forEach(e => e.innerHTML = emblem); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready); else ready();
})();
