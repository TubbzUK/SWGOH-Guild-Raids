#!/usr/bin/env python3
"""
Pull guild data straight from the game through SWGoH Comlink, so fewer files need uploading.

For every guild whose config.yml has an `ally_code` (any member's ally code):
  * roster      - every member's units (stars, gear, relic) and GP, at most once a day
                  -> guilds/<guild>/roster/<date> roster.csv  (same columns as a WookieeBot roster export)
  * raid scores - the guild's latest finished raid of each type, with every member's score
                  -> guilds/<guild>/<raid>/<date> <Raid name>.csv  (skipped if that raid is already there)
  * TW results  - our score and theirs for recent territory wars -> win / loss in guilds/<guild>/tw/results.json
                  (a result an officer already entered is never changed)
Territory battle stats and TW banners per member aren't available from the game this way, so those
still come from WookieeBot uploads.

Comlink runs next to this script in the GitHub Action (a Docker container on port 3000):
    docker run -d -p 3000:3000 -e APP_NAME=guild-statistics ghcr.io/swgoh-utils/swgoh-comlink:latest
    python scripts/sync_game.py
COMLINK_URL overrides the address. Writes 'new=<added raid files>' and 'changed=true|false' to
$GITHUB_OUTPUT so the next steps can post new raids to Discord and skip a rebuild when nothing changed.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as B  # noqa: E402

COMLINK = os.getenv("COMLINK_URL", "http://localhost:3000").rstrip("/")
SHIPS_FILE = Path(__file__).resolve().parent / "ships.txt"
ROSTER_COLS = ["AllyCode", "Name", "BaseId", "CombatType", "Stars", "Level", "GearLevel", "GP", "RelicLevel"]


def call(endpoint: str, payload: dict, tries: int = 3) -> dict:
    body = json.dumps({"payload": payload, "enums": False}).encode()
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(f"{COMLINK}/{endpoint}", data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            last = e
            time.sleep(2 + 3 * i)
    raise RuntimeError(f"Comlink /{endpoint} failed: {last}")


def wait_ready(seconds: int = 150) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        try:
            req = urllib.request.Request(f"{COMLINK}/metadata", data=b"{}", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(4)
    return False


def num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def when(obj: dict) -> dt.date | None:
    """The end date of a raid or TW entry, whatever the field is called (seconds or milliseconds)."""
    for k, v in obj.items():
        lk = k.lower()
        if "end" in lk and ("time" in lk or "second" in lk):
            n = num(v)
            if n:
                if n > 1e11:
                    n /= 1000
                return dt.datetime.fromtimestamp(n, dt.timezone.utc).date()
    for v in obj.values():   # ids like 'TERRITORY_WAR_EVENT_C01:O1727456400000' carry the time
        m = re.search(r":O(\d{10,13})\b", str(v)) if isinstance(v, str) else None
        if m:
            n = float(m.group(1))
            return dt.datetime.fromtimestamp(n / 1000 if n > 1e11 else n, dt.timezone.utc).date()
    return None


def ally_of(v) -> str:
    return re.sub(r"\D", "", str(v or ""))


# ---------------------------------------------------------------- ships (to tell ships from characters)
def known_ships() -> set[str]:
    ships = set()
    if SHIPS_FILE.exists():
        ships |= {l.strip().upper() for l in SHIPS_FILE.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}
    # swgoh.gg's unit list (scripts/units.json), when the build has fetched it
    try:
        uj = json.loads((Path(__file__).resolve().parent / "units.json").read_text(encoding="utf-8"))
        ships |= {k.upper() for k, v in uj.items() if v.get("ship")}
    except (OSError, ValueError):
        pass
    # learn from any WookieeBot roster in the repo
    for f in B.GUILDS_DIR.glob("*/roster/*.csv"):
        try:
            with open(f, encoding="utf-8-sig", newline="") as fh:
                rd = csv.DictReader(fh)
                if not rd.fieldnames or "CombatType" not in rd.fieldnames or "BaseId" not in rd.fieldnames:
                    continue
                for r in rd:
                    if "ship" in (r.get("CombatType") or "").lower():
                        ships.add((r.get("BaseId") or "").upper())
        except OSError:
            pass
    ships.discard("")
    return ships


def is_ship(base: str, unit: dict, ships: set[str]) -> bool:
    if base in ships or base.startswith("CAPITAL"):
        return True
    return False


# ---------------------------------------------------------------- per guild
class Guild:
    def __init__(self, gdir: Path, cfg: dict, ships: set[str], log: list[str], added: list[str]):
        self.gdir, self.cfg, self.ships, self.log, self.added = gdir, cfg, ships, log, added
        self.players: dict[str, dict] = {}       # playerId -> /player response
        self.changed = False
        self.state_file = gdir / "game-sync.json"   # what was pulled last, so a raid isn't added twice
        try:
            self.state = json.loads(self.state_file.read_text(encoding="utf-8")) if self.state_file.exists() else {}
        except (OSError, ValueError):
            self.state = {}

    def save_state(self) -> None:
        self.state_file.write_text(json.dumps(self.state, indent=1, sort_keys=True), encoding="utf-8")

    def player(self, pid: str) -> dict | None:
        if pid not in self.players:
            try:
                self.players[pid] = call("player", {"playerId": pid})
            except RuntimeError as e:
                print(f"::warning::{self.gdir.name}: couldn't load a member ({e})")
                self.players[pid] = None
        return self.players[pid]

    def run(self) -> None:
        ally = ally_of(self.cfg.get("ally_code"))
        if len(ally) != 9:
            return
        me = call("player", {"allyCode": ally})
        gid = me.get("guildId")
        if not gid:
            print(f"::warning::{self.gdir.name}: the player with ally code {ally} isn't in a guild - nothing pulled")
            return
        g = (call("guild", {"guildId": gid, "includeRecentGuildActivityInfo": True}) or {}).get("guild") or {}
        members = g.get("member") or []
        gname = (g.get("profile") or {}).get("name") or me.get("guildName") or "?"
        print(f"{self.gdir.name}: {gname} - {len(members)} members")
        if not members:
            return
        self.roster(members)
        self.raids(g, members)
        self.tw(g)

    # roster, once a day
    def roster(self, members: list[dict]) -> None:
        rdir = self.gdir / "roster"
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        existing = B.data_files(rdir)
        if any(p.name.startswith(today) for p in existing):
            print(f"  roster: already have today's")
            return
        rows = []
        for m in members:
            p = self.player(m.get("playerId"))
            if not p:
                continue
            name, ally = p.get("name") or m.get("playerName"), ally_of(p.get("allyCode"))
            gp = num(m.get("galacticPower")) or 0
            first = True
            for u in p.get("rosterUnit") or []:
                base = str(u.get("definitionId") or "").split(":")[0].upper()
                if not base:
                    continue
                ship = is_ship(base, u, self.ships)
                relic = (u.get("relic") or {}).get("currentTier")
                rl = max(0, int(num(relic) or 0) - 2) if not ship and relic is not None else 0
                rows.append([ally, name, base, "Ship" if ship else "Character", int(num(u.get("currentRarity")) or 0),
                             int(num(u.get("currentLevel")) or 0), int(num(u.get("currentTier")) or 0),
                             int(gp), rl])
                first = False
        if not rows:
            print("::warning::  roster: no units came back - kept the old roster")
            return
        rdir.mkdir(parents=True, exist_ok=True)
        out = rdir / f"{today} roster.csv"
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(ROSTER_COLS)
        w.writerows(rows)
        out.write_text(buf.getvalue(), encoding="utf-8")
        for old in existing:
            if old != out:
                old.unlink()
        self.changed = True
        self.log.append(f"{self.gdir.name}: roster from the game ({len(members)} members, {len(rows)} units)")

    # the latest finished raid of each type
    def raids(self, g: dict, members: list[dict]) -> None:
        defs = B.load_raid_defs()
        day_first = str(self.cfg.get("date_format", "dmy")).lower() != "mdy"
        for res in g.get("recentRaidResult") or []:
            rid = str(res.get("raidId") or (res.get("identifier") or {}).get("campaignMissionId") or "")
            d = match_raid(rid, defs)
            if not d:
                print(f"::warning::{self.gdir.name}: a raid called '{rid}' came from the game but doesn't match any raids/*.yml. "
                      f"Add  game_ids: [\"{rid}\"]  to the right raid file to pick it up.")
                continue
            scores = {rm.get("playerId"): num(rm.get("memberProgress")) for rm in res.get("raidMember") or []}
            sig = f"{rid}|{res.get('guildRewardScore')}|{round(sum(v or 0 for v in scores.values()))}|{len(scores)}"
            if (self.state.get("raids") or {}).get(d["slug"]) == sig:
                continue      # the same raid as last time
            date = when(res) or dt.datetime.now(dt.timezone.utc).date()
            folder = self.gdir / d["slug"]
            have = [B.name_date(p, day_first)[0] for p in B.data_files(folder)]
            self.state.setdefault("raids", {})[d["slug"]] = sig
            if any(h and abs((h - date).days) <= 1 for h in have):
                continue      # already uploaded (or pulled) - leave it
            ids = [m.get("playerId") for m in members] + [pid for pid in scores if pid not in {m.get("playerId") for m in members}]
            rows = []
            for pid in ids:
                p = self.player(pid)
                m = next((x for x in members if x.get("playerId") == pid), {})
                name = (p or {}).get("name") or m.get("playerName")
                if not name:
                    continue
                s = scores.get(pid)
                rows.append([name, ally_of((p or {}).get("allyCode")), "" if s is None else int(s),
                             date.strftime("%d/%m/%Y" if day_first else "%m/%d/%Y")])
            if not any(r[2] != "" for r in rows):
                continue
            folder.mkdir(parents=True, exist_ok=True)
            out = folder / f"{date.isoformat()} {B_safe(d['name'])}.csv"
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["name", "allycode", "lastActualScore", "Date"])
            w.writerows(rows)
            out.write_text(buf.getvalue(), encoding="utf-8")
            self.changed = True
            self.added.append(out.relative_to(B.ROOT).as_posix())
            self.log.append(f"{self.gdir.name}: {d['name']} raid of {date} from the game ({sum(r[2] != '' for r in rows)} scores)")

    # territory war scores -> win / loss
    def tw(self, g: dict) -> None:
        results = g.get("recentTerritoryWarResult") or []
        if not results:
            return
        f = self.gdir / "tw" / "results.json"
        try:
            data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        except (OSError, ValueError):
            print(f"::warning::{self.gdir.name}: tw/results.json couldn't be read - TW results not updated")
            return
        added = 0
        for r in results:
            date = when(r)
            ours, theirs = num(r.get("score")), num(r.get("opponentScore"))
            if not date or ours is None or theirs is None:
                continue
            near = [k for k in data if re.fullmatch(r"\d{4}-\d{2}-\d{2}", k) and abs((dt.date.fromisoformat(k) - date).days) <= 1]
            if near:
                continue      # an officer (or an earlier pull) already recorded it
            opp = (r.get("opponentGuildProfile") or {}).get("name") if isinstance(r.get("opponentGuildProfile"), dict) else None
            data[date.isoformat()] = {"result": "win" if ours > theirs else "loss" if ours < theirs else "draw",
                                      "our_score": int(ours), "their_score": int(theirs), "source": "game",
                                      **({"opponent": opp} if opp else {})}
            added += 1
        if added:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(dict(sorted(data.items())), indent=1), encoding="utf-8")
            self.changed = True
            self.log.append(f"{self.gdir.name}: {added} territory war result{'s' if added > 1 else ''} from the game")


def B_safe(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "", s).strip() or "Raid"


def match_raid(rid: str, defs: list[dict]) -> dict | None:
    n = B.norm(rid)
    if not n:
        return None
    for d in defs:
        ids = [B.norm(x) for x in (d["cfg"].get("game_ids") or [])]
        if n in ids:
            return d
    for d in defs:
        keys = {B.norm(d["slug"]), B.norm(d["name"]), *d["match"]}
        if any(k and (k == n or k in n or n in k) for k in keys):
            return d
    return None


def main() -> int:
    targets = []
    for gdir in B.guild_dirs():
        B.use_guild(gdir)
        cfg = B.load_config()
        if len(ally_of(cfg.get("ally_code"))) == 9:
            targets.append((gdir, cfg))
    out = os.getenv("GITHUB_OUTPUT")
    if not targets:
        print("No guild has an ally_code in its config.yml - nothing to pull from the game")
        if out:
            with open(out, "a") as fh:
                fh.write("changed=false\nnew=\n")
        return 0
    if not wait_ready():
        print("::warning::Comlink didn't start, so nothing was pulled from the game this time")
        if out:
            with open(out, "a") as fh:
                fh.write("changed=false\nnew=\n")
        return 0
    ships = known_ships()
    log, added, changed = [], [], False
    for gdir, cfg in targets:
        B.use_guild(gdir)
        gs = Guild(gdir, cfg, ships, log, added)
        before = json.dumps(gs.state, sort_keys=True)
        try:
            gs.run()
        except Exception as e:   # one guild failing shouldn't stop the others
            print(f"::warning::{gdir.name}: pulling from the game failed: {e}")
        if json.dumps(gs.state, sort_keys=True) != before:
            gs.save_state()
        changed |= gs.changed
    for line in log:
        print("Pulled:", line)
    if not log:
        print("Nothing new from the game")
    if out:
        with open(out, "a") as fh:
            fh.write(f"changed={'true' if changed else 'false'}\n")
            fh.write("new<<EOF\n" + "\n".join(added) + "\nEOF\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
