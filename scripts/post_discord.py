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


def render_page(page_name: str, query: dict, selector: str | None = None) -> bytes | None:
    """Photograph a page (card.html, or another page with ?card=1) once it says it's ready."""
    slug, raid = query.get("guild", ""), query.get("raid") or query.get("kind", "")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright isn't installed - posting the text summary only")
        return None
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
                return None
            page = browser.new_page(viewport={"width": 1100, "height": 900 if selector else 300}, device_scale_factor=2, color_scheme="dark")
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_selector("body[data-ready]", state="attached", timeout=40000)
            err = page.evaluate("document.body.dataset.error || ''")
            if err:
                print(f"{slug}/{raid}: results panel didn't draw ({err}) - posting the text summary only")
                browser.close()
                return None
            png = page.locator(selector).screenshot(type="png") if selector else page.screenshot(type="png", full_page=True)
            browser.close()
            return png
    except Exception as e:
        print(f"{slug}/{raid}: couldn't take the results panel picture ({e}) - posting the text summary only")
        return None


def send(hook: str, payload: dict, png: bytes | None, filename: str) -> int:
    """Post JSON, or multipart with the picture attached when there is one."""
    headers = {"User-Agent": "swgoh-guild-raids (github actions)"}
    if png is None:
        body, headers["Content-Type"] = json.dumps(payload).encode(), "application/json"
    else:
        b = uuid.uuid4().hex
        parts = [
            f"--{b}\r\nContent-Disposition: form-data; name=\"payload_json\"\r\nContent-Type: application/json\r\n\r\n".encode()
            + json.dumps(payload).encode() + b"\r\n",
            f"--{b}\r\nContent-Disposition: form-data; name=\"files[0]\"; filename=\"{filename}\"\r\nContent-Type: image/png\r\n\r\n".encode()
            + png + b"\r\n",
            f"--{b}--\r\n".encode(),
        ]
        body, headers["Content-Type"] = b"".join(parts), f"multipart/form-data; boundary={b}"
    req = urllib.request.Request(hook, data=body, method="POST", headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status


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
    fname = ""
    if png:
        fname = f"{slug}-{kind}.png"
        embed["image"] = {"url": f"attachment://{fname}"}
    elif fallback_fields:
        embed["fields"] = fallback_fields
    status = send(hook, {"username": "Guild Statistics", "embeds": [embed]}, png, fname)
    print(f"{slug}/{kind}: posted to Discord{' with the panel' if png else ''} (HTTP {status})")


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


def post_effectiveness(slug, hook):
    link = site_link(f"effectiveness.html?guild={slug}")
    png = render_page("effectiveness.html", {"guild": slug, "card": "1", "site": link})
    post_panel(hook, slug, "effectiveness", f"{guild_name(slug)} · Guild effectiveness",
               "Raid scores and territory battle contribution combined.", link, png,
               [{"name": "Panel", "value": "The picture couldn't be made this time - open the page for the full ranking.", "inline": False}])


def post_platoons(slug, it, hook):
    phase = int(it.get("phase") or 1)
    link = site_link(f"platoons.html?guild={slug}")
    png = render_page("platoons.html", {"guild": slug, "phase": str(phase), "card": "1", "site": link})
    who = it.get("who") or ""
    post_panel(hook, slug, f"platoons-p{phase}", f"{guild_name(slug)} · RotE phase {phase} platoons" + (f" · {who}" if who else ""),
               "Who places what this phase. Lists follow below.", link, png)
    # the member lists, split into Discord-sized messages at member boundaries
    text = (it.get("text") or "").strip()
    chunks, cur = [], ""
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        while len(block) > 1900:            # a single very long block: hard split on lines
            cut = block.rfind("\n", 0, 1900)
            cut = cut if cut > 0 else 1900
            chunks.append(block[:cut]); block = block[cut:].lstrip("\n")
        if len(cur) + len(block) + 2 > 1900:
            chunks.append(cur); cur = block
        else:
            cur = (cur + "\n\n" + block) if cur else block
    if cur:
        chunks.append(cur)
    import time
    for n, c in enumerate(chunks):
        time.sleep(0.8)
        send(hook, {"username": "Guild Statistics", "content": c, "allowed_mentions": {"parse": []}}, None, "")
    print(f"{slug}/platoons: posted phase {phase} lists in {len(chunks)} message(s)")


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
    png = render_card(slug, raid, site)
    if png:
        # with the panel picture the embed stays short: title, link and the picture itself
        fname = f"{slug}-{raid}-{latest['date']}.png"
        embed = {"title": embed["title"], "description": embed["description"], "color": embed["color"],
                 "image": {"url": f"attachment://{fname}"}, "footer": embed["footer"], **({"url": site} if site else {})}
    else:
        fname = ""
    status = send(hook, {"username": "Guild Statistics", "embeds": [embed]}, png, fname)
    print(f"{slug}/{raid}: posted to Discord{' with the results panel' if png else ''} (HTTP {status})")


if __name__ == "__main__":
    sys.exit(main())
