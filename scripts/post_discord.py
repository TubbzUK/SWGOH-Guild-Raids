#!/usr/bin/env python3
"""
Posts a raid summary to each guild's own Discord channel.

    python scripts/post_discord.py oanr/order-66 endor-legacy/order-66   # a specific raid
    python scripts/post_discord.py oanr endor-legacy                     # each guild's latest raid

Each guild's webhook comes from the GitHub secret named in its config.yml (discord_secret),
default DISCORD_WEBHOOK_<FOLDER NAME IN CAPITALS>, e.g. DISCORD_WEBHOOK_OANR.
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


def webhook_for(slug: str) -> tuple[str, str]:
    cfg_file = ROOT / "guilds" / slug / "config.yml"
    cfg = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {} if cfg_file.exists() else {}
    name = cfg.get("discord_secret") or "DISCORD_WEBHOOK_" + re.sub(r"[^A-Z0-9]", "_", slug.upper())
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
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright isn't installed - posting the text summary only")
        return None
    port = _serve_site()
    url = f"http://127.0.0.1:{port}/card.html?" + urllib.parse.urlencode({"guild": slug, "raid": raid, "site": site})
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
            page = browser.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=2, color_scheme="dark")
            page.goto(url, wait_until="networkidle", timeout=45000)
            page.wait_for_selector("body[data-ready]", timeout=30000)
            err = page.evaluate("document.body.dataset.error || ''")
            if err:
                print(f"{slug}/{raid}: results panel didn't draw ({err}) - posting the text summary only")
                browser.close()
                return None
            png = page.locator("#card").screenshot(type="png")
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
    slugs = sys.argv[1:]
    if not slugs:
        print("No guilds to post for")
        return 0
    try:
        index = {g["slug"]: g for g in json.loads((ROOT / "site" / "guilds.json").read_text(encoding="utf-8"))}
    except (OSError, json.JSONDecodeError):
        index = {}
    for arg in slugs:
        slug, _, raid = arg.partition("/")
        raid = raid or (index.get(slug) or {}).get("default_raid")
        if not raid:
            print(f"{slug}: no raid results yet - nothing to post")
            continue
        secret, hook = webhook_for(slug)
        if not hook:
            print(f"{slug}: no GitHub secret called {secret} - skipping Discord post")
            continue
        try:
            post_guild(slug, raid, hook)
        except Exception as e:  # one guild failing shouldn't stop the others
            print(f"::warning::{slug}/{raid}: Discord post failed: {e}")
    return 0


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
