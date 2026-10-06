#!/usr/bin/env python3
"""
Posts a raid summary to each guild's own Discord channel.

    python scripts/post_discord.py oanr/order-66 endor-legacy/order-66   # a specific raid
    python scripts/post_discord.py oanr endor-legacy                     # each guild's latest raid

Each guild's webhook comes from the GitHub secret named in its config.yml (discord_secret),
default DISCORD_WEBHOOK_<FOLDER NAME IN CAPITALS>, e.g. DISCORD_WEBHOOK_OANR.
The Action passes all secrets in SECRETS_JSON. SITE_URL (optional) adds a link to the dashboard.
"""
import json
import os
import re
import sys
import urllib.request
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
    body = json.dumps({"username": "Raid Tracker", "embeds": [embed]}).encode()
    req = urllib.request.Request(hook, data=body, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "swgoh-guild-raids (github actions)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        print(f"{slug}/{raid}: posted to Discord (HTTP {r.status})")


if __name__ == "__main__":
    sys.exit(main())
