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
  // each page, and the sections inside it (tabs, buttons or places on the page) shown as a tree under it
  const RAID = { id: "raidLink", file: "./", match: /(^|\/)(index\.html)?$/ };
  const TB = { id: "tbLink", file: "tb.html", match: /tb\.html$/ };
  const RANK = { id: "rankLink", file: "ranking.html", match: /ranking\.html$/ };
  const TW = { id: "twLink", file: "tw.html", match: /tw\.html$/ };
  const EFF = { id: "effLink", file: "effectiveness.html", match: /effectiveness\.html$/ };
  const PLAT = { id: "platoonLink", file: "platoons.html", match: /platoons\.html$/ };
  const tab = t => `nav button[data-tab="${t}"]`;
  // officer tools, grouped; each lives on one page and can be started from any page (it opens that page and runs it)
  // sel = a button on that page; fn = the label the page registers with RaidTheme.menuItem("officer", ...)
  const OFFICER = [
    { key: "post", ic: "📣", label: "Post to Discord", kids: [
      { id: "post-raid", label: "Raid results", page: RAID, sel: "#postBtn" },
      { id: "post-ready", label: "Raid readiness", page: RAID, sel: "#postReadyBtn" },
      { id: "post-tb", label: "TB stats", page: TB, sel: "#postBtn" },
      { id: "post-tw", label: "TW stats", page: TW, sel: "#postBtn" },
      { id: "post-eff", label: "Guild effectiveness (officers)", page: EFF, sel: "#postBtn" },
      { id: "post-plat", label: "Platoons: one phase", page: PLAT, sel: "#postDiscord" },
      { id: "post-plat-all", label: "Platoons: whole guild", page: PLAT, sel: "#postAll" }] },
    { key: "oraid", ic: "⚔", label: "Raids", kids: [
      { id: "raid-targets", label: "Score targets", page: RAID, fn: "Raid score targets" }] },
    { key: "otb", ic: "◈", label: "Territory battles", kids: [
      { id: "tb-manage", label: "Manage TB uploads", page: TB, fn: "Manage TB uploads" },
      { id: "tb-stars", label: "Set TB stars", page: TB, fn: "Set TB stars" },
      { id: "tb-contrib", label: "Contribution settings", page: RANK, fn: "Contribution settings" }] },
    { key: "otw", ic: "✦", label: "Territory wars", kids: [
      { id: "tw-result", label: "Set the TW result", page: TW, sel: "#resultBtn" }] },
    { key: "oeff", ic: "◎", label: "Guild effectiveness", kids: [
      { id: "eff-weights", label: "Effectiveness weighting", page: EFF, fn: "Effectiveness weighting" }] },
    { key: "oplat", ic: "⚑", label: "RotE platoons", kids: [
      { id: "plat-data", label: "Planner data", page: PLAT, fn: "Platoon planner: data" },
      { id: "plat-ops", label: "Operations to fill", page: PLAT, fn: "Platoon planner: operations to fill" },
      { id: "plat-rules", label: "Rules", page: PLAT, fn: "Platoon planner: rules" }] },
  ];
  const OFF_FN = new Set(OFFICER.flatMap(g => g.kids).filter(k => k.fn).map(k => k.fn));
  const offReg = {};   // fn label -> the page's action
  const PAGES = [
    { key: "raids", ...RAID, ic: "⚔", label: "Raids", kids: [
      { label: "Overview", hash: "overview", sel: tab("overview") },
      { label: "Players", hash: "players", sel: tab("players") },
      { label: "Readiness", hash: "readiness", sel: tab("readiness") }] },
    { key: "player", id: "playerLink", file: "player.html", match: /player\.html$/, ic: "◉", label: "Player status" },
    { key: "overview", id: "overviewLink", file: "guild.html", match: /guild\.html$/, ic: "▦", label: "Guild overview", kids: [
      { label: "Stats", hash: "stats", sel: tab("stats") },
      { label: "Roster", hash: "roster", sel: tab("roster") },
      { label: "Abilities", hash: "abilities", sel: tab("abilities") }] },
    { key: "tb", ...TB, ic: "◈", label: "Territory battles", kids: [
      { label: "Overview", hash: "overview", sel: tab("overview") },
      { label: "Members", hash: "members", sel: tab("members") },
      { label: "Phases", hash: "phases", sel: tab("phases") },
      { label: "Player", hash: "player", sel: tab("player") },
      { label: "TB contribution", page: RANK }] },
    { key: "tw", ...TW, ic: "✦", label: "Territory wars", kids: [
      { label: "Overview", hash: "overview", sel: tab("overview") },
      { label: "Members", hash: "members", sel: tab("members") }] },
    { key: "eff", ...EFF, ic: "◎", label: "Guild effectiveness", kids: [
      { label: "Overview", hash: "" },
      { label: "Raids vs TBs", hash: "effQuad" },
      { label: "Ranking", hash: "effRank" },
      { label: "Members", hash: "effTable" },
      { label: "How it's worked out", hash: "effHow" }] },
    { key: "plat", ...PLAT, ic: "⚑", label: "RotE platoons", kids: [
      { label: "Assignments", hash: "assign", sel: "#assignBtn" },
      { label: "Summary", hash: "summary", sel: "#summaryBtn" },
      { label: "Requirements", hash: "requirements", sel: "#reqBtn" },
      { label: "Missing platoons", hash: "missing", sel: "#missingBtn" },
      { label: "Simulate", hash: "simulate", sel: "#simBtn" },
      { label: "Toon lookup", hash: "toon", sel: "#toonBtn" }] },
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
  /* page tree */
  .sb .sb-grp .car { margin-left: auto; flex: none; width: 14px; height: 14px; color: var(--text-2); transition: transform .15s ease; }
  .sb .sb-grp[aria-expanded="true"] .car { transform: rotate(90deg); }
  .sb .sb-grp.here { color: var(--accent) !important; }
  .sb .sb-kids { position: relative; margin: 0 0 4px 21px; padding-left: 10px; border-left: 1px solid var(--border); }
  .sb .sb-kids[hidden] { display: none; }
  .sb .sb-item.sb-kid { min-height: 32px; padding: 6px 10px !important; font: 500 13px var(--font-ui) !important; color: var(--text-2) !important; }
  .sb .sb-item.sb-kid[aria-current="page"]::before { left: -11px; top: 6px; bottom: 6px; }
  .sb .sb-item.sb-kid[aria-current="page"] { color: var(--accent) !important; font-weight: 650 !important; }
  body.sb-min .sb .sb-kids, body.sb-min .sb .car { display: none !important; }
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
    body.sb-min .sb .sb-kids:not([hidden]) { display: block !important; } body.sb-min .sb .car { display: inline-block !important; }
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

    // pages, each with its sections underneath as a tree
    const here = location.pathname, pagesSec = sb.querySelector('[data-sec="pages"]');
    const CARET = '<svg class="car" viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    const pageHref = p => {
      const own = document.getElementById(p.id), g = guildNow();
      let h = own && own.getAttribute("href") ? own.href.replace(/#.*$/, "") : p.file;
      if (g && !/[?&]guild=/.test(h)) h += (h.includes("?") ? "&" : "?") + "guild=" + encodeURIComponent(g);   // keep the guild you're looking at
      return h;
    };
    const watch = (p, fn) => { const own = document.getElementById(p.id); if (own && window.MutationObserver) new MutationObserver(fn).observe(own, { attributes: true, attributeFilter: ["hidden", "href"] }); };
    const ownHidden = p => { const own = document.getElementById(p.id); return !!(own && own.hidden && !p.match.test(here)); };
    const kidState = [];   // [link, kid, page] for highlighting the section you're on
    PAGES.forEach(p => {
      const onPage = p.match.test(here);
      if (!p.kids) {
        const a = document.createElement("a"); a.className = "sb-item"; iconise(a, `${p.ic} ${p.label}`);
        a.href = pageHref(p); ["pointerdown", "focus", "click"].forEach(ev => a.addEventListener(ev, () => { a.href = pageHref(p); }));
        if (onPage) a.setAttribute("aria-current", "page");
        const sync = () => { a.hidden = ownHidden(p); a.href = pageHref(p); }; sync(); watch(p, sync);
        pagesSec.appendChild(a); return;
      }
      const here2 = onPage || p.kids.some(k => k.page && k.page.match.test(here));
      const grp = document.createElement("button"); grp.type = "button"; grp.className = "sb-item sb-grp" + (here2 ? " here" : "");
      iconise(grp, `${p.ic} ${p.label}`); grp.insertAdjacentHTML("beforeend", CARET);
      const kids = document.createElement("div"); kids.className = "sb-kids"; kids.id = "sbk-" + p.key; grp.setAttribute("aria-controls", kids.id);
      const setOpen = v => { kids.hidden = !v; grp.setAttribute("aria-expanded", String(v)); };
      setOpen(here2);   // the page you're on starts open; the rest open with a click
      grp.onclick = () => {
        if (body.classList.contains("sb-min") && matchMedia("(min-width: 900px)").matches) { location.href = pageHref(p); return; }   // icon rail: go to the page
        setOpen(kids.hidden);
      };
      p.kids.forEach(k => {
        const kp = k.page || p, a = document.createElement("a"); a.className = "sb-item sb-kid"; a.textContent = k.label; a.title = k.label;
        const href = () => { const h = pageHref(kp); return k.page ? h : h.replace(/#.*$/, "") + (k.hash ? "#" + k.hash : ""); };
        a.href = href(); ["pointerdown", "focus"].forEach(ev => a.addEventListener(ev, () => { a.href = href(); }));
        a.addEventListener("click", e => {
          if (!kp.match.test(here) || k.page) return;            // another page: just follow the link
          e.preventDefault();                                      // this page: switch to that section here
          try { history.replaceState(null, "", location.pathname + location.search + (k.hash ? "#" + k.hash : "")); } catch (err) {}
          goSection(k); setTimeout(markKids, 50);
        });
        if (k.page) { const sync = () => { a.hidden = ownHidden(k.page); }; sync(); watch(k.page, sync); }
        kids.appendChild(a); kidState.push([a, k, kp]);
      });
      const sync = () => { const hid = ownHidden(p); grp.hidden = hid; kids.style.display = hid ? "none" : ""; }; sync(); watch(p, sync);
      pagesSec.appendChild(grp); pagesSec.appendChild(kids);
    });
    // officer tools as a tree
    const offSec = sb.querySelector('[data-sec="officer"]');
    const holder = document.createElement("div"); holder.hidden = true; holder.className = "sb-holder"; body.appendChild(holder);
    const kidHere = k => k.page.match.test(here);
    const runKid = k => {
      if (!kidHere(k)) { const h = pageHref(k.page); location.href = h + (h.includes("?") ? "&" : "?") + "do=" + encodeURIComponent(k.id); return; }
      if (k.fn) { const f = offReg[k.fn]; f ? f() : alertish("That isn't ready yet - try again in a moment."); return; }
      const el = document.querySelector(k.sel);
      if (!el || el.hidden) { alertish("There's nothing to post here for this guild yet."); return; }
      el.click();
    };
    OFFICER.forEach(gp => {
      const grp = document.createElement("button"); grp.type = "button"; grp.className = "sb-item sb-grp";
      iconise(grp, `${gp.ic} ${gp.label}`); grp.insertAdjacentHTML("beforeend", CARET);
      const kids = document.createElement("div"); kids.className = "sb-kids"; kids.id = "sbo-" + gp.key; grp.setAttribute("aria-controls", kids.id);
      const setOpen = v => { kids.hidden = !v; grp.setAttribute("aria-expanded", String(v)); }; setOpen(false);
      grp.onclick = () => {
        if (body.classList.contains("sb-min") && matchMedia("(min-width: 900px)").matches) { body.classList.remove("sb-min"); ls.set(SB_KEY, null); flipLabel(); setOpen(true); return; }
        setOpen(kids.hidden);
      };
      const btns = gp.kids.map(k => {
        const b = document.createElement("button"); b.type = "button"; b.className = "sb-item sb-kid"; b.textContent = k.label; b.title = k.label + (kidHere(k) ? "" : " (opens " + (k.page === RANK ? "TB contribution" : PAGES.find(p => p.id === k.page.id)?.label || "that page") + ")");
        b.onclick = () => runKid(k); kids.appendChild(b); return [b, k];
      });
      const sync = () => { let any = false; btns.forEach(([b, k]) => { b.hidden = ownHidden(k.page); any = any || !b.hidden; }); grp.hidden = !any; kids.style.display = any ? "" : "none"; };
      sync(); [...new Set(gp.kids.map(k => k.page))].forEach(p => watch(p, sync));
      offSec.appendChild(grp); offSec.appendChild(kids);
    });
    // arriving with ?do=<tool>: run it once the page has it ready
    (function fromDo() {
      const m = /[?&]do=([^&#]*)/.exec(location.search); if (!m) return;
      const id = decodeURIComponent(m[1]), k = OFFICER.flatMap(g => g.kids).find(x => x.id === id);
      const strip = () => { try { history.replaceState(null, "", location.pathname + location.search.replace(/([?&])do=[^&#]*&?/, "$1").replace(/[?&]$/, "") + location.hash); } catch (e) {} };
      if (id === "pull") { strip(); const t0 = Date.now(); (function w() { if (window.Officer) pullNow(); else if (Date.now() - t0 < 10000) setTimeout(w, 150); })(); return; }
      if (!k || !kidHere(k)) { strip(); return; }
      const t0 = Date.now();
      (function tryIt() {
        let ok = false;
        if (k.fn) ok = !!offReg[k.fn] && !!window.Officer;
        else { const el = document.querySelector(k.sel); ok = !!el && !el.hidden && !(el.closest("[hidden]") && !holder.contains(el)) && !!window.Officer; }
        if (ok) { strip(); runKid(k); return; }
        if (Date.now() - t0 < 15000) return setTimeout(tryIt, 200);
        strip(); runKid(k);
      })();
    })();

    // which section of this page is showing
    const isOn = el => !!el && (el.getAttribute("aria-selected") === "true" || el.getAttribute("aria-pressed") === "true");
    function markKids() {
      kidState.forEach(([a, k, kp]) => {
        let cur = false;
        if (kp.match.test(here)) {
          if (k.page) cur = true;
          else if (k.sel) cur = isOn(document.querySelector(k.sel));
          else { const h = location.hash.slice(1), hs = kidState.filter(([, x, y]) => y === kp && !x.sel && !x.page).map(([, x]) => x.hash); cur = hs.includes(h) ? h === k.hash : k.hash === ""; }
        }
        cur ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current");
      });
    }
    function goSection(k) {
      if (k.sel) {
        const el = document.querySelector(k.sel); if (!el) return;
        el.click();
        const r = el.getBoundingClientRect(); if (r.top < 0 || r.top > innerHeight * .6) el.scrollIntoView({ block: "start", behavior: reduceMotion ? "auto" : "smooth" });
      } else if (k.hash) { const t = document.getElementById(k.hash); if (t && t.tagName === "DETAILS") t.open = true; t?.scrollIntoView({ block: "start", behavior: reduceMotion ? "auto" : "smooth" }); }
      else scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
    }
    // arriving with #section: open that section once the page has loaded it (pages that don't handle the hash themselves)
    (function fromHash() {
      const h = location.hash.slice(1); if (!h) return;
      const hit = kidState.find(([, k, kp]) => !k.page && kp.match.test(here) && k.hash === h);
      if (!hit) return;
      if (!hit[1].sel) {   // a place on the page: go there again once charts have filled in above it
        const t = document.getElementById(h); if (t && t.tagName === "DETAILS") t.open = true;
        setTimeout(() => t?.scrollIntoView({ block: "start" }), 1200); return;
      }
      const t0 = Date.now();
      (function tryIt() {
        const el = document.querySelector(hit[1].sel);
        if (el && !el.closest("[hidden]") && !el.disabled) { if (!isOn(el)) el.click(); markKids(); return; }
        if (Date.now() - t0 < 15000) setTimeout(tryIt, 150);
      })();
    })();
    markKids();
    document.addEventListener("click", e => { if (e.target.closest(PAGES.flatMap(p => p.kids || []).filter(k => k.sel).map(k => k.sel).join(","))) setTimeout(markKids, 30); });
    addEventListener("hashchange", markKids);

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
    const drawer = v => { body.classList.toggle("sb-drawer", v); x.hidden = !v; openBtn.setAttribute("aria-expanded", String(v)); if (v) (sb.querySelector('.sb-kid[aria-current="page"]') || sb.querySelector('[aria-current="page"]') || x).focus(); };
    openBtn.onclick = () => drawer(true); x.onclick = () => { drawer(false); openBtn.focus(); }; scrim.onclick = () => drawer(false);
    document.addEventListener("keydown", e => { if (e.key === "Escape" && body.classList.contains("sb-drawer")) { drawer(false); openBtn.focus(); } });
    sb.addEventListener("click", e => { if (e.target.closest(".sb-body .sb-item:not(.sb-grp), .sb-body [data-menu]") && body.classList.contains("sb-drawer")) setTimeout(() => drawer(false), 0); });
    matchMedia("(min-width: 900px)").addEventListener?.("change", e => { if (e.matches) drawer(false); });

    // move the page's officer and upload controls in
    const claimed = OFFICER.flatMap(g => g.kids).filter(k => k.sel && kidHere(k)).map(k => document.querySelector(k.sel));
    document.querySelectorAll("[data-menu]").forEach(n => {
      if (n.dataset.menu === "officer" && claimed.includes(n)) { holder.appendChild(n); return; }   // started from the officer tree
      const sec = sb.querySelector(`[data-sec="${n.dataset.menu}"]`); if (sec) { iconise(n); sec.appendChild(n); }
    });
    if (!sb.querySelector('[data-sec="upload"] [data-menu]')) {
      const g = guildNow(), up = menuItem("upload", "⬆ Upload a WookieeBot file", "upload.html" + (g ? "?guild=" + encodeURIComponent(g) : ""));
      if (/upload\.html$/.test(here)) up.setAttribute("aria-current", "page");
    }
    menuItem("upload", "＋ Add a new guild", "upload.html#newguild");
    menuItem("upload", "🔗 Connect a guild to the game", "upload.html" + (guildNow() ? "?guild=" + encodeURIComponent(guildNow()) : "") + "#connect");
    menuItem("officer", "🔄 Pull from the game now", () => {
      if (window.Officer) return pullNow();
      const g = guildNow(); location.href = "./?" + (g ? "guild=" + encodeURIComponent(g) + "&" : "") + "do=pull";
    });
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
    Officer.form({ title: "Pull from the game now", trackLabel: "Pulling from the game",
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
    if (section === "officer" && typeof action === "function") {
      const t = String(label).trim().replace(/^[^\p{L}\p{N}\s]+\s*/u, "");
      if (OFF_FN.has(t)) { offReg[t] = action; return null; }   // shown in the officer tree instead
    }
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
    // wait (up to 8 s) for pictures such as unit portraits, so the posted image isn't full of gaps
    const imgs = [...document.images].filter(i => !i.complete);
    if (imgs.length) {
      imgs.forEach(i => { i.loading = "eager"; });
      await Promise.race([Promise.all(imgs.map(i => new Promise(r => { if (i.complete) r(); else { i.addEventListener("load", r, { once: true }); i.addEventListener("error", r, { once: true }); } }))), new Promise(r => setTimeout(r, 8000))]);
    }
    document.body.dataset.cardw = w;
    document.body.dataset.ready = "1";
  }
  // ---------------- site update progress ----------------
  // After an upload or "Pull from the game now", follow GitHub's site update with a progress bar,
  // then reload (or open the results) once the new site is live. Survives moving between pages.
  const UP_KEY = "gsUpdate";
  const UP_CSS = `
  .gs-up-line { position: fixed; left: 0; top: 0; height: 3px; z-index: 10001; background: var(--accent); box-shadow: 0 0 10px var(--accent); transition: width .6s ease; }
  .gs-up { position: fixed; right: 18px; bottom: 18px; z-index: 10000; width: min(360px, calc(100vw - 32px)); background: var(--surface-solid); color: var(--text);
    border: 1px solid var(--border); border-radius: 14px; box-shadow: 0 14px 40px rgba(0,0,0,.45); padding: 12px 14px; font: 13.5px/1.45 var(--font-ui); }
  .gs-up .h { display: flex; align-items: center; gap: 8px; font-weight: 700; }
  .gs-up .h span { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .gs-up .h b { font: 700 13px var(--font-display); color: var(--accent); }
  .gs-up .x { border: 0; background: none; color: var(--text-2); cursor: pointer; font-size: 16px; line-height: 1; padding: 2px 4px; }
  .gs-up .st { color: var(--text-2); font-size: 12.5px; margin: 4px 0 8px; }
  .gs-up .bar { height: 8px; border-radius: 6px; background: var(--surface-2); overflow: hidden; }
  .gs-up .bar i { display: block; height: 100%; width: 0; background: linear-gradient(90deg, var(--accent), color-mix(in srgb, var(--accent) 60%, #fff)); border-radius: 6px; transition: width .6s ease; }
  .gs-up.done .bar i { background: var(--good, #2fbf71); } .gs-up.fail .bar i { background: var(--bad, #e5484d); }
  .gs-up a { color: var(--accent); }
  html.cardmode .gs-up, html.cardmode .gs-up-line { display: none !important; }
  @media (max-width: 600px) { .gs-up { right: 16px; left: 16px; bottom: 12px; width: auto; } }`;
  const STEP_NAMES = [[/checkout|setup-python|pip install/i, "Getting ready"], [/what changed/i, "Checking what changed"], [/pull from the game/i, "Pulling from the game"],
    [/comlink|unit names/i, "Connecting to the game"], [/file uploads/i, "Filing the upload"], [/build/i, "Working out the stats"], [/configure-pages|upload-pages/i, "Packing up the site"],
    [/deploy-pages/i, "Publishing the site"]];
  const friendly = n => (STEP_NAMES.find(([re]) => re.test(n || "")) || [null, "Updating"])[1];
  let upTimer = null, upToken = null, upRepo = null;
  async function upRepoName() {
    if (upRepo) return upRepo;
    try { const c = await (await fetch("upload-config.json", { cache: "no-store" })).json(); upRepo = c && c.repository; } catch (e) {}
    if (!upRepo && /\.github\.io$/i.test(location.hostname)) upRepo = location.hostname.split(".")[0] + "/" + (location.pathname.split("/").filter(Boolean)[0] || "");
    return upRepo;
  }
  function upBox() {
    let box = document.getElementById("gsUp");
    if (box) return box;
    if (!document.getElementById("gsUpCss")) { const st = document.createElement("style"); st.id = "gsUpCss"; st.textContent = UP_CSS; document.head.appendChild(st); }
    const line = document.createElement("div"); line.className = "gs-up-line"; line.id = "gsUpLine"; line.style.width = "0";
    box = document.createElement("div"); box.className = "gs-up"; box.id = "gsUp"; box.setAttribute("role", "status"); box.setAttribute("aria-live", "polite");
    box.innerHTML = `<div class="h"><span id="gsUpT"></span><b id="gsUpP"></b><button class="x" type="button" title="Hide (the page still refreshes when it's done)" aria-label="Hide">×</button></div><div class="st" id="gsUpS"></div><div class="bar"><i id="gsUpB"></i></div>`;
    box.querySelector(".x").onclick = () => { box.hidden = true; };
    document.body.appendChild(line); document.body.appendChild(box);
    return box;
  }
  function upShow(job, pct, text, cls) {
    const box = upBox();
    box.classList.toggle("done", cls === "done"); box.classList.toggle("fail", cls === "fail");
    document.getElementById("gsUpT").textContent = job.label || "Updating the site";
    document.getElementById("gsUpP").textContent = pct == null ? "" : Math.round(pct) + "%";
    document.getElementById("gsUpS").innerHTML = text;
    document.getElementById("gsUpB").style.width = (pct ?? 0) + "%";
    document.getElementById("gsUpLine").style.width = cls ? "0" : (pct ?? 0) + "%";
  }
  const upSave = job => { try { job ? localStorage.setItem(UP_KEY, JSON.stringify(job)) : localStorage.removeItem(UP_KEY); } catch (e) {} };
  /** Follow the site update started by commit `sha`. opts: { sha, label, then (URL to open when done; default: reload), token, onDone, onFail } */
  function track(opts) {
    const job = { sha: opts.sha, label: opts.label || "Updating the site", then: opts.then || null, t0: Date.now(), runId: null };
    if (opts.token) upToken = opts.token;
    upSave(job); follow(job, opts);
  }
  async function follow(job, cb = {}) {
    clearTimeout(upTimer);
    const repo = await upRepoName();
    if (!repo || !job.sha) { upSave(null); return; }
    if (!upToken && window.Officer && Officer.authToken) { try { upToken = await Officer.authToken(); } catch (e) {} }
    const api = async p => { const r = await fetch("https://api.github.com/repos/" + repo + p, { cache: "no-store", headers: { Accept: "application/vnd.github+json", ...(upToken ? { Authorization: "Bearer " + upToken } : {}) } }); if (!r.ok) { const e = new Error(String(r.status)); e.status = r.status; throw e; } return r.json(); };
    const runsUrl = `https://github.com/${repo}/actions`;
    const elapsed = () => (Date.now() - job.t0) / 1000;
    const finish = () => {
      upSave(null); upShow(job, 100, "Done - the site is updated. Refreshing…", "done");
      if (cb.onDone) cb.onDone();
      setTimeout(() => { if (job.then) location.href = job.then; else location.reload(); }, 2500);
    };
    const fail = (html) => { upSave(null); upShow(job, 100, html, "fail"); if (cb.onFail) cb.onFail(html); };
    const tick = async () => {
      if (elapsed() > 20 * 60) { fail(`This is taking longer than usual. <a href="${runsUrl}" target="_blank" rel="noopener">Check on GitHub</a>.`); return; }
      try {
        if (!job.runId) {
          const r = await api(`/actions/runs?head_sha=${job.sha}&per_page=5`);
          const run = (r.workflow_runs || [])[0];
          if (!run) {
            if (elapsed() > 75) {   // GitHub never started an update: the upload didn't change anything
              let empty = false; try { empty = !((await api(`/commits/${job.sha}`)).files || []).length; } catch (e) {}
              if (empty) { upSave(null); upShow(job, 100, "Nothing to update - that was the same as what's already saved.", "done"); setTimeout(() => { const b = document.getElementById("gsUp"); if (b) b.hidden = true; }, 6000); return; }
            }
            upShow(job, Math.min(8, 2 + elapsed() / 10), "Sent. Waiting for GitHub to start the update…");
            upTimer = setTimeout(tick, 6000); return;
          }
          job.runId = run.id; upSave(job);
        }
        const run = await api(`/actions/runs/${job.runId}`);
        if (run.status === "completed" && run.conclusion === "cancelled") {   // replaced by a newer update that includes this one
          const r = await api(`/actions/runs?branch=${encodeURIComponent(run.head_branch || "main")}&per_page=1`);
          const nr = (r.workflow_runs || [])[0];
          if (nr && nr.id !== job.runId) { job.runId = nr.id; upSave(job); upTimer = setTimeout(tick, 3000); return; }
          fail(`GitHub cancelled the update. <a href="${runsUrl}" target="_blank" rel="noopener">Check on GitHub</a>.`); return;
        }
        if (run.status === "queued" || run.status === "waiting" || run.status === "pending" || run.status === "requested") {
          upShow(job, 10, "Waiting for an earlier update to finish first…"); upTimer = setTimeout(tick, 8000); return;
        }
        const jobs = (await api(`/actions/runs/${job.runId}/jobs`)).jobs || [];
        const steps = (jobs[0] && jobs[0].steps) || [];
        const dep = steps.findIndex(s => /deploy-pages/i.test(s.name));
        const last = dep >= 0 ? dep : steps.length - 1;
        if (dep >= 0 && steps[dep].status === "completed" && steps[dep].conclusion === "success") { finish(); return; }
        if (steps.some((s, i) => i <= last && s.conclusion === "failure") || (run.status === "completed" && run.conclusion !== "success")) {
          if (run.status === "completed" && run.conclusion === "success") { finish(); return; }
          fail(`The site update failed. <a href="${esc(run.html_url || runsUrl)}" target="_blank" rel="noopener">See what went wrong on GitHub</a>.`); return;
        }
        if (run.status === "completed") { finish(); return; }
        const doneN = steps.slice(0, last + 1).filter(s => s.status === "completed").length, cur = steps.find(s => s.status === "in_progress");
        const pct = 12 + (last > 0 ? doneN / (last + 1) * 85 : Math.min(85, elapsed() / 2));
        upShow(job, Math.min(97, pct), (cur ? friendly(cur.name) : "Updating the site") + "…");
      } catch (e) {
        if (e.status === 403 || e.status === 429) {   // GitHub's limit for checking without a login: estimate instead
          const pct = Math.min(95, 5 + elapsed() / 180 * 90);
          upShow(job, pct, "Updating the site (about 3 minutes)…");
          if (elapsed() > 240) { finish(); return; }
        }
      }
      upTimer = setTimeout(tick, 7000);
    };
    upShow(job, 3, "Sent. Waiting for GitHub to start the update…");
    tick();
  }
  function resumeTrack() {
    let job = null; try { job = JSON.parse(localStorage.getItem(UP_KEY) || "null"); } catch (e) {}
    if (!job || !job.sha) return;
    if (Date.now() - job.t0 > 25 * 60 * 1000) { upSave(null); return; }
    follow(job);
  }

  window.RaidTheme = { banner, isDark, emblem, cardReady, menuItem, mountToggle, track };
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
  // ---------------- guild picker: the banner's guild buttons become one dropdown ----------------
  // The page still draws its buttons (hidden); the dropdown mirrors them and clicks the chosen one.
  // The choice is remembered on this device and carried to every page (see the snippet in each page's head).
  function mountGuildSelect() {
    const pills = document.getElementById("guildSwitch");
    if (!pills || root.classList.contains("cardmode")) return;
    if (!document.getElementById("gsGselCss")) {
      const st = document.createElement("style"); st.id = "gsGselCss";
      st.textContent = `#guildSwitch.gs-replaced { display: none !important; }
      .gs-gsel { display: inline-flex; align-items: center; gap: 8px; }
      .gs-gsel span { font: 700 10.5px var(--font-display); letter-spacing: .16em; text-transform: uppercase; color: rgba(230,236,255,.75); }
      .gs-gsel select { appearance: none; -webkit-appearance: none; background: rgba(5,7,15,.55) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' fill='none' stroke='%23e6ecff' stroke-width='1.6'/%3E%3C/svg%3E") no-repeat right 12px center / 11px 8px;
        color: #f2f5ff; border: 1px solid rgba(230,236,255,.35); border-radius: 999px; padding: 7px 34px 7px 14px; font: 600 13.5px var(--font-ui); cursor: pointer; max-width: 260px;
        -webkit-backdrop-filter: blur(6px); backdrop-filter: blur(6px); }
      .gs-gsel select:hover, .gs-gsel select:focus { border-color: #8fdcff; outline: none; }
      .gs-gsel select option { background: var(--surface-solid); color: var(--text); }`;
      document.head.appendChild(st);
    }
    const wrap = document.createElement("label"); wrap.className = "gs-gsel"; wrap.hidden = true;
    wrap.innerHTML = `<span>Guild</span><select aria-label="Guild"></select>`;
    pills.after(wrap); pills.classList.add("gs-replaced");
    const sel = wrap.querySelector("select");
    const btns = () => [...pills.querySelectorAll("button")];
    const valOf = b => b.dataset.id || b.dataset.slug || b.textContent.trim();
    const sync = () => {
      const bs = btns();
      wrap.hidden = pills.hidden || bs.length < 2;
      const sig = bs.map(b => valOf(b) + (b.getAttribute("aria-pressed") === "true" ? "*" : "")).join("|");
      if (sel.dataset.sig === sig) return;
      sel.dataset.sig = sig;
      sel.innerHTML = bs.map(b => `<option value="${esc(valOf(b))}"${b.getAttribute("aria-pressed") === "true" ? " selected" : ""}>${esc(b.textContent.trim())}</option>`).join("");
    };
    sel.onchange = () => {
      ls.set(G_KEY, sel.value);
      const b = btns().find(x => valOf(x) === sel.value);
      if (b) b.click();
    };
    sync();
    if (window.MutationObserver) new MutationObserver(sync).observe(pills, { childList: true, subtree: true, attributes: true, attributeFilter: ["hidden", "aria-pressed"] });
  }
  // remember the guild this page shows, so the next page opens on it too
  function rememberGuild() {
    const g = /[?&]guild=([^&#]*)/.exec(location.search);
    if (g && g[1]) ls.set(G_KEY, decodeURIComponent(g[1]));
  }
  if (window.history && history.replaceState) {
    const rs = history.replaceState.bind(history);
    history.replaceState = function () { const r = rs.apply(history, arguments); try { if (!root.classList.contains("cardmode")) rememberGuild(); } catch (e) {} return r; };
  }

  const ready = () => { if (!root.classList.contains("cardmode")) { resumeTrack(); rememberGuild(); mountGuildSelect();
    const up = /upload\.html$/.test(location.pathname) && document.querySelector("select#guild"); if (up) up.addEventListener("change", () => { if (up.value) ls.set(G_KEY, up.value); }); } cardFoot(); mountSky(); document.querySelectorAll("[data-theme-toggle], [data-site-menu]").forEach(mountMenu); pending.splice(0).forEach(a => menuItem(...a)); if (window.MutationObserver && menuPanel) new MutationObserver(tidy).observe(menuPanel, { subtree: true, attributes: true, attributeFilter: ["hidden"] }); document.querySelectorAll("[data-emblem]").forEach(e => e.innerHTML = emblem); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready); else ready();
})();
