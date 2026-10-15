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
SKILLS_OUT = Path(__file__).resolve().parent / "skills.json"   # abilities that can take a zeta or an omicron
COMLINK = os.getenv("COMLINK_URL", "http://localhost:3000").rstrip("/")
UNITS_ITEM = str(137438953472 + 4 + 2097152)   # game data collections: units + skills + abilities
OMICRON_MODES = {4: "Raid", 7: "TB", 8: "TW", 9: "GAC", 11: "Conquest", 12: "Galactic Challenge", 14: "GAC 3v3", 15: "GAC 5v5"}
KINDS = {"basicskill": "Basic", "specialskill": "Special", "uniqueskill": "Unique", "leaderskill": "Leader",
         "hardwareskill": "Hardware", "contractskill": "Contract"}
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
    if force or not OUT.exists() or not SKILLS_OUT.exists():
        return "forced" if force else "no unit list yet"
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
        if "|" in line and not line.startswith("#"):
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
    # abilities with a zeta or omicron tier, and which unit each belongs to
    abil = {a.get("id"): a for a in data.get("ability") or []}
    owner = {}
    for u in data.get("units") or []:
        bid = str(u.get("baseId") or "").upper()
        if bid not in units:
            continue
        refs = list(u.get("skillReference") or []) + [r for c in u.get("crew") or [] for r in c.get("skillReference") or []]
        for r in refs:
            owner.setdefault(r.get("skillId"), bid)
    skills = {}
    for sk in data.get("skill") or []:
        sid, tiers = sk.get("id"), sk.get("tier") or []
        if sid not in owner:
            continue
        z = next((i for i, t in enumerate(tiers) if t.get("isZetaTier")), None)
        o = next((i for i, t in enumerate(tiers) if t.get("isOmicronTier")), None)
        if z is None and o is None:
            continue
        a = abil.get(sk.get("abilityReference")) or {}
        nm = names.get(a.get("nameKey") or "", "") or names.get(sk.get("nameKey") or "", "") or sid
        e = {"unit": owner[sid], "name": nm, "kind": KINDS.get(sid.split("_", 1)[0].lower(), "")}
        if z is not None:
            e["zeta"] = z
        if o is not None:
            e["omicron"] = o
            mode = sk.get("omicronMode")
            e["mode"] = OMICRON_MODES.get(int(mode), str(mode)) if str(mode).isdigit() else str(mode or "")
        skills[sid] = e
    if skills:
        SKILLS_OUT.write_text(json.dumps(dict(sorted(skills.items())), indent=0, ensure_ascii=False), encoding="utf-8")
        print(f"Zeta/omicron abilities saved: {len(skills)} ({sum('omicron' in v for v in skills.values())} with omicrons)")
    out = {"_fetched": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), **dict(sorted(units.items()))}
    OUT.write_text(json.dumps(out, indent=0, ensure_ascii=False), encoding="utf-8")
    print(f"Unit list saved: {len(units)} units, {sum('img' in v for v in units.values())} with pictures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
