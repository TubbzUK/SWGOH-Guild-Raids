#!/usr/bin/env python3
"""
Unit names, portrait names, ship/character and light/dark side for every playable unit, read from the
game itself through SWGoH Comlink (the same container the game pull uses), saved to scripts/units.json.

The portraits are shown on the site straight from swgoh.gg's image server
(https://game-assets.swgoh.gg/textures/<portrait>.png) - nothing is copied into the repository.

It only downloads the game data when needed: no units.json yet, the list is over a week old, or a
roster has a unit the list doesn't know. Keeps the old list if anything goes wrong.

    python scripts/fetch_units.py            # Comlink at COMLINK_URL (default http://localhost:3000)
    python scripts/fetch_units.py --force
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "units.json"
COMLINK = os.getenv("COMLINK_URL", "http://localhost:3000").rstrip("/")
UNITS_ITEM = "137438953472"          # the game data 'units' collection
SIDES = {"1": "N", "2": "L", "3": "D"}


def post(endpoint: str, body: dict, timeout: int = 300):
    req = urllib.request.Request(f"{COMLINK}/{endpoint}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def wait_ready(seconds: int = 150) -> dict | None:
    end = time.time() + seconds
    while time.time() < end:
        try:
            return post("metadata", {}, timeout=20)
        except Exception:
            time.sleep(4)
    return None


def roster_ids() -> set[str]:
    ids = set()
    for f in (ROOT / "guilds").glob("*/roster/*.csv"):
        try:
            with open(f, encoding="utf-8-sig", newline="") as fh:
                for r in csv.DictReader(fh):
                    if r.get("BaseId"):
                        ids.add(r["BaseId"].strip().upper())
        except OSError:
            pass
    return ids


def needed(force: bool) -> str | None:
    if force or not OUT.exists():
        return "no unit list yet" if not OUT.exists() else "forced"
    try:
        cur = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "the saved list couldn't be read"
    when = cur.get("_fetched")
    if not when or (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(when)).days >= 7:
        return "the list is over a week old"
    missing = roster_ids() - set(cur)
    if missing:
        return f"{len(missing)} unit(s) in a roster aren't in the list (e.g. {sorted(missing)[0]})"
    return None


def main() -> int:
    why = needed("--force" in sys.argv)
    if not why:
        print("Unit list is up to date")
        return 0
    print(f"Fetching the unit list from the game: {why}")
    meta = wait_ready()
    if not meta:
        print("::warning::Comlink didn't start, so the unit list (names and pictures) wasn't updated")
        return 0
    try:
        data = post("data", {"payload": {"version": meta["latestGamedataVersion"], "includePveUnits": False,
                                         "devicePlatform": "Android", "items": UNITS_ITEM}, "enums": False})
        loc = post("localization", {"unzip": True, "enums": False,
                                    "payload": {"id": meta["latestLocalizationBundleVersion"] + ":ENG_US"}})
    except Exception as e:
        print(f"::warning::Couldn't read the unit list from the game ({e}) - keeping the saved one")
        return 0
    text = next((v for k, v in (loc or {}).items() if isinstance(v, str) and "|" in v), "")
    names = {}
    for line in text.splitlines():
        if line.startswith("UNIT_") and "|" in line:
            k, v = line.split("|", 1)
            names[k] = v.strip()
    units: dict[str, dict] = {}
    for u in data.get("units") or []:
        bid = str(u.get("baseId") or "").upper()
        if not bid or str(u.get("obtainableTime") or "0") != "0" or u.get("obtainable") is False:
            continue
        if bid in units and str(u.get("rarity")) not in ("7", "SEVEN_STAR"):
            continue
        name = names.get(u.get("nameKey") or "", "") or bid.title()
        entry = {"name": name}
        thumb = u.get("thumbnailName")
        if thumb:
            entry["img"] = f"textures/{thumb}.png"
        if str(u.get("combatType")) in ("2", "SHIP"):
            entry["ship"] = True
        side = SIDES.get(str(u.get("forceAlignment")))
        if side:
            entry["side"] = side
        units[bid] = entry
    if len(units) < 100:
        print(f"::warning::The game returned only {len(units)} units - keeping the saved list")
        return 0
    out = {"_fetched": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), **dict(sorted(units.items()))}
    OUT.write_text(json.dumps(out, indent=0, ensure_ascii=False), encoding="utf-8")
    print(f"Unit list saved: {len(units)} units, {sum('img' in v for v in units.values())} with pictures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
