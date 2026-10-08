#!/usr/bin/env python3
"""
Posts results panels to each guild's own Discord channels.

    python scripts/post_discord.py oanr/order-66 endor-legacy/order-66   # a specific raid
    python scripts/post_discord.py oanr endor-legacy                     # each guild's latest raid

It also posts whatever officers asked for with the site's "Post to Discord" buttons: the requests are
collected by organize.py into .post-queue.json (raid, tb, effectiveness or platoons).

Webhooks come from GitHub secrets. Raids, TBs and effectiveness go to the guild's main channel:
discord_secret in its config.yml, default DISCORD_WEBHOOK_<FOLDER NAME IN CAPITALS> (DISCORD_WEBHOOK_OANR).
Platoons go to their own channel: discord_platoons_secret, default DISCORD_WEBHOOK_<FOLDER>_PLATOONS.
Effectiveness goes to the officers' channel: discord_officer_secret, default OFFICER_<FOLDER> (e.g. OFFICER_OANR),
or the main channel if that secret doesn't exist.
The Action passes all secrets in SECRETS_JSON. SITE_URL (optional) adds a link to the dashboard.

The post includes a picture of the results panel (site/card.html), taken with Playwright using the
Chrome that GitHub's runners already have. If that can't be done, it posts the text summary instead.
"""
import functools
import http.server
import json
import os
import re
import sys
import threading
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def fmt(n):
    if n is None:
        return "-"
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(n) >= div:
            return f"{n / div:.2f}{suf}" if suf != "K" else f"{n / div:.1f}{suf}"
    return f"{n:.0f}"


def clip(text, limit=1024):
    return text if len(text) <= limit else text[: limit - 2] + " …"


def webhook_for(slug: str, channel: str = "main") -> tuple[str, str]:
    cfg_file = ROOT / "guilds" / slug / "config.yml"
    cfg = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {} if cfg_file.exists() else {}
    base = "DISCORD_WEBHOOK_" + re.sub(r"[^A-Z0-9]", "_", slug.upper())
    try:
        secrets = json.loads(os.getenv("SECRETS_JSON") or "{}")
    except json.JSONDecodeError:
        secrets = {}
    if channel == "platoons":
        name = cfg.get("discord_platoons_secret") or base + "_PLATOONS"
    elif channel == "officers":
        # officers' channel: discord_officer_secret, else OFFICER_<GUILD> if it exists, else the main channel
        officer = cfg.get("discord_officer_secret") or "OFFICER_" + re.sub(r"[^A-Z0-9]", "_", slug.upper())
        name = officer if (secrets.get(officer) or os.getenv(officer) or cfg.get("discord_officer_secret")) else (cfg.get("discord_secret") or base)
    else:
        name = cfg.get("discord_secret") or base
    try:
        secrets = json.loads(os.getenv("SECRETS_JSON") or "{}")
    except json.JSONDecodeError:
        secrets = {}
    return name, (secrets.get(name) or os.getenv(name) or "").strip()


# ---------- results panel picture ----------
_server = None


def _serve_site() -> int:
    """Serve site/ on a free local port (once) so card.html can load the built data."""
    global _server
    if _server is None:
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a):
                pass
        handler = functools.partial(Quiet, directory=str(ROOT / "site"))
        _server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=_server.serve_forever, daemon=True).start()
    return _server.server_address[1]


def render_card(slug: str, raid: str, site: str) -> bytes | None:
    return render_page("card.html", {"guild": slug, "raid": raid, "site": site}, "#card")


def render_page(page_name: str, query: dict, selector: str | None = None) -> list[bytes]:
    """Photograph a page (?card=1) once it says it's ready: the whole page, cut between sections into
    pictures of up to about 1,600px tall so Discord shows them readably. Returns [] if it can't."""
    slug, what = query.get("guild", ""), query.get("raid") or page_name
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright isn't installed - posting the text summary only")
        return []
    port = _serve_site()
    url = f"http://127.0.0.1:{port}/{page_name}?" + urllib.parse.urlencode(query)
    try:
        with sync_playwright() as p:
            browser = None
            for opts in ({"channel": "chrome"}, {}):   # GitHub's runners have Chrome; otherwise Playwright's own
                try:
                    browser = p.chromium.launch(**opts)
                    break
                except Exception:
                    continue
            if browser is None:
                print("No browser available - posting the text summary only")
                return []
            page = browser.new_page(viewport={"width": 1100, "height": 600}, device_scale_factor=1.5, color_scheme="dark")
            page.goto(url, wait_until="networkidle", timeout=90000)
            page.wait_for_selector("body[data-ready]", state="attached", timeout=60000)
            err = page.evaluate("document.body.dataset.error || ''")
            if err:
                print(f"{slug}/{what}: the page didn't draw ({err}) - posting the text summary only")
                browser.close()
                return []
            if selector:
                shots = [page.locator(selector).screenshot(type="png")]
                browser.close()
                return shots
            width = int(page.evaluate("+document.body.dataset.cardw || document.documentElement.scrollWidth"))
            page.set_viewport_size({"width": width, "height": 600})
            page.wait_for_timeout(800)
            # the page's blocks, top to bottom (each card section split into its own pieces)
            blocks = page.evaluate("""(limit) => {
                const out = [], y = window.scrollY;
                const visible = el => el.offsetParent || getComputedStyle(el).position === 'fixed';
                const box = el => { const r = el.getBoundingClientRect(); return [r.top + y, r.bottom + y, r.height]; };
                // break tall things into smaller pieces we can cut between: table rows, cards, list items
                const collect = el => {
                    if (!visible(el)) return;
                    const [t, b, h] = box(el);
                    if (h <= 2) return;
                    if (h <= limit) { out.push([t, b]); return; }
                    if (el.tagName === 'TABLE') {
                        const head = el.tHead ? box(el.tHead) : null;
                        const rows = [...el.rows].filter(r => !el.tHead || r.parentNode !== el.tHead);
                        if (head) out.push([t, head[1]]);
                        rows.forEach(r => { const [rt, rb] = box(r); out.push([rt, rb]); });
                        return;
                    }
                    const kids = [...el.children].filter(visible);
                    if (!kids.length) { out.push([t, b]); return; }
                    out.push([t, Math.min(...kids.map(k => box(k)[0]))]);   // padding / heading above the children
                    kids.forEach(collect);
                    out.push([Math.max(...kids.map(k => box(k)[1])), b]);   // padding below
                };
                document.querySelectorAll('.wrap, main').forEach(root => [...root.children].forEach(collect));
                document.querySelectorAll('.cardfoot').forEach(collect);
                return out.filter(([t, b]) => b - t > 0.5).sort((a, b) => a[0] - b[0] || a[1] - b[1]);
            }""", 1500)
            total = page.evaluate("document.documentElement.scrollHeight")
            # cut only where nothing spans the cut, and never leave a sliver on its own
            chunks, start, end, limit = [], 0, 0, 1500
            for top, bottom in blocks:
                if end and top >= end - 1 and bottom - start > limit and end - start > 300:
                    chunks.append((start, end))
                    start = end
                end = max(end, bottom)
            if chunks and end - start < 220:          # fold a short tail (the footer) into the last picture
                start = chunks.pop()[0]
            chunks.append((start, min(total, end + 18)))
            shots = []
            for a, b in chunks:
                if b - a < 8:
                    continue
                shots.append(page.screenshot(type="png", full_page=True,
                                             clip={"x": 0, "y": max(0, a - 6), "width": width, "height": b - max(0, a - 6)}))
            browser.close()
            return shots
    except Exception as e:
        print(f"{slug}/{what}: couldn't take the pictures ({e}) - posting the text summary only")
        return []


def send(hook: str, payload: dict, png, filename: str = "") -> int:
    """Post JSON, or multipart with pictures attached: png is one picture (bytes) or a list of
    (filename, bytes)."""
    headers = {"User-Agent": "swgoh-guild-raids (github actions)"}
    files = [] if png is None else ([(filename, png)] if isinstance(png, (bytes, bytearray)) else list(png))
    if not files:
        body, headers["Content-Type"] = json.dumps(payload).encode(), "application/json"
    else:
        b = uuid.uuid4().hex
        parts = [f"--{b}\r\nContent-Disposition: form-data; name=\"payload_json\"\r\nContent-Type: application/json\r\n\r\n".encode()
                 + json.dumps(payload).encode() + b"\r\n"]
        for n, (fname, data) in enumerate(files):
            parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"files[{n}]\"; filename=\"{fname}\"\r\nContent-Type: image/png\r\n\r\n".encode()
                         + data + b"\r\n")
        parts.append(f"--{b}--\r\n".encode())
        body, headers["Content-Type"] = b"".join(parts), f"multipart/form-data; boundary={b}"
    req = urllib.request.Request(hook, data=body, method="POST", headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status


def send_pictures(hook: str, embed: dict, shots: list[bytes], stem: str) -> int:
    """The first embed carries the title and link; each picture gets its own embed below it.
    Discord allows 10 pictures and about 10 MB per message, so long pages go out in several messages."""
    import time
    batches, cur, size = [], [], 0
    for n, png in enumerate(shots, 1):
        if cur and (len(cur) == 10 or size + len(png) > 9_000_000):
            batches.append(cur); cur, size = [], 0
        cur.append((f"{stem}-{n}.png", png)); size += len(png)
    if cur:
        batches.append(cur)
    status = 0
    for k, batch in enumerate(batches):
        embeds = []
        for m, (fname, _) in enumerate(batch):
            e = dict(embed) if (k == 0 and m == 0) else {"color": embed.get("color", 0x2A78D6)}
            if k == 0 and m == 0:
                e.pop("fields", None)
            e["image"] = {"url": f"attachment://{fname}"}
            embeds.append(e)
        if k:
            time.sleep(1)
        status = send(hook, {"username": "Guild Statistics", "embeds": embeds}, batch)
    return status

def main():
    items = []
    try:
        index = {g["slug"]: g for g in json.loads((ROOT / "site" / "guilds.json").read_text(encoding="utf-8"))}
    except (OSError, json.JSONDecodeError):
        index = {}
    for arg in sys.argv[1:]:
        if arg == "queue":
            continue
        slug, _, raid = arg.partition("/")
        items.append({"guild": slug, "kind": "raid", "raid": raid or (index.get(slug) or {}).get("default_raid")})
    queue_file = ROOT / ".post-queue.json"
    if queue_file.exists():
        try:
            items += json.loads(queue_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"::warning::Couldn't read the post queue: {e}")
        queue_file.unlink()
    if not items:
        print("Nothing to post to Discord")
        return 0
    for it in items:
        slug, kind = it.get("guild"), it.get("kind")
        if not slug or not (ROOT / "guilds" / slug).is_dir():
            print(f"::warning::Post request for an unknown guild ({slug}) - skipped")
            continue
        channel = {"platoons": "platoons", "effectiveness": "officers"}.get(kind, "main")
        secret, hook = webhook_for(slug, channel)
        if not hook:
            print(f"::warning::{slug}: no GitHub secret called {secret} - can't post the {kind} panel. "
                  f"Add it under Settings > Secrets and variables > Actions.")
            continue
        try:
            if kind == "raid":
                if not it.get("raid"):
                    print(f"{slug}: no raid results yet - nothing to post")
                    continue
                post_guild(slug, it["raid"], hook)
            elif kind == "tb":
                post_tb(slug, it.get("tb"), hook)
            elif kind == "tw":
                post_tw(slug, it.get("tw"), hook)
            elif kind == "effectiveness":
                post_effectiveness(slug, hook)
            elif kind == "platoons":
                post_platoons(slug, it, hook)
            else:
                print(f"::warning::{slug}: unknown post type {kind!r} - skipped")
        except Exception as e:  # one post failing shouldn't stop the others
            print(f"::warning::{slug}/{kind}: Discord post failed: {e}")
    return 0


def site_link(path: str) -> str:
    site = os.getenv("SITE_URL", "").strip()
    return site.rstrip("/") + "/" + path if site else ""


def guild_name(slug: str) -> str:
    try:
        return next(g["name"] for g in json.loads((ROOT / "site" / "guilds.json").read_text(encoding="utf-8")) if g["slug"] == slug)
    except Exception:
        return slug


def post_panel(hook, slug, kind, title, description, link, png, fallback_fields=None, footer=None):
    embed = {"title": title, "description": description + (f"\n[Open on the site]({link})" if link else ""), "color": 0x2A78D6}
    if link:
        embed["url"] = link
    if footer:
        embed["footer"] = {"text": footer}
    if png:
        status = send_pictures(hook, embed, png, f"{slug}-{kind}")
    else:
        if fallback_fields:
            embed["fields"] = fallback_fields
        status = send(hook, {"username": "Guild Statistics", "embeds": [embed]}, None)
    print(f"{slug}/{kind}: posted to Discord{f' with {len(png)} picture(s)' if png else ''} (HTTP {status})")


def post_tb(slug, tb_id, hook):
    d = json.loads((ROOT / "site" / "data" / slug / "tb.json").read_text(encoding="utf-8"))
    tbs = d["tbs"]
    t = next((x for x in tbs if x["id"] == tb_id), tbs[-1])
    i = tbs.index(t)
    prev = tbs[i - 1] if i else None
    link = site_link(f"tb.html?guild={slug}&tb={t['id']}")
    png = render_page("tb.html", {"guild": slug, "tb": t["id"], "card": "1", "site": link})
    st = d.get("status") or {}
    fields = [
        {"name": "Territory points", "value": fmt(t["tp"]) + (f" ({(t['tp'] - prev['tp']) / prev['tp'] * 100:+.1f}% vs last TB)" if prev and prev["tp"] else ""), "inline": True},
        {"name": "Wave completion", "value": f"{t['wave_pct']:.0f}%", "inline": True},
        {"name": "Fully deployed", "value": f"{t['all_deployed']}/{t['members']}", "inline": True},
    ]
    if i == len(tbs) - 1 and st:
        fields.append({"name": "Participation", "value": f"✓ {st.get('active', 0)} active · ● {st.get('partial', 0)} partial · ○ {st.get('inactive', 0)} inactive", "inline": False})
    post_panel(hook, slug, "tb", f"{guild_name(slug)} · Territory battle results", f"{t['label']} of {t['date']}", link, png, fields,
               f"{len(tbs)} territory battles tracked")


def post_tw(slug, tw_id, hook):
    d = json.loads((ROOT / "site" / "data" / slug / "tw.json").read_text(encoding="utf-8"))
    tws = d["tws"]
    t = next((x for x in tws if x["id"] == tw_id), tws[-1])
    link = site_link(f"tw.html?guild={slug}&tw={t['id']}")
    shots = render_page("tw.html", {"guild": slug, "tw": t["id"], "card": "1", "site": link})
    res = {"win": "🏆 Won", "loss": "Lost", "draw": "Draw"}.get(t.get("result") or "", "Result not recorded yet")
    score = f" {t['our_score']:,} – {t['their_score']:,}" if t.get("our_score") is not None and t.get("their_score") is not None else ""
    fields = [
        {"name": "Result", "value": res + score, "inline": True},
        {"name": "Joined", "value": f"{t['joined']}" + (f"/{t['members']}" if t.get("members") else ""), "inline": True},
        {"name": "Banners", "value": f"{t['total']:,.0f} (defence {t['defense']:,.0f} · offence {t['offense']:,.0f})", "inline": False},
    ]
    if t.get("not_joined"):
        fields.append({"name": f"Didn't join ({len(t['not_joined'])})", "value": clip(", ".join(t["not_joined"])), "inline": False})
    post_panel(hook, slug, "tw", f"{guild_name(slug)} · Territory war" + (f" vs {t['opponent']}" if t.get("opponent") else ""),
               f"{res}{score} · {t['date']}", link, shots, fields, f"{len(tws)} territory wars tracked")


def post_effectiveness(slug, hook):
    link = site_link(f"effectiveness.html?guild={slug}")
    png = render_page("effectiveness.html", {"guild": slug, "card": "1", "site": link})
    post_panel(hook, slug, "effectiveness", f"{guild_name(slug)} · Guild effectiveness",
               "Raid scores and territory battle contribution combined.", link, png,
               [{"name": "Panel", "value": "The picture couldn't be made this time - open the page for the full ranking.", "inline": False}])


def post_platoons(slug, it, hook):
    phase = int(it.get("phase") or 1)
    who = it.get("who") or ""
    link = site_link(f"platoons.html?guild={slug}")
    q = {"guild": slug, "phase": str(phase), "card": "1", "site": link}
    if who:
        q["who"] = who
    shots = render_page("platoons.html", q)
    post_panel(hook, slug, f"platoons-p{phase}", f"{guild_name(slug)} · RotE phase {phase} platoons" + (f" · {who}" if who else ""),
               "Who places what this phase.", link, shots,
               [{"name": "Assignments", "value": "The pictures couldn't be made this time - open the planner for this phase's lists.", "inline": False}])

def post_guild(slug, raid, hook):
    data = json.loads((ROOT / "site" / "data" / slug / f"{raid}.json").read_text(encoding="utf-8"))
    raids = data["raids"]
    if not raids:
        print(f"{slug}/{raid}: no raid results - nothing to post")
        return
    latest = raids[-1]
    prev = raids[-2] if len(raids) > 1 else None
    players = [p for p in data["players"] if p["last"] and p["current"]]
    site = os.getenv("SITE_URL", "").strip()
    if site:
        site = site.rstrip("/") + f"/?guild={slug}&raid={raid}"

    total_line = f"**{fmt(latest['total'])}**"
    if prev and prev["total"]:
        pct = (latest["total"] - prev["total"]) / prev["total"] * 100
        arrow = "🔺" if pct > 0 else "🔻" if pct < 0 else "➖"
        total_line += f"  {arrow} {pct:+.1f}% vs last raid"

    medals = ["🥇", "🥈", "🥉"]
    top = sorted(players, key=lambda p: -p["last"])[:5]
    top_txt = "\n".join(f"{medals[i] if i < 3 else f'`{i + 1}.`'} {p['name']} — {fmt(p['last'])}"
                        for i, p in enumerate(top))

    current = [p for p in data["players"] if p["current"]]
    improvers = sorted((p for p in current if p.get("delta_pct") and p["delta_pct"] > 0),
                       key=lambda p: -p["delta_pct"])[:3]
    imp_txt = "\n".join(f"📈 {p['name']} +{p['delta_pct']:.1f}%" for p in improvers) or "—"
    declining = sorted((p for p in current if p.get("trend") == "declining"), key=lambda p: p["trend_pct"])
    dec_txt = ", ".join(f"{p['name']} ({p['trend_pct']:+.0f}%/raid)" for p in declining)

    no_score = latest.get("no_score") or []
    target = data.get("target_score")
    fields = [
        {"name": "Guild total", "value": total_line, "inline": False},
        {"name": "Participation", "value": f"{latest['participants']}/{latest['members']}", "inline": True},
        {"name": "Average", "value": fmt(latest["average"]), "inline": True},
    ]
    if target:
        fields.append({"name": f"Below {fmt(target)}", "value": str(latest["below_target"]), "inline": True})
    ts = data.get("trend_summary") or {}
    if ts:
        fields.append({"name": "Trend",
                       "value": f"▲ {ts.get('improving', 0)} improving · ■ {ts.get('level', 0)} level · "
                                f"▼ {ts.get('declining', 0)} declining", "inline": False})
    fields += [
        {"name": "Top 5", "value": clip(top_txt or "—"), "inline": True},
        {"name": "Biggest jumps vs last raid", "value": clip(imp_txt), "inline": True},
    ]
    if dec_txt:
        fields.append({"name": "Declining – watch list", "value": clip(dec_txt), "inline": False})
    if no_score:
        fields.append({"name": f"No score ({len(no_score)})", "value": clip(", ".join(no_score)), "inline": False})
    rs = data.get("readiness_summary")
    if rs:
        fields.append({"name": "Raid readiness",
                       "value": f"{rs['average']:.0f}% guild average · {rs['status']['ready']} ready", "inline": False})

    embed = {
        "title": f"{data['guild_name']} · {data.get('raid_name') or 'raid'} results",
        "description": f"Raid of {latest['date']}" + (f"\n[Open the full dashboard]({site})" if site else ""),
        "color": 0x2A78D6,
        "fields": fields,
        "footer": {"text": f"{len(raids)} raids tracked"},
    }
    if site:
        embed["url"] = site
    # the whole raid page (overview, players, readiness) as pictures; the text summary if that can't be done
    shots = render_page("index.html", {"guild": slug, "raid": raid, "card": "1", "site": site})
    if shots:
        status = send_pictures(hook, embed, shots, f"{slug}-{raid}-{latest['date']}")
    else:
        status = send(hook, {"username": "Guild Statistics", "embeds": [embed]}, None)
    print(f"{slug}/{raid}: posted to Discord{f' with {len(shots)} picture(s)' if shots else ''} (HTTP {status})")


if __name__ == "__main__":
    sys.exit(main())
