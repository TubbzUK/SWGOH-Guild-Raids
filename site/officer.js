/* Officer actions shared by the pages: unlock with the officer password (same one as the upload page)
   and ask GitHub to post a results panel to Discord.

   Officer.postButton(button, () => ({ guild, kind, label, ...extra }))
     kind: "raid" (with raid), "tb" (with tb), "effectiveness", "platoons" (with phase, text), "platoons-all" (with text)
   A click asks for the officer password if needed, confirms, then saves a small request file
   (guilds/<guild>/posts/<time>-<kind>.json). The site update that follows posts it to Discord
   and removes the request. */
(function () {
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }, del(k) { try { localStorage.removeItem(k); } catch (e) {} } };
  const te = new TextEncoder(), td = new TextDecoder(), unb64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
  let TOKEN = null, site = null;

  const CSS = `
  .off-dlg { border: 1px solid var(--border); border-radius: 14px; background: var(--surface-solid); color: var(--text); padding: 18px 20px; width: min(440px, calc(100vw - 32px)); box-shadow: 0 20px 60px rgba(0,0,0,.45); font: 15px/1.5 var(--font-ui); }
  .off-dlg::backdrop { background: rgba(3, 5, 11, .6); }
  .off-dlg h2 { font: 700 13px var(--font-display); letter-spacing: .1em; text-transform: uppercase; margin: 0 0 8px; }
  .off-dlg p, .off-dlg .off-text { font-size: 13.5px; color: var(--text-2); margin: 0 0 12px; }
  .off-dlg.wide { width: min(680px, calc(100vw - 32px)); }
  .off-dlg input[type=password] { width: 100%; background: var(--surface); color: var(--text); border: 1px solid var(--border); border-radius: 8px; padding: 9px 12px; font: 14px var(--font-ui); }
  .off-dlg label { display: flex; gap: 6px; align-items: center; color: var(--text-2); font-size: 13px; margin-top: 10px; }
  .off-dlg .row { display: flex; gap: 8px; justify-content: flex-end; margin-top: 14px; }
  .off-dlg button { border: 1px solid var(--border); background: var(--surface); color: var(--text); border-radius: 8px; padding: 7px 14px; font: 600 13px var(--font-ui); cursor: pointer; }
  .off-dlg button.primary { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); }
  .off-dlg button:disabled { opacity: .5; cursor: default; }
  .off-msg { border-radius: 8px; padding: 8px 12px; font-size: 13px; margin-top: 10px; }
  .off-msg.err { background: var(--bad-bg); color: var(--bad-ink); } .off-msg.ok { background: var(--good-bg); color: var(--good-ink); } .off-msg.info { background: var(--surface-2); color: var(--text-2); }
  .off-toast { position: fixed; left: 50%; bottom: 22px; transform: translateX(-50%); z-index: 9999; max-width: calc(100vw - 32px); background: var(--surface-solid); color: var(--text); border: 1px solid var(--accent); border-radius: 12px; padding: 10px 16px; font: 14px var(--font-ui); box-shadow: 0 10px 30px rgba(0,0,0,.4); }
  `;
  function mount() {
    if ($("#offDlg")) return;
    const st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st);
    const d = document.createElement("dialog"); d.id = "offDlg"; d.className = "off-dlg";
    d.innerHTML = `<form method="dialog" id="offForm"><h2 id="offTitle">Post to Discord</h2><div id="offText" class="off-text"></div>
      <div id="offPw"><input type="password" id="offPass" autocomplete="current-password" spellcheck="false" aria-label="Officer password" placeholder="Officer password">
      <label><input type="checkbox" id="offRemember" checked> Remember on this device</label></div>
      <div id="offMsg"></div>
      <div class="row"><button type="button" id="offCancel">Cancel</button><button type="submit" class="primary" id="offGo">Post</button></div></form>`;
    document.body.appendChild(d);
    $("#offCancel").onclick = () => d.close();
  }
  const msg = (cls, text) => { $("#offMsg").innerHTML = cls ? `<div class="off-msg ${cls}">${text}</div>` : ""; };
  function toast(text) {
    const t = document.createElement("div"); t.className = "off-toast"; t.innerHTML = text; document.body.appendChild(t);
    setTimeout(() => t.remove(), 7000);
  }

  async function loadSite() {
    if (site) return site;
    const get = u => fetch(u, { cache: "no-store" }).then(r => r.ok ? r.json() : null).catch(() => null);
    const [cfg, key] = await Promise.all([get("upload-config.json"), get("upload-key.json")]);
    let repo = cfg && cfg.repository;
    if (!repo && /\.github\.io$/i.test(location.hostname)) repo = location.hostname.split(".")[0] + "/" + (location.pathname.split("/").filter(Boolean)[0] || "");
    return (site = { repo, branch: (cfg && cfg.branch) || "main", key: key && key.data ? key : null });
  }
  async function unlockBlob(blob, pw) {
    try {
      const base = await crypto.subtle.importKey("raw", te.encode(pw), "PBKDF2", false, ["deriveKey"]);
      const key = await crypto.subtle.deriveKey({ name: "PBKDF2", salt: unb64(blob.salt), iterations: blob.iterations, hash: "SHA-256" }, base, { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
      return td.decode(await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(blob.iv) }, key, unb64(blob.data)));
    } catch (e) { return null; }
  }
  async function remembered() {
    const s = await loadSite(), pw = store.get("raidTrackerPassword"), tk = store.get("raidTrackerToken");
    if (pw && s.key) { const t = await unlockBlob(s.key, pw); if (t) return t; }
    return tk || null;
  }
  async function login(secret) {
    const s = await loadSite();
    if (s.key) { const t = await unlockBlob(s.key, secret); if (t) return { t, kind: "pw" }; }
    return /^(github_pat_|ghp_)/.test(secret) ? { t: secret, kind: "tok" } : null;
  }
  const gh = (path, opts = {}) => fetch("https://api.github.com" + path, { ...opts, headers: { Authorization: `Bearer ${TOKEN}`, Accept: "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", ...(opts.body ? { "Content-Type": "application/json" } : {}) } });
  async function putFile(path, text, message) {
    const s = await loadSite();
    if (!s.repo) throw new Error("the site settings haven't loaded, so it doesn't know which repository to use");
    const bytes = te.encode(text); let bin = ""; bytes.forEach(b => bin += String.fromCharCode(b));
    const res = await gh(`/repos/${s.repo}/contents/${path.split("/").map(encodeURIComponent).join("/")}`, { method: "PUT", body: JSON.stringify({ message, content: btoa(bin), branch: s.branch }) });
    if (!res.ok) {
      if (res.status === 401) { TOKEN = null; throw new Error("GitHub didn't accept the login (the token behind the officer password may have expired)"); }
      if (res.status === 403 || res.status === 404) throw new Error("the GitHub token isn't allowed to save to this repository");
      throw new Error(`GitHub said ${res.status}`);
    }
    try { return lastSha = (await res.json()).commit.sha; } catch (e) { return null; }
  }
  let lastSha = null;

  async function requestPost(req) {
    const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\..*/, "").replace("T", "-");
    const body = { ...req, requested_at: new Date().toISOString() };
    delete body.label;
    await putFile(`guilds/${req.guild}/posts/${stamp}-${req.kind}.json`, JSON.stringify(body, null, 1), `Post ${req.label || req.kind} to Discord`);
  }

  /** Ask (password if needed) and confirm, then queue the post. */
  async function post(req) {
    mount();
    const d = $("#offDlg");
    if (!TOKEN) TOKEN = await remembered();
    const s = await loadSite();
    d.classList.remove("wide"); $("#offTitle").textContent = "Post to Discord"; $("#offGo").textContent = "Post";
    $("#offText").innerHTML = `Post <b>${esc(req.label)}</b> to the guild's ${String(req.kind).startsWith("platoons") ? "assignments" : req.kind === "effectiveness" ? "officers'" : "Discord"} channel? It appears about 3 minutes from now, once the site has updated.`
      + (TOKEN ? "" : `<br><br>${s.key ? "Enter the officer password (the same one as the upload page)." : "No officer password is set up yet: enter a GitHub access token."}`);
    $("#offPw").hidden = !!TOKEN; $("#offPass").value = ""; msg(); $("#offGo").disabled = false;
    $("#offForm").onsubmit = async e => {
      e.preventDefault();
      $("#offGo").disabled = true;
      if (!TOKEN) {
        const secret = $("#offPass").value.trim(); if (!secret) { $("#offGo").disabled = false; return; }
        msg("info", "Checking…");
        const r = await login(secret);
        if (!r) { msg("err", s.key ? "That password isn't right." : "That doesn't look like a GitHub token (they start github_pat_)."); $("#offGo").disabled = false; return; }
        TOKEN = r.t;
        if ($("#offRemember").checked) store.set(r.kind === "pw" ? "raidTrackerPassword" : "raidTrackerToken", secret);
      }
      msg("info", "Sending…");
      try {
        await requestPost(req);
        d.close();
        toast(`📣 Queued: <b>${esc(req.label)}</b> will appear in Discord in about 3 minutes.`);
      } catch (err) { msg("err", `Couldn't queue the post: ${esc(err.message)}.`); $("#offGo").disabled = false; }
    };
    d.showModal ? d.showModal() : d.setAttribute("open", "");
    if (!TOKEN) setTimeout(() => $("#offPass").focus(), 50);
  }

  async function getJSONFile(path) {
    const st = await loadSite();
    const res = await gh(`/repos/${st.repo}/contents/${path.split("/").map(encodeURIComponent).join("/")}?ref=${encodeURIComponent(st.branch)}`);
    if (!res.ok) return { data: null, sha: null };
    const j = await res.json();
    try { return { data: JSON.parse(td.decode(unb64(j.content.replace(/\s/g, "")))), sha: j.sha }; } catch (e) { return { data: null, sha: j.sha }; }
  }
  async function putFileSha(path, text, message, sha) {
    const st = await loadSite();
    const bytes = te.encode(text); let bin = ""; bytes.forEach(b => bin += String.fromCharCode(b));
    const res = await gh(`/repos/${st.repo}/contents/${path.split("/").map(encodeURIComponent).join("/")}`, { method: "PUT", body: JSON.stringify({ message, content: btoa(bin), branch: st.branch, ...(sha ? { sha } : {}) }) });
    if (!res.ok) throw new Error(res.status === 401 ? "GitHub didn't accept the login" : res.status === 409 ? "someone else saved at the same time - try again" : `GitHub said ${res.status}`);
    try { return lastSha = (await res.json()).commit.sha; } catch (e) { return null; }
  }

  /** A general officer form: title, body HTML, a button label, and run() which saves (after the password). */
  async function form({ title, html, button, run, done, wide, ready, trackLabel }) {
    mount();
    const d = $("#offDlg");
    d.classList.toggle("wide", !!wide);
    if (!TOKEN) TOKEN = await remembered();
    const s = await loadSite();
    $("#offTitle").textContent = title;
    $("#offText").innerHTML = html + (TOKEN ? "" : `<br><br>${s.key ? "Enter the officer password (the same one as the upload page)." : "No officer password is set up yet: enter a GitHub access token."}`);
    $("#offPw").hidden = !!TOKEN; $("#offPass").value = ""; msg(); $("#offGo").disabled = false; $("#offGo").textContent = button || "Save";
    if (ready) ready();
    $("#offForm").onsubmit = async e => {
      e.preventDefault();
      $("#offGo").disabled = true;
      if (!TOKEN) {
        const secret = $("#offPass").value.trim(); if (!secret) { $("#offGo").disabled = false; return; }
        msg("info", "Checking…");
        const r = await login(secret);
        if (!r) { msg("err", s.key ? "That password isn't right." : "That doesn't look like a GitHub token (they start github_pat_)."); $("#offGo").disabled = false; return; }
        TOKEN = r.t;
        if ($("#offRemember").checked) store.set(r.kind === "pw" ? "raidTrackerPassword" : "raidTrackerToken", secret);
      }
      msg("info", "Saving…");
      try {
        lastSha = null;
        await run({ getJSONFile, putFile: putFileSha, gh, site: await loadSite() });
        d.close();
        // follow the site update with a progress bar, then refresh the page once it's live
        if (lastSha && window.RaidTheme && RaidTheme.track) RaidTheme.track({ sha: lastSha, label: trackLabel || title, token: TOKEN });
        else if (done) toast(done);
      }
      catch (err) { msg("err", `Couldn't save: ${esc(err.message)}.`); $("#offGo").disabled = false; }
    };
    d.showModal ? d.showModal() : d.setAttribute("open", "");
    if (!TOKEN) setTimeout(() => $("#offPass").focus(), 50);
  }

  function postButton(btn, getReq) {
    if (!btn) return;
    btn.addEventListener("click", () => { const r = getReq(); if (r) post(r); });
  }

  // ---------- Discord webhooks for any guild, saved straight into the repository's GitHub secrets ----------
  const loadScript = src => new Promise((res, rej) => { if (document.querySelector(`script[src="${src}"]`)) return res(); const s = document.createElement("script"); s.src = src; s.onload = res; s.onerror = () => rej(new Error("couldn't load " + src)); document.head.appendChild(s); });
  const HOOK_RE = /^https:\/\/(?:ptb\.|canary\.)?discord(?:app)?\.com\/api\/webhooks\/\d+\/[\w-]+$/;
  const KINDS = [
    { k: "main", name: g => `DISCORD_WEBHOOK_${g}`, label: "Main channel", hint: "raid results and readiness, TB and TW stats" },
    { k: "officers", name: g => `OFFICER_${g}`, label: "Officers' channel", hint: "guild effectiveness (falls back to the main channel)" },
    { k: "assign", name: g => `${g}_ASSIGN`, label: "Platoon assignments", hint: "each TB phase's platoons, posted automatically" },
  ];
  async function webhooks(slug) {
    let guilds = [];
    try { guilds = await (await fetch("guilds.json", { cache: "no-store" })).json(); } catch (e) {}
    if (!guilds.length) { toast("No guilds found."); return; }
    let cur = guilds.find(g => g.slug === slug) || guilds[0];
    const up = s => s.toUpperCase().replace(/[^A-Z0-9]/g, "_");
    const inp = "width:100%;box-sizing:border-box;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:8px;padding:8px 10px;font:13.5px var(--font-ui)";
    const html = `<p style="margin:0 0 10px">Paste a Discord webhook for each channel. It's saved straight into the site's GitHub secrets (encrypted - nobody can read it back, not even here), so there's no need to go to GitHub. In Discord: channel settings → Integrations → Webhooks → New Webhook → Copy Webhook URL.</p>
      <label style="display:block;margin:6px 0 4px;font-weight:600;color:var(--text)">Guild</label>
      <select id="whGuild" style="${inp}">${guilds.map(g => `<option value="${esc(g.slug)}" ${g.slug === cur.slug ? "selected" : ""}>${esc(g.name)}</option>`).join("")}</select>
      <div id="whRows" style="margin-top:6px"></div>
      <div style="border:1px dashed var(--border);border-radius:10px;padding:10px 12px;margin-top:14px">
        <div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap"><b style="color:var(--text)">Discord bot (for DMs, every guild)</b><span style="font-size:12px" id="botState"></span></div>
        <div style="font-size:12.5px;margin:2px 0 6px">The bot that DMs members their own platoons. Developer Portal → your application → Bot → Reset Token → copy.</div>
        <input type="password" autocomplete="off" spellcheck="false" id="whBot" placeholder="Leave empty to keep the current bot token" style="${inp}">
      </div><div id="whNote" style="margin-top:10px;font-size:12.5px"></div>`;
    let existing = null;   // secret name -> updated_at (null = couldn't read)
    const drawRows = () => {
      const G = up(cur.slug);
      $("#whRows").innerHTML = KINDS.map(k => { const n = k.name(G), set = existing && existing[n];
        return `<div style="border:1px solid var(--border);border-radius:10px;padding:10px 12px;margin-top:10px">
          <div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap"><b style="color:var(--text)">${esc(k.label)}</b><span style="font-size:12px">${existing ? (set ? `✓ set ${esc(new Date(set).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }))}` : "not set") : ""} · <code>${esc(n)}</code></span></div>
          <div style="font-size:12.5px;margin:2px 0 6px">${esc(k.hint)}</div>
          <input type="password" autocomplete="off" spellcheck="false" data-wh="${k.k}" placeholder="${set ? "Leave empty to keep the current webhook" : "https://discord.com/api/webhooks/…"}" style="${inp}">
          <div style="display:flex;gap:12px;align-items:center;margin-top:6px;flex-wrap:wrap"><button type="button" data-test="${k.k}" style="font-size:12px;padding:4px 10px">Send a test message</button>${set ? `<label style="margin:0;font-size:12.5px"><input type="checkbox" data-del="${k.k}"> Remove this webhook</label>` : ""}<span data-msg="${k.k}" style="font-size:12.5px"></span></div></div>`; }).join("");
      $("#botState").innerHTML = existing ? (existing.DISCORD_BOT_TOKEN ? `✓ set · <code>DISCORD_BOT_TOKEN</code>` : "not set · <code>DISCORD_BOT_TOKEN</code>") : "";
      $("#whRows").querySelectorAll("[data-test]").forEach(b => b.onclick = async () => {
        const k = b.dataset.test, url = $(`[data-wh="${k}"]`).value.trim(), m = $(`[data-msg="${k}"]`);
        if (!HOOK_RE.test(url)) { m.textContent = "Paste the webhook first."; return; }
        m.textContent = "Sending…";
        try { const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: `✅ Test from Guild Statistics: this channel will get ${KINDS.find(x => x.k === k).hint} for ${cur.name}.` }) });
          m.textContent = r.ok ? "✓ Sent - check the channel" : `Discord said ${r.status} - check the webhook`; }
        catch (e) { m.textContent = "The browser couldn't send it (Discord may block that) - it will still work from the site."; }
      });
    };
    const loadExisting = async () => {
      existing = null;
      try { const s = await loadSite(); const r = await gh(`/repos/${s.repo}/actions/secrets?per_page=100`);
        if (r.ok) { existing = {}; ((await r.json()).secrets || []).forEach(x => existing[x.name] = x.updated_at || x.created_at); $("#whNote").textContent = ""; }
        else if (r.status === 403 || r.status === 404) $("#whNote").innerHTML = `<span style="color:var(--bad-ink)">The GitHub token behind the officer password isn't allowed to manage secrets yet. Ask the repository owner to edit it once on GitHub (Settings → Developer settings → Fine-grained tokens → the site's token → Repository permissions → <b>Secrets: Read and write</b>). After that, webhooks can be set here.</span>`;
      } catch (e) {}
      drawRows();
    };
    form({ title: "Discord webhooks", wide: true, html, button: "Save webhooks",
      ready: () => { drawRows(); (async () => { if (!TOKEN) TOKEN = await remembered(); if (TOKEN) loadExisting(); })();
        $("#whGuild").onchange = () => { cur = guilds.find(g => g.slug === $("#whGuild").value) || cur; drawRows(); }; },
      run: async () => {
        const s = await loadSite(), G = up(cur.slug), jobs = [];
        for (const k of KINDS) {
          const url = $(`[data-wh="${k.k}"]`).value.trim(), del = $(`[data-del="${k.k}"]`)?.checked;
          if (url && !HOOK_RE.test(url)) throw new Error(`the ${k.label.toLowerCase()} webhook doesn't look like a Discord webhook (it starts https://discord.com/api/webhooks/)`);
          if (url) jobs.push({ name: k.name(G), url }); else if (del) jobs.push({ name: k.name(G), del: true });
        }
        const bot = $("#whBot").value.trim();
        if (bot) { if (!/^[\w-]{20,}\.[\w-]{4,}\.[\w-]{20,}$/.test(bot)) throw new Error("that doesn't look like a Discord bot token (three parts separated by dots)"); jobs.push({ name: "DISCORD_BOT_TOKEN", url: bot }); }
        if (!jobs.length) throw new Error("nothing to save - paste a webhook, or tick Remove");
        const dels = jobs.filter(j => j.del).map(j => j.name);
        if (dels.length && !confirm(`Remove ${dels.join(", ")}? Posts that use it will stop until a new webhook is set.`)) throw new Error("cancelled");
        let key = null;
        if (jobs.some(j => j.url)) {
          const kr = await gh(`/repos/${s.repo}/actions/secrets/public-key`);
          if (!kr.ok) throw new Error(kr.status === 403 || kr.status === 404 ? "the GitHub token isn't allowed to manage secrets (it needs Secrets: Read and write)" : `GitHub said ${kr.status}`);
          key = await kr.json();
          await loadScript("vendor/nacl-fast.min.js"); await loadScript("vendor/sealedbox.web.js");
        }
        for (const j of jobs) {
          const path = `/repos/${s.repo}/actions/secrets/${encodeURIComponent(j.name)}`;
          if (j.del) { const r = await gh(path, { method: "DELETE" }); if (!r.ok && r.status !== 404) throw new Error(`couldn't remove ${j.name} (GitHub said ${r.status})`); continue; }
          const sealed = window.sealedBox.seal(te.encode(j.url), unb64(key.key));
          let bin = ""; sealed.forEach(b => bin += String.fromCharCode(b));
          const r = await gh(path, { method: "PUT", body: JSON.stringify({ encrypted_value: btoa(bin), key_id: key.key_id }) });
          if (!r.ok) throw new Error(`couldn't save ${j.name} (GitHub said ${r.status})`);
        }
      },
      done: `🔗 Webhooks saved. Posts use them from now on.` });
  }

  // ---------- who gets their platoons by DM: members opt in by reacting ✅; officers confirm the in-game names ----------
  async function discordDms(slug) {
    let guilds = [];
    try { guilds = await (await fetch("guilds.json", { cache: "no-store" })).json(); } catch (e) {}
    const g = guilds.find(x => x.slug === slug) || guilds[0];
    if (!g) { toast("No guilds found."); return; }
    if (!TOKEN) TOKEN = await remembered();
    let st = {}, saved = {}, sha = null, players = [];
    for (const fn of ["platoon-roster.json", "rosters.json"]) { if (players.length) break;
      try { const r = await fetch(`data/${encodeURIComponent(g.slug)}/${fn}`, { cache: "no-store" }); if (r.ok) players = ((await r.json()).players || []).map(p => typeof p === "string" ? p : p.name).filter(Boolean).sort((a, b) => a.localeCompare(b)); } catch (e) {} }
    if (TOKEN) { try { st = (await getJSONFile(`guilds/${g.slug}/discord.json`)).data || {}; const l = await getJSONFile(`guilds/${g.slug}/discord-links.json`); saved = (l.data && l.data.links) || {}; sha = l.sha; } catch (e) {} }
    const opt = Object.entries(st.optin || {}).sort((a, b) => (a[1].nick || a[1].name || "").localeCompare(b[1].nick || b[1].name || ""));
    const auto = st.auto || {}, failed = st.dm_failed || {};
    const sel = (uid, curName, sure) => `<select data-uid="${esc(uid)}" style="width:100%;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:8px;padding:6px 8px;font:13px var(--font-ui)">
      <option value="">— not linked (no DMs) —</option>${players.map(p => `<option value="${esc(p)}" ${p === curName ? "selected" : ""}>${esc(p)}${p === curName && !(uid in saved) ? (sure ? " (matched)" : " (best guess - check)") : ""}</option>`).join("")}</select>`;
    const rows = opt.map(([uid, r]) => { const a = auto[uid] || {}, cur = uid in saved ? saved[uid] : (a.player || ""), who = [r.nick, r.name && r.name !== r.nick ? r.name : "", r.user ? "@" + r.user : ""].filter(Boolean).join(" · ");
      return `<tr style="border-top:1px solid var(--border)"><td style="padding:7px 8px">${esc(who)}${failed[uid] ? `<div style="font-size:11.5px;color:var(--bad-ink)">Last DM failed: ${esc(failed[uid])}</div>` : ""}</td><td style="padding:7px 8px;min-width:180px">${sel(uid, cur, a.sure)}</td></tr>`; }).join("");
    const html = `<p style="margin:0 0 8px">Members choose DMs themselves: the bot has put a message in the assignments channel, and anyone who reacts ✅ gets their own list by DM when each phase starts (removing the reaction stops it). Their Discord name is matched to an in-game name; confirm or fix the links below. Anyone left "not linked" gets no DMs.</p>
      ${!TOKEN ? `<p style="color:var(--bad-ink)">Enter the officer password (Save below) to see who has opted in.</p>` : !st.optin_message_id ? `<p style="font-size:13px">The bot hasn't posted its opt-in message yet. It does that within 15 minutes of the bot token and the assignments webhook being set (Officers → Discord webhooks), once the bot is in the server.</p>` : ""}
      ${opt.length ? `<div style="max-height:50vh;overflow:auto;border:1px solid var(--border);border-radius:10px"><table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr style="background:var(--surface-2)"><th style="text-align:left;padding:6px 8px">Opted in on Discord</th><th style="text-align:left;padding:6px 8px">In-game name</th></tr></thead><tbody>${rows}</tbody></table></div>` : st.optin_message_id ? `<p style="font-size:13px">Nobody has reacted ✅ yet.</p>` : ""}
      <p style="margin:8px 0 0;font-size:12.5px">${opt.length} opted in · updated every 15 minutes.</p>`;
    form({ title: `Discord DMs · ${g.name}`, wide: true, html, button: "Save links",
      run: async ({ getJSONFile: gj, putFile }) => {
        const cur = await gj(`guilds/${g.slug}/discord-links.json`), links = { ...((cur.data && cur.data.links) || {}) };
        document.querySelectorAll("#offDlg select[data-uid]").forEach(s => { const uid = s.dataset.uid, a = auto[uid] || {};
          if (s.value === (a.sure ? a.player : "") && !(uid in links)) return;   // unchanged from a sure automatic match
          links[uid] = s.value; });
        await putFile(`guilds/${g.slug}/discord-links.json`, JSON.stringify({ links }, null, 1), `Link ${g.name} Discord DMs to in-game names`, cur.sha);
      },
      done: "📬 Saved. DMs use these links from the next phase." });
  }

  window.Officer = { post, postButton, requestPost, form, setToken: t => { TOKEN = t; }, authToken: async () => TOKEN || await remembered(), webhooks, discordDms };
})();
