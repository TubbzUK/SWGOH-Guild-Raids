"""Territory War results: reads guilds/<guild>/tw/<date> TW.csv exports (WookieeBot "twstats") and works out
who joined, banners on defence and offence, results, and each member's trend across TWs.

Export columns (long format, one row per member per statistic):
    CurrentRoundEndTime, Instance, MapStatId, AllyCode, Name, DiscordTag, Score
MapStatId: stars (total banners), set_defense_stars (defence), attack_stars (offence), disobey.
Members in the file joined the TW; guild members missing from it didn't.
The result isn't in the export: officers record it when uploading (guilds/<guild>/tw/results.json).
"""
from __future__ import annotations

import datetime as dt
import json
import re
import statistics
from pathlib import Path

import build as B

STATS = {"stars": "total", "set_defense_stars": "defense", "attack_stars": "offense", "disobey": "disobey"}


def tw_columns(df) -> dict | None:
    cols = {B.norm(c): c for c in df.columns}
    if "mapstatid" not in cols or "score" not in cols:
        return None
    return {"stat": cols["mapstatid"], "score": cols["score"], "name": cols.get("name"), "ally": cols.get("allycode"),
            "end": cols.get("currentroundendtime"), "instance": cols.get("instance")}


def is_tw_file(path: Path) -> bool:
    try:
        df = B.with_header(B.read_raw(path), B.NAME_KEYS + B.ALLY_KEYS)
    except Exception:
        return False
    return bool(df is not None and tw_columns(df))


def end_date(df, cols) -> dt.date | None:
    if not cols["end"]:
        return None
    for v in df[cols["end"]]:
        n = B.to_number(v)
        if n:
            return dt.datetime.fromtimestamp(n / 1000 if n > 1e11 else n, dt.timezone.utc).date()
    return None


def read_tw(path: Path) -> dict | None:
    df = B.with_header(B.read_raw(path), B.NAME_KEYS + B.ALLY_KEYS)
    cols = tw_columns(df) if df is not None else None
    if not cols or not cols["name"]:
        B.warn(f"{path.name}: doesn't look like a Territory War export (no Name / MapStatId / Score columns)")
        return None
    rows: dict[str, dict] = {}
    for _, r in df.iterrows():
        name = B.cell(r[cols["name"]])
        stat = STATS.get(B.cell(r[cols["stat"]]).strip().lower())
        if not name or not stat:
            continue
        ally = re.sub(r"\D", "", B.cell(r[cols["ally"]])) if cols["ally"] else ""
        key = ally or B.norm(name)
        p = rows.setdefault(key, {"name": name, "ally": ally, "total": 0, "defense": 0, "offense": 0, "disobey": 0})
        p[stat] = (B.to_number(r[cols["score"]]) or 0)
    opp = ""
    if cols["instance"]:
        opp = next((B.cell(v) for v in df[cols["instance"]] if B.cell(v)), "")
        opp = re.sub(r"^\s*vs\.?\s*", "", opp).strip()
    for p in rows.values():   # total = defence + offence when the export has no "stars" row for someone
        if not p["total"] and (p["defense"] or p["offense"]):
            p["total"] = p["defense"] + p["offense"]
    return {"rows": list(rows.values()), "opponent": opp, "end": end_date(df, cols)}


def load_results(folder: Path) -> dict:
    f = folder / "results.json"
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        B.warn("tw/results.json couldn't be read - TW results left blank")
        return {}


def build_tw(gdir: Path, cfg: dict, current_names: dict[str, str]) -> dict | None:
    """current_names: {normalised name: display name} for current guild members (to list who didn't join)."""
    folder = gdir / "tw"
    files = B.data_files(folder) if folder.exists() else []
    if not files:
        return None
    results = load_results(folder)
    tws = []
    for path in files:
        parsed = read_tw(path)
        if not parsed or not parsed["rows"]:
            continue
        d, _ = B.name_date(path)
        d = d or parsed["end"]
        if not d:
            B.warn(f"tw/{path.name}: no date in the file or its name - skipped")
            continue
        tws.append({"date": d, "file": path.name, **parsed})
        print(f"TW:     {path.name} - {len(parsed['rows'])} joined, vs {parsed['opponent'] or '?'}")
    if not tws:
        return None
    tws.sort(key=lambda t: t["date"])

    trend_n = int(cfg.get("trend_over_last", 5))
    trend_thr = float(cfg.get("trend_threshold_pct", 3))
    people: dict[str, dict] = {}
    out = []
    for i, t in enumerate(tws):
        rows = sorted(t["rows"], key=lambda r: -r["total"])
        for k, r in enumerate(rows):
            r["rank"] = k + 1
            key = B.norm(r["name"])
            p = people.setdefault(key, {"name": r["name"], "hist": {}})
            p["name"] = r["name"]
            p["hist"][i] = r
        joined = {B.norm(r["name"]) for r in rows}
        missing = sorted((n for k, n in current_names.items() if k not in joined), key=str.lower) if i == len(tws) - 1 else []
        res = results.get(t["date"].isoformat()) or {}
        out.append({
            "id": t["date"].isoformat(), "date": t["date"].isoformat(), "file": t["file"], "opponent": t["opponent"],
            "joined": len(rows), "members": len(current_names) if i == len(tws) - 1 and current_names else None,
            "total": sum(r["total"] for r in rows), "defense": sum(r["defense"] for r in rows),
            "offense": sum(r["offense"] for r in rows), "disobey": sum(r["disobey"] for r in rows),
            "no_defense": sorted((r["name"] for r in rows if r["defense"] <= 0), key=str.lower),
            "no_offense": sorted((r["name"] for r in rows if r["offense"] <= 0), key=str.lower),
            "did_nothing": sorted((r["name"] for r in rows if r["total"] <= 0), key=str.lower),
            "median_total": statistics.median([r["total"] for r in rows]) if rows else 0,
            "median_defense": statistics.median([r["defense"] for r in rows]) if rows else 0,
            "median_offense": statistics.median([r["offense"] for r in rows]) if rows else 0,
            "not_joined": missing,
            "result": (res.get("result") or "").lower() or None,       # win / loss / draw
            "our_score": res.get("our_score"), "their_score": res.get("their_score"),
        })

    latest_i = len(tws) - 1
    players = []
    for key, p in people.items():
        hist = p["hist"]
        tot = [hist[i]["total"] if i in hist else None for i in range(len(tws))]
        played = [v for v in tot if v is not None]
        tpct, tlabel = B.trend_of(played[-trend_n:], trend_thr)
        last, prev = hist.get(latest_i), next((hist[i] for i in range(latest_i - 1, -1, -1) if i in hist), None)
        current = key in current_names if current_names else latest_i in hist
        if last:
            status = "idle" if last["total"] <= 0 else "no_defense" if last["defense"] <= 0 else "no_offense" if last["offense"] <= 0 else "full"
        else:
            status = "not_joined" if current else None
        players.append({
            "id": key, "name": p["name"], "current": current,
            "total": tot,
            "defense": [hist[i]["defense"] if i in hist else None for i in range(len(tws))],
            "offense": [hist[i]["offense"] if i in hist else None for i in range(len(tws))],
            "disobey": [hist[i]["disobey"] if i in hist else None for i in range(len(tws))],
            "rank": [hist[i]["rank"] if i in hist else None for i in range(len(tws))],
            "joined": len(played), "last": last["total"] if last else None, "prev": prev["total"] if prev else None,
            "delta": (last["total"] - prev["total"]) if last and prev else None,
            "avg": sum(played[-trend_n:]) / len(played[-trend_n:]) if played else None,
            "best": max(played) if played else None,
            "trend": tlabel, "trend_pct": tpct, "status": status,
        })
    # current members who never joined any TW tracked
    known = set(people)
    for k, n in current_names.items():
        if k not in known:
            players.append({"id": k, "name": n, "current": True, "total": [None] * len(tws), "defense": [None] * len(tws),
                            "offense": [None] * len(tws), "disobey": [None] * len(tws), "rank": [None] * len(tws),
                            "joined": 0, "last": None, "prev": None, "delta": None, "avg": None, "best": None,
                            "trend": "new", "trend_pct": None, "status": "not_joined"})
    players.sort(key=lambda p: (-(p["last"] if p["last"] is not None else -1), p["name"].lower()))
    rec = {r: sum(t["result"] == r for t in out) for r in ("win", "loss", "draw")}
    return {"tws": out, "players": players, "trend_over_last": trend_n, "record": rec}
