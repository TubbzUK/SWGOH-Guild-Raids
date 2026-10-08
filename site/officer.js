/* Officer actions shared by the pages: unlock with the officer password (same one as the upload page)
   and ask GitHub to post a results panel to Discord.

   Officer.postButton(button, () => ({ guild, kind, label, ...extra }))
     kind: "raid" (with raid), "tb" (with tb), "effectiveness", "platoons" (with phase, text)
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
  .off-dlg p { font-size: 13.5px; color: var(--text-2); margin: 0 0 12px; }
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
    d.innerHTML = `<form method="dialog" id="offForm"><h2 id="offTitle">Post to Discord</h2><p id="offText"></p>
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
  }

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
    $("#offTitle").textContent = "Post to Discord";
    $("#offText").innerHTML = `Post <b>${esc(req.label)}</b> to the guild's ${req.kind === "platoons" ? "platoons" : req.kind === "effectiveness" ? "officers'" : "Discord"} channel? It appears about 3 minutes from now, once the site has updated.`
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

  function postButton(btn, getReq) {
    if (!btn) return;
    btn.addEventListener("click", () => { const r = getReq(); if (r) post(r); });
  }

  window.Officer = { post, postButton, requestPost, setToken: t => { TOKEN = t; } };
})();
