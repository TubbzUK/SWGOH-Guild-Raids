#!/usr/bin/env python3
"""
Reads every raid export in guilds/<guild>/raids/, the latest roster in guilds/<guild>/roster/,
and config.yml for every guild folder in guilds/, then writes site/data/<guild>.json
and site/guilds.json for the dashboard.

Built around WookieeBot's raid export:
    name, allycode, estimatedScore, lastActualScore, diff, diffPercent, Date
and its guild roster export (one row per player per unit):
    AllyCode, Name, ..., BaseId, ..., GearLevel, ..., RelicLevel, ...
Other layouts work too as long as there is a name column and a score column.

Run locally:
    pip install -r requirements.txt
    python scripts/build.py
    python -m http.server -d site 8000      # then open http://localhost:8000
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import re
import shutil
import statistics
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
RAID_DEFS_DIR = ROOT / "raids"        # one .yml per raid type, shared by every guild
PLATOON_PLAN = ROOT / "guilds" / "_platoons" / "rote-plan.csv"   # RotE operations plan, shared by every guild
GUILDS_DIR = ROOT / "guilds"          # guilds/<guild>/{config.yml, roster/, <raid>/ ...}
SITE_DIR = ROOT / "site"
# Set per guild by use_guild()
GUILD_DIR = ROSTER_DIR = CONFIG_FILE = None
TABLE_EXTS = {".csv", ".tsv", ".txt", ".xlsx", ".xlsm", ".xls"}

# Column names we recognise, compared after lower-casing and removing spaces/punctuation.
# Order matters: earlier names win.
NAME_KEYS = ["name", "playername", "player", "membername", "member", "username", "user", "nickname"]
ALLY_KEYS = ["allycode", "ally", "allycodes"]
SCORE_KEYS = ["lastactualscore", "actualscore", "score", "raidscore", "totalscore", "damage", "totaldamage", "points"]
ESTIMATE_KEYS = ["estimatedscore", "estimate", "estimated", "estscore"]
DATE_KEYS = ["date", "raiddate", "raidend", "enddate"]
UNIT_KEYS = ["baseid", "defid", "character", "charactername", "unit", "unitname", "toon"]
RELIC_KEYS = ["reliclevel", "relic", "relictier", "relics"]
SKIP_NAMES = {"total", "guildtotal", "totals", "sum", "average", "avg"}

YMD_RE = re.compile(r"(\d{4})[-_./ ](\d{1,2})[-_./ ](\d{1,2})")
DMY_RE = re.compile(r"(\d{1,2})[-_./ ](\d{1,2})[-_./ ](\d{4})")

WARNINGS: list[str] = []
PLAN_KEYS: set[str] | None = None


def warn(msg: str) -> None:
    WARNINGS.append(msg)
    prefix = "::warning::" if os.getenv("GITHUB_ACTIONS") else "WARNING: "
    print(prefix + msg, file=sys.stderr)


def norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def guild_dirs() -> list[Path]:
    """Every folder in guilds/ except ones starting with '_' or '.' (e.g. _template)."""
    if not GUILDS_DIR.exists():
        return []
    return sorted(p for p in GUILDS_DIR.iterdir() if p.is_dir() and not p.name.startswith(("_", ".")))


def use_guild(gdir: Path) -> None:
    global GUILD_DIR, ROSTER_DIR, CONFIG_FILE
    GUILD_DIR, ROSTER_DIR, CONFIG_FILE = gdir, gdir / "roster", gdir / "config.yml"
    WARNINGS.clear()


def load_raid_defs() -> list[dict]:
    """raids/<slug>.yml -> name, target score, readiness characters, how to spot its files."""
    defs = []
    if RAID_DEFS_DIR.exists():
        for p in sorted(RAID_DEFS_DIR.iterdir()):
            if p.suffix.lower() not in (".yml", ".yaml") or p.name.startswith(("_", ".")):
                continue
            d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            # banner picture with the same name as the raid file; capitals don't matter (Order-66.JPG works)
            img = next((q for q in sorted(RAID_DEFS_DIR.iterdir())
                        if q.stem.lower() == p.stem.lower() and q.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")), None)
            defs.append({"slug": p.stem, "name": str(d.get("name", p.stem)), "order": d.get("order", 99),
                         "banner_file": img,
                         "target_score": d.get("target_score"),
                         "match": [norm(m) for m in (d.get("file_names") or [d.get("name", p.stem)])],
                         "cfg": d})
    defs.sort(key=lambda d: (d["order"], d["name"].lower()))
    return defs


def raid_for_filename(name: str, defs: list[dict]) -> dict | None:
    n = norm(name)
    return next((d for d in defs if any(m and m in n for m in d["match"])), None)


def load_config() -> dict:
    if CONFIG_FILE.exists():
        return yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8")) or {}
    return {}


# ---------------------------------------------------------------- file reading
def read_raw(path: Path) -> pd.DataFrame:
    """Read a csv/xlsx into a header-less DataFrame (first sheet for Excel)."""
    ext = path.suffix.lower()
    if ext in {".xlsx", ".xlsm", ".xls"}:
        return pd.read_excel(path, header=None, dtype=object)
    raw_bytes = path.read_bytes()
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw_bytes.decode("cp1252", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = [r for r in csv.reader(io.StringIO(text), dialect)]
    width = max((len(r) for r in rows), default=0)
    rows = [r + [""] * (width - len(r)) for r in rows]
    return pd.DataFrame(rows, dtype=object)


def with_header(raw: pd.DataFrame, keys: list[str]) -> pd.DataFrame | None:
    """Use the first row (within the top 20) containing a recognised column name as the header."""
    for i in range(min(20, len(raw))):
        cells = [cell(c) for c in raw.iloc[i]]
        if any(norm(c) in keys for c in cells):
            seen: dict[str, int] = {}
            cols = []
            for j, c in enumerate(cells):
                c = c or f"col{j}"
                if c in seen:
                    seen[c] += 1
                    c = f"{c}_{seen[c]}"
                else:
                    seen[c] = 0
                cols.append(c)
            df = raw.iloc[i + 1:].copy()
            df.columns = cols
            return df.reset_index(drop=True)
    return None


def find_col(df: pd.DataFrame, keys: list[str], exclude=()) -> str | None:
    cols = [c for c in df.columns if c not in exclude and c is not None]
    for k in keys:                       # exact matches first
        for c in cols:
            if norm(c) == k:
                return c
    for k in keys:                       # then "contains", for longer keys only
        if len(k) < 5:
            continue
        for c in cols:
            if k in norm(c):
                return c
    return None


def cell(v) -> str:
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    return str(v).strip()


def to_number(v) -> float | None:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return None if pd.isna(v) else float(v)
    s = cell(v).replace(",", "").replace(" ", "").replace(" ", "")
    if not s or s.lower() in {"nan", "none", "-", "n/a"}:
        return None
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)([kKmMbB]?)", s)
    if not m:
        return None
    mult = {"k": 1e3, "m": 1e6, "b": 1e9}.get(m.group(2).lower(), 1)
    return float(m.group(1)) * mult


def clean_ally(v) -> str | None:
    if isinstance(v, float) and not pd.isna(v):
        v = int(v)
    d = re.sub(r"\D", "", cell(v))
    return d if len(d) == 9 else None


def parse_relic(v) -> int | None:
    """'R7', '7', 'Relic 7', 7.0 -> 7 ; 'G12'/'G11' -> 0 ; blank/locked -> None."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return None if pd.isna(v) else int(v)
    s = cell(v).upper()
    if not s or s in {"NAN", "NONE", "-", "LOCKED", "N/A"}:
        return None
    if re.fullmatch(r"G\s*\d+", s):
        return 0
    m = re.fullmatch(r"(?:R|RELIC|RELIC\s*TIER)?\s*(\d+)(?:\.0+)?", s)
    return int(m.group(1)) if m else None


def parse_date(v, day_first: bool = True) -> dt.date | None:
    """Accepts real dates, '06/10/2026' (UK day-first by default), '2026-10-06', or Excel serial numbers."""
    if v is None:
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, pd.Timestamp):
        return None if pd.isna(v) else v.date()
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if pd.isna(v) or not (20000 < v < 80000):
            return None
        return (dt.datetime(1899, 12, 30) + dt.timedelta(days=float(v))).date()
    s = cell(v)
    m = YMD_RE.search(s)
    if m:
        try:
            return dt.date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None
    m = DMY_RE.search(s)
    if m:
        a, b, y = int(m[1]), int(m[2]), int(m[3])
        d, mo = (a, b) if day_first else (b, a)
        try:
            return dt.date(y, mo, d)
        except ValueError:
            try:
                return dt.date(y, d, mo)  # e.g. 10/25/2026 can only be month-first
            except ValueError:
                return None
    n = to_number(s)
    return parse_date(n, day_first) if n is not None else None


def name_date(path: Path, day_first=True) -> tuple[dt.date | None, str]:
    """Date and remaining label from a file name like '2026-10-06 Order 66.csv'."""
    stem = path.stem
    for rx in (YMD_RE, DMY_RE):
        m = rx.search(stem)
        if m:
            d = parse_date(m.group(0), day_first)
            if d:
                label = (stem[: m.start()] + " " + stem[m.end():]).strip(" -_.")
                return d, re.sub(r"[_]+", " ", label).strip()
    return None, re.sub(r"[_]+", " ", stem).strip()


def data_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(p for p in folder.iterdir()
                  if p.is_file() and p.suffix.lower() in TABLE_EXTS and not p.name.startswith(("~$", ".")))


# ---------------------------------------------------------------- identities
class Players:
    """Matches people across files by ally code first, then by name."""

    def __init__(self):
        self.by_ally: dict[str, str] = {}
        self.by_name: dict[str, str] = {}
        self.info: dict[str, dict] = {}

    def resolve(self, name: str, ally: str | None, update_name=True) -> str:
        n = norm(name)
        if ally and ally in self.by_ally:
            key = self.by_ally[ally]
        elif not ally and n and n in self.by_name:
            key = self.by_name[n]
        else:
            key = f"a{ally}" if ally else f"n{n}"
        rec = self.info.setdefault(key, {"name": name, "ally": ally})
        if update_name and name:
            rec["name"] = name
        rec["ally"] = ally or rec["ally"]
        if ally:
            self.by_ally[ally] = key
        if n:
            self.by_name[n] = key
        return key


# ---------------------------------------------------------------- raids
def read_raid_file(path: Path, day_first=True) -> dict | None:
    """Parse one raid export. Returns {'date', 'rows': [(name, ally, score|None, estimate|None)]}."""
    raw = read_raw(path)
    df = with_header(raw, NAME_KEYS)
    if df is None:
        warn(f"{path.name}: couldn't find a player name column - file skipped")
        return None
    name_c = find_col(df, NAME_KEYS)
    ally_c = find_col(df, ALLY_KEYS, exclude=[name_c])
    est_c = find_col(df, ESTIMATE_KEYS, exclude=[name_c, ally_c])
    date_c = find_col(df, DATE_KEYS, exclude=[name_c, ally_c, est_c])
    score_c = find_col(df, SCORE_KEYS, exclude=[name_c, ally_c, est_c, date_c])
    if not score_c:  # fall back to the most numeric column
        best, best_n = None, 0
        for c in df.columns:
            if c in (name_c, ally_c, est_c, date_c):
                continue
            n = sum(to_number(v) is not None for v in df[c])
            if n > best_n:
                best, best_n = c, n
        score_c = best
        if score_c:
            warn(f"{path.name}: no score column recognised, using '{score_c}'")
    if not score_c:
        warn(f"{path.name}: no score column found - file skipped")
        return None

    date = None
    if date_c:
        found = Counter(d for d in (parse_date(v, day_first) for v in df[date_c]) if d)
        if found:
            date = found.most_common(1)[0][0]
    fdate, label = name_date(path, day_first)
    date = date or fdate
    if date is None:
        warn(f"{path.name}: no Date column or date in the file name - using today's date")
        date = dt.date.today()

    rows = []
    for _, r in df.iterrows():
        name = cell(r[name_c])
        if not name or norm(name) in SKIP_NAMES:
            continue
        rows.append((name, clean_ally(r[ally_c]) if ally_c else None,
                     to_number(r[score_c]), to_number(r[est_c]) if est_c else None))
    return {"date": date, "label": label, "rows": rows, "score_col": score_c}


def load_raids(players: Players, cfg: dict, raid_dir: Path, label: str) -> list[dict]:
    day_first = cfg.get("date_format", "dmy").lower() != "mdy"
    parsed = []
    for path in data_files(raid_dir):
        r = read_raid_file(path, day_first)
        if r:
            r["file"] = path.name
            parsed.append(r)
            print(f"Raid:   {path.name} - {r['date']} - {len(r['rows'])} rows (score column '{r['score_col']}')")
    parsed.sort(key=lambda r: (r["date"], r["file"]))

    by_date: dict[dt.date, dict] = {}
    for r in parsed:
        if r["date"] in by_date:
            warn(f"{r['file']} has the same raid date ({r['date']}) as {by_date[r['date']]['file']} - using {r['file']}")
        by_date[r["date"]] = r

    raids = []
    for date in sorted(by_date):
        r = by_date[date]
        scores: dict[str, float | None] = {}
        estimates: dict[str, float | None] = {}
        for name, ally, score, est in r["rows"]:
            key = players.resolve(name, ally)
            if key in scores and scores[key] is not None and score is not None:
                warn(f"{r['file']}: {name} appears twice - keeping the higher score")
                score = max(score, scores[key])
            scores[key] = score if score is not None else scores.get(key)
            estimates[key] = est
        raids.append({"date": date, "id": date.isoformat(), "file": r["file"],
                      "label": label,
                      "scores": scores, "estimates": estimates})
    return raids


# ---------------------------------------------------------------- roster
def load_roster(players: Players):
    files = data_files(ROSTER_DIR)
    if not files:
        warn("No roster export uploaded for this guild yet - readiness scores will be empty")
        return None, {}, None
    files.sort(key=lambda p: (name_date(p)[0] or dt.date.fromtimestamp(p.stat().st_mtime), p.name))
    path = files[-1]
    rdate = name_date(path)[0] or dt.date.fromtimestamp(path.stat().st_mtime)
    raw = read_raw(path)
    df = with_header(raw, NAME_KEYS + ALLY_KEYS)
    if df is None:
        warn(f"{path.name}: couldn't find a player name column (e.g. 'Name' or 'Player')")
        return path.name, {}, rdate
    name_c = find_col(df, NAME_KEYS)
    ally_c = find_col(df, ALLY_KEYS, exclude=[name_c])
    unit_c = find_col(df, UNIT_KEYS, exclude=[name_c, ally_c])
    relic_c = find_col(df, RELIC_KEYS, exclude=[name_c, ally_c, unit_c])

    roster: dict[str, dict[str, int | None]] = {}
    if unit_c and relic_c:          # long format: one row per player+unit (WookieeBot roster export)
        names = df[name_c].map(cell)
        allies = df[ally_c].map(clean_ally) if ally_c else pd.Series([None] * len(df))
        units = df[unit_c].map(norm)
        relics = df[relic_c].map(parse_relic)
        for name, ally, unit, relic in zip(names, allies, units, relics):
            if not name or norm(name) in SKIP_NAMES:
                continue
            key = players.resolve(name, ally, update_name=False)
            roster.setdefault(key, {})[unit] = relic
    else:                           # wide format: one row per player, a column per character
        char_cols = [c for c in df.columns if c not in (name_c, ally_c)]
        for _, r in df.iterrows():
            name = cell(r[name_c])
            if not name or norm(name) in SKIP_NAMES:
                continue
            key = players.resolve(name, clean_ally(r[ally_c]) if ally_c else None, update_name=False)
            roster[key] = {norm(c): parse_relic(r[c]) for c in char_cols}
    print(f"Roster: {path.name} - {len(roster)} players ({'long' if unit_c and relic_c else 'wide'} format)")
    return path.name, roster, rdate


# ---------------------------------------------------------------- readiness
def load_readiness_config(cfg: dict) -> dict:
    rc = cfg.get("readiness") or {}
    max_relic = int(rc.get("max_relic", 10))

    def parse_chars(items, where):
        out, seen = [], set()
        for c in items or []:
            if isinstance(c, str):
                cid, relic, label, aliases = c, max_relic, None, []
            elif isinstance(c, dict) and ("id" in c or "name" in c):
                cid = c.get("id") or c.get("name")
                relic = int(c.get("relic", max_relic))
                label = c.get("label") or (c.get("name") if c.get("id") else None)
                aliases = c.get("aliases") or []
            elif isinstance(c, dict) and len(c) == 1:
                (cid, relic), label, aliases = next(iter(c.items())), None, []
            else:
                warn(f"config: couldn't read readiness character {c!r}")
                continue
            if norm(cid) in seen:
                warn(f"config: {cid} is listed twice in {where} - counted once")
                continue
            seen.add(norm(cid))
            out.append({"id": str(cid), "label": str(label or cid), "relic": int(relic),
                        "keys": [norm(cid)] + [norm(a) for a in aliases]})
        return out

    teams = []
    if rc.get("characters"):
        chars = parse_chars(rc["characters"], "characters")
        if chars:
            teams.append({"name": rc.get("group_name", "Raid characters"), "weight": 1.0, "characters": chars})
    for t in rc.get("teams") or []:
        chars = parse_chars(t.get("characters"), t.get("name", "a team"))
        if chars:
            teams.append({"name": str(t.get("name", f"Team {len(teams) + 1}")),
                          "weight": float(t.get("weight", 1)), "characters": chars})
    return {"title": rc.get("title", "Raid readiness"), "max_relic": max_relic,
            "ready_pct": float(rc.get("ready_pct", 75)), "close_pct": float(rc.get("close_pct", 50)),
            "teams": teams}


def readiness_for(units: dict[str, int | None] | None, rconf: dict):
    if units is None or not rconf["teams"]:
        return None
    teams, total_w, acc = [], 0.0, 0.0
    relics, relicked, at_target, n_chars = {}, 0, 0, 0
    for t in rconf["teams"]:
        have_sum, need_sum, all_ready = 0, 0, True
        for c in t["characters"]:
            relic = next((units[k] for k in c["keys"] if k in units), None)
            relics[c["id"]] = relic
            have = max(relic or 0, 0)
            have_sum += min(have, c["relic"])
            need_sum += c["relic"]
            relicked += have > 0
            at_target += have >= c["relic"]
            all_ready &= have >= c["relic"]
            n_chars += 1
        tp = have_sum / need_sum if need_sum else 0.0
        teams.append({"name": t["name"], "pct": round(tp * 100, 1), "ready": all_ready})
        total_w += t["weight"]
        acc += tp * t["weight"]
    score = round(acc / total_w * 100, 1) if total_w else 0.0
    status = "ready" if score >= rconf["ready_pct"] else "close" if score >= rconf["close_pct"] else "building"
    return {"score": score, "status": status, "teams": teams, "relics": relics,
            "relicked": relicked, "at_target": at_target, "characters": n_chars}


def unknown_characters(roster: dict, rconf: dict) -> list[str]:
    """Readiness characters that appear in nobody's roster (new unit, or a spelling/ID mismatch)."""
    if not roster:
        return []
    seen = set().union(*[set(u) for u in roster.values()])
    return [c["id"] for t in rconf["teams"] for c in t["characters"] if not any(k in seen for k in c["keys"])]


# ---------------------------------------------------------------- trend
def trend_of(values: list[float], threshold_pct: float):
    """Least-squares slope of the player's recent scores, as % of their average per raid."""
    if len(values) < 3:
        return None, "new"
    n = len(values)
    xm, ym = (n - 1) / 2, sum(values) / n
    denom = sum((i - xm) ** 2 for i in range(n))
    slope = sum((i - xm) * (v - ym) for i, v in enumerate(values)) / denom
    pct = slope / ym * 100 if ym else 0.0
    label = "improving" if pct >= threshold_pct else "declining" if pct <= -threshold_pct else "level"
    return round(pct, 1), label


def roster_names_of(roster: dict, players: "Players") -> list[str]:
    return [players.info[k]["name"] for k in roster] if roster else []


# ---------------------------------------------------------------- platoons
def plan_unit_keys() -> set[str] | None:
    """Unit keys (BaseId and name) used by the RotE plan, to keep the platoon roster small."""
    if not PLATOON_PLAN.exists():
        return None
    df = with_header(read_raw(PLATOON_PLAN), ["phase"])
    if df is None:
        return None
    keys = set()
    for col in df.columns:
        if norm(col) in ("baseid", "charactername", "unitname", "character", "unit", "toon", "ship", "name"):
            keys |= {norm(v) for v in df[col] if cell(v)}
    return keys or None


def platoon_roster(path: Path, keep: set[str] | None) -> dict | None:
    """The planner's roster format: players, GP and each player's units with relic/stars/gear.
    Mirrors the planner's own reading of a WookieeBot roster export."""
    raw = read_raw(path)
    df = with_header(raw, NAME_KEYS + ALLY_KEYS)
    if df is None:
        return None
    cols = {norm(c): c for c in df.columns}
    name_c, ally_c = cols.get("name"), cols.get("allycode")
    base_c = cols.get("baseid")
    relic_c = find_col(df, ["reliclevel", "relic"])
    stars_c = find_col(df, ["stars", "rarity"])
    gear_c = find_col(df, ["gearlevel", "gear"])
    type_c = find_col(df, ["combattype"])
    power_c = cols.get("power")
    if not (name_c and base_c):
        return None

    def ival(v):
        n = to_number(v)
        return int(n) if n is not None else None

    ids, taken, players, gp = {}, {}, {}, {}
    max_rel, g13min, low_gear_one = -1, 10 ** 9, False
    better = lambda a, b: ((a.get("relic") or -1), (a.get("gear") or -1), (a.get("stars") or -1)) > \
                          ((b.get("relic") or -1), (b.get("gear") or -1), (b.get("stars") or -1))
    for _, r in df.iterrows():
        nm = cell(r[name_c])
        if not nm:
            continue
        code = clean_ally(r[ally_c]) if ally_c else None
        pid = "#" + code if code else "@" + nm
        if pid not in ids:
            disp = nm if taken.get(nm, pid) == pid else f"{nm} ({pid[-3:]})"
            taken[disp] = pid
            ids[pid] = disp
        p = ids[pid]
        units = players.setdefault(p, {})
        if power_c:
            gp[p] = gp.get(p, 0) + (to_number(r[power_c]) or 0)
        key = norm(r[base_c])
        if not key:
            continue
        lvl = {}
        if relic_c and cell(r[relic_c]) != "":
            lvl["relic"] = ival(r[relic_c])
        if stars_c and cell(r[stars_c]) != "":
            lvl["stars"] = ival(r[stars_c])
        if gear_c and cell(r[gear_c]) != "":
            lvl["gear"] = ival(r[gear_c])
        if type_c and "ship" in cell(r[type_c]).lower():
            lvl["ship"] = True
            lvl.pop("relic", None)
        if not lvl:
            lvl["unknown"] = True
        if not lvl.get("ship") and lvl.get("relic") is not None:
            max_rel = max(max_rel, lvl["relic"])
            if lvl.get("gear") == 13:
                g13min = min(g13min, lvl["relic"])
            elif lvl.get("gear") is not None and lvl["relic"] == 1:
                low_gear_one = True
        if keep is not None and key not in keep:
            continue
        prev = units.get(key)
        if prev is None or better(lvl, prev):
            units[key] = lvl
    raw_scale = max_rel >= 11 or (2 <= g13min < 10 ** 9 and low_gear_one)
    if raw_scale:
        for units in players.values():
            for l in units.values():
                if l.get("relic") is not None:
                    l["relic"] = max(0, l["relic"] - 2)
    names = list(players)
    return {"players": names, "roster": [players[n] for n in names],
            "gp": [round(gp.get(n, 0)) for n in names], "raw": False,
            "file": path.name}


# ---------------------------------------------------------------- main
def raid_view(gdir: Path, cfg: dict, rdef: dict, raids: list[dict], roster: dict, roster_file,
              players: Players, current: set) -> dict:
    """Everything the site shows for one guild + one raid type."""
    recent_n = int(cfg.get("average_over_last", 5))
    trend_n = int(cfg.get("trend_over_last", 5))
    trend_thr = float(cfg.get("trend_threshold_pct", 3))
    target = (cfg.get("target_scores") or {}).get(rdef["slug"], rdef["target_score"])
    target = float(target) if target else None
    rconf = load_readiness_config(rdef["cfg"])
    for cid in unknown_characters(roster, rconf):
        warn(f"{rdef['name']} readiness character '{cid}' isn't in anyone's roster - new unit, "
             f"or check the ID in raids/{rdef['slug']}.yml")

    raids_out = []
    for i, r in enumerate(raids):
        listed = r["scores"]
        vals = [v for v in listed.values() if v and v > 0]
        total = sum(vals)
        out = {
            "id": r["id"], "date": r["date"].isoformat(), "label": r["label"], "file": r["file"],
            "total": total,
            "participants": len(vals),
            "members": len(listed),
            "zero": sum(1 for v in listed.values() if v == 0),
            "no_attempt": sum(1 for v in listed.values() if v is None),
            "below_target": sum(1 for v in listed.values() if v and target and v < target),
            "average": total / len(vals) if vals else 0,
            "median": statistics.median(vals) if vals else 0,
            "max": max(vals) if vals else 0,
        }
        if i == len(raids) - 1:
            out["no_score"] = sorted((players.info[k]["name"] for k, v in listed.items() if not v and k in current),
                                     key=str.lower)
        raids_out.append(out)

    latest_rank = {}
    if raids:
        ordered = sorted(((v, k) for k, v in raids[-1]["scores"].items() if v and v > 0), reverse=True)
        latest_rank = {k: i + 1 for i, (_, k) in enumerate(ordered)}

    players_out = []
    all_keys = {k for r in raids for k in r["scores"]} | set(roster) | current
    for key in all_keys:
        info = players.info[key]
        series = [r["scores"].get(key) for r in raids]
        played = [v for v in series if v and v > 0]
        recent = [v for v in series[-recent_n:] if v and v > 0]
        last = series[-1] if series else None
        prev = next((v for v in reversed(series[:-1]) if v and v > 0), None) if series else None
        delta = (last - prev) if (last and prev) else None
        tpct, tlabel = trend_of(played[-trend_n:], trend_thr)
        est = raids[-1]["estimates"].get(key) if raids else None
        players_out.append({
            "id": key,
            "name": info["name"],
            "ally": info["ally"],
            "current": key in current,
            "scores": series,
            "last": last,
            "prev": prev,
            "delta": delta,
            "delta_pct": round(delta / prev * 100, 1) if delta is not None else None,
            "avg_recent": sum(recent) / len(recent) if recent else None,
            "best": max(played) if played else None,
            "worst": min(played) if played else None,
            "played": len(played),
            "listed": sum(1 for r in raids if key in r["scores"]),
            "played_recent": len(recent),
            "recent_window": min(recent_n, len(raids)),
            "trend_pct": tpct,
            "trend": tlabel,
            "estimate": est,
            "vs_estimate_pct": round((last - est) / est * 100, 1) if (last and est) else None,
            "rank": latest_rank.get(key),
            "readiness": readiness_for(roster.get(key), rconf) if roster else None,
        })
    # Former members only matter where they have scores in this raid
    players_out = [p for p in players_out if p["current"] or p["played"] or p["listed"]]
    players_out.sort(key=lambda p: (-(p["last"] or 0), -((p["readiness"] or {}).get("score") or 0), p["name"].lower()))

    cur = [p for p in players_out if p["current"]]
    trend_summary = {t: sum(p["trend"] == t for p in cur) for t in ("improving", "level", "declining", "new")}

    ready_summary = None
    cur_ready = [p["readiness"] for p in cur if p["readiness"]]
    if cur_ready and rconf["teams"]:
        ready_summary = {
            "average": round(sum(r["score"] for r in cur_ready) / len(cur_ready), 1),
            "players": len(cur_ready),
            "status": {s: sum(r["status"] == s for r in cur_ready) for s in ("ready", "close", "building")},
            "teams": [{"name": t["name"], "ready": sum(r["teams"][i]["ready"] for r in cur_ready)}
                      for i, t in enumerate(rconf["teams"])],
            "characters": [{"id": c["id"], "label": c["label"], "relic": c["relic"], "team": t["name"],
                            "at_target": sum((r["relics"].get(c["id"]) or 0) >= c["relic"] for r in cur_ready),
                            "relicked": sum((r["relics"].get(c["id"]) or 0) > 0 for r in cur_ready),
                            "average": round(sum(max(r["relics"].get(c["id"]) or 0, 0) for r in cur_ready)
                                             / len(cur_ready), 1)}
                           for t in rconf["teams"] for c in t["characters"]],
        }

    return {
        "slug": gdir.name,
        "raid_slug": rdef["slug"],
        "guild_name": cfg.get("guild_name", gdir.name),
        "raid_name": rdef["name"],
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
        "average_over_last": recent_n,
        "trend_over_last": trend_n,
        "trend_threshold_pct": trend_thr,
        "target_score": target,
        "roster_file": roster_file,
        "raids": raids_out,
        "players": players_out,
        "trend_summary": trend_summary,
        "readiness_config": {
            "title": rconf["title"], "max_relic": rconf["max_relic"],
            "ready_pct": rconf["ready_pct"], "close_pct": rconf["close_pct"],
            "teams": [{"name": t["name"], "weight": t["weight"],
                       "characters": [{"id": c["id"], "label": c["label"], "relic": c["relic"]}
                                      for c in t["characters"]]}
                      for t in rconf["teams"]],
        },
        "readiness_summary": ready_summary,
        "warnings": list(WARNINGS),
    }


def build_guild(gdir: Path, defs: list[dict]) -> dict:
    use_guild(gdir)
    print(f"\n=== {gdir.name} ===")
    cfg = load_config()
    players = Players()

    # Load every raid type's score files first, keeping each one's warnings separate
    loaded, raid_warn = {}, {}
    for d in defs:
        WARNINGS.clear()
        loaded[d["slug"]] = load_raids(players, cfg, gdir / d["slug"], d["name"])
        raid_warn[d["slug"]] = list(WARNINGS)
    for extra in sorted(p.name for p in gdir.iterdir() if p.is_dir() and p.name not in loaded
                        and p.name not in ("roster", "tb", "tw", "posts") and not p.name.startswith((".", "_"))):
        print(f"Note: folder {gdir.name}/{extra} doesn't match a raid in raids/ - ignored")

    WARNINGS.clear()
    roster_file, roster, roster_date = load_roster(players)
    for stray in data_files(gdir):
        warn(f"{stray.name} wasn't filed: its name doesn't say which raid it's from. "
             f"Delete it and upload it into the raid's folder instead (e.g. {gdir.name}/{defs[0]['slug'] if defs else 'order-66'}/)")
    guild_warn = list(WARNINGS)

    # Current members: from whichever is newer - the latest raid export (any raid type;
    # WookieeBot lists the whole guild) or the roster export.
    latest = max((r for rs in loaded.values() for r in rs), key=lambda r: r["date"], default=None)
    if roster and (latest is None or (roster_date and roster_date > latest["date"])):
        current = set(roster)
    else:
        current = set(latest["scores"]) if latest else set()

    out_dir = SITE_DIR / "data" / gdir.name
    out_dir.mkdir(parents=True, exist_ok=True)

    # Territory Battles
    sys.modules.setdefault("build", sys.modules[__name__])   # so tb.py shares this module (and its warnings list)
    import tb as TB
    WARNINGS.clear()
    tb_data = TB.build_tb(gdir, cfg, {norm(players.info[k]["name"]) for k in current} | {norm(n) for n in (roster_names_of(roster, players))})
    if tb_data:
        tb_data.update({"slug": gdir.name, "guild_name": cfg.get("guild_name", gdir.name),
                        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
                        "warnings": list(WARNINGS)})
        (out_dir / "tb.json").write_text(json.dumps(tb_data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
        print(f"Wrote site/data/{gdir.name}/tb.json: {len(tb_data['tbs'])} TBs, {len(tb_data['players'])} members")
    tb_index = {"count": len(tb_data["tbs"]), "latest": tb_data["tbs"][-1]["date"]} if tb_data else None

    # Territory Wars
    import tw as TW
    WARNINGS.clear()
    cur_names = {norm(players.info[k]["name"]): players.info[k]["name"] for k in current}
    for n in roster_names_of(roster, players):
        cur_names.setdefault(norm(n), n)
    tw_data = TW.build_tw(gdir, cfg, cur_names)
    if tw_data:
        tw_data.update({"slug": gdir.name, "guild_name": cfg.get("guild_name", gdir.name),
                        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
                        "warnings": list(WARNINGS)})
        (out_dir / "tw.json").write_text(json.dumps(tw_data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
        print(f"Wrote site/data/{gdir.name}/tw.json: {len(tw_data['tws'])} TWs, {len(tw_data['players'])} members")
    tw_index = {"count": len(tw_data["tws"]), "latest": tw_data["tws"][-1]["date"]} if tw_data else None

    # Platoon planner: this guild's roster in the planner's format, and its saved assignments
    has_platoon_roster = False
    roster_files = data_files(ROSTER_DIR)
    if roster_files:
        newest = max(roster_files, key=lambda p: (name_date(p)[0] or dt.date.fromtimestamp(p.stat().st_mtime), p.name))
        pr = platoon_roster(newest, PLAN_KEYS)
        if pr:
            pr["updated"] = (roster_date or dt.date.today()).isoformat()
            (out_dir / "platoon-roster.json").write_text(json.dumps(pr, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
            has_platoon_roster = True
            print(f"Platoon roster: {len(pr['players'])} players")
    for name in ("tb-settings.json", "stats-settings.json"):   # officers' page settings
        if (gdir / name).exists():
            shutil.copy2(gdir / name, out_dir / name)
    if (gdir / "platoon-settings.json").exists():
        shutil.copy2(gdir / "platoon-settings.json", out_dir / "platoon-settings.json")
    saved = gdir / "platoons.json"
    platoons_saved = None
    if saved.exists():
        shutil.copy2(saved, out_dir / "platoons.json")
        try:
            platoons_saved = json.loads(saved.read_text(encoding="utf-8")).get("savedAt")
        except (ValueError, AttributeError):
            warn("platoons.json couldn't be read")
    raids_index = []
    for d in defs:
        WARNINGS[:] = guild_warn + raid_warn[d["slug"]]
        view = raid_view(gdir, cfg, d, loaded[d["slug"]], roster, roster_file, players, current)
        (out_dir / f"{d['slug']}.json").write_text(json.dumps(view, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote site/data/{gdir.name}/{d['slug']}.json: {len(view['raids'])} raids, "
              f"{len(view['players'])} players, {len(view['warnings'])} warnings")
        raids_index.append({"slug": d["slug"], "name": d["name"], "raids": len(view["raids"]),
                            "latest": view["raids"][-1]["date"] if view["raids"] else None,
                            "banner": f"banners/{d['banner_file'].name}" if d["banner_file"] else None})

    with_scores = [r for r in raids_index if r["latest"]]
    default = max(with_scores, key=lambda r: r["latest"])["slug"] if with_scores else \
        (raids_index[0]["slug"] if raids_index else None)
    return {"slug": gdir.name, "name": cfg.get("guild_name", gdir.name), "members": len(current),
            "raids": raids_index, "default_raid": default,
            "has_data": bool(with_scores or roster or tb_data or tw_data), "order": cfg.get("site_order", 99),
            "platoons": {"roster": has_platoon_roster, "saved": platoons_saved},
            "tb": tb_index, "tw": tw_index}


def main() -> int:
    global PLAN_KEYS
    PLAN_KEYS = plan_unit_keys()
    if PLATOON_PLAN.exists():
        (SITE_DIR / "data" / "platoons").mkdir(parents=True, exist_ok=True)
        shutil.copy2(PLATOON_PLAN, SITE_DIR / "data" / "platoons" / "rote-plan.csv")
    defs = load_raid_defs()
    # Optional banner pictures: raids/<raid>.jpg|png|webp is shown instead of the drawn artwork
    banner_dir = SITE_DIR / "banners"
    shutil.rmtree(banner_dir, ignore_errors=True)
    for d in defs:
        if d["banner_file"]:
            banner_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(d["banner_file"], banner_dir / d["banner_file"].name)
            print(f"Banner: {d['banner_file'].name}")
    if not defs:
        print("No raid definitions found in raids/", file=sys.stderr)
    guilds = [build_guild(g, defs) for g in guild_dirs()]
    if not guilds:
        print("No guild folders found in guilds/", file=sys.stderr)
    # Guilds with no files yet are left off the site's guild switcher
    guilds.sort(key=lambda g: (g.pop("order"), g["name"].lower()))
    index = [g for g in guilds if g["has_data"]]
    (SITE_DIR / "guilds.json").write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8")
    # Settings for the site's upload page: every guild (even ones with no files yet) and raid
    upload_cfg = {
        "repository": os.getenv("GITHUB_REPOSITORY"),          # e.g. TubbzUK/SWGOH-Guild-Raids (set by GitHub Actions)
        "branch": os.getenv("GITHUB_REF_NAME") or "main",
        "guilds": [{"slug": g["slug"], "name": g["name"]} for g in guilds],
        "raids": [{"slug": d["slug"], "name": d["name"], "match": d["match"]} for d in defs],
    }
    (SITE_DIR / "upload-config.json").write_text(json.dumps(upload_cfg, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote site/guilds.json: {', '.join(g['name'] for g in index) or 'no guilds with data'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
