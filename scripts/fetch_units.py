#!/usr/bin/env python3
"""
Unit names, portraits, ship/character and light/dark side from swgoh.gg's public unit lists
(https://swgoh.gg/api/characters/ and /api/ships/), saved to scripts/units.json for the build.

The portraits themselves aren't copied: the site shows them straight from swgoh.gg's image server
(game-assets.swgoh.gg). If swgoh.gg can't be reached the old units.json is kept, and without one the
site simply shows no portraits.

    python scripts/fetch_units.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent / "units.json"
LISTS = {"characters": "https://swgoh.gg/api/characters/", "ships": "https://swgoh.gg/api/ships/"}
IMG_BASE = "https://game-assets.swgoh.gg/"


def get(url: str):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; GuildStatistics/1.0; guild site for SWGoH)",
        "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def side(v) -> str:
    s = str(v or "").lower()
    return "L" if "light" in s else "D" if "dark" in s else "N" if "neutral" in s else ""


def main() -> int:
    units: dict[str, dict] = {}
    for kind, url in LISTS.items():
        try:
            data = get(url)
        except Exception as e:  # network, Cloudflare, JSON
            print(f"::warning::Couldn't load the {kind} list from swgoh.gg ({e}) - keeping the saved unit list")
            return 0
        items = data.get("data") if isinstance(data, dict) else data
        for u in items or []:
            bid = str(u.get("base_id") or "").upper()
            if not bid:
                continue
            img = str(u.get("image") or "")
            if img.startswith(IMG_BASE):
                img = img[len(IMG_BASE):]           # store the short path; the site adds the server
            entry = {"name": u.get("name") or bid, "img": img}
            if kind == "ships" or str(u.get("combat_type")) == "2":
                entry["ship"] = True
            sd = side(u.get("alignment"))
            if sd:
                entry["side"] = sd
            units[bid] = entry
    if len(units) < 100:
        print(f"::warning::swgoh.gg returned only {len(units)} units - keeping the saved unit list")
        return 0
    new = json.dumps(dict(sorted(units.items())), indent=0, ensure_ascii=False)
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != new:
        OUT.write_text(new, encoding="utf-8")
        print(f"Unit list updated: {len(units)} units")
    else:
        print(f"Unit list unchanged ({len(units)} units)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
