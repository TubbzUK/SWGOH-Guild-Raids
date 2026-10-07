"""Territory Battle results: reads guilds/<guild>/tb/<date> *.csv|xlsx exports and works out
per-member and per-phase stats, trends across TBs and what each member could improve.

Expected export columns (one row per member):
    Name, Total Territory Points, Platoon Units, Combat Waves, Rogue Actions,
    P1 Deployed, P1 Territory Points, P1 Deployed GP, P1 Combat Attempts, P1 Special Attempts, P1 Waves,
    P2 ... (as many phases as the TB has)
"Waves" is waves completed; "Combat Attempts" is combat missions attempted.
"""
from __future__ import annotations

import re
import statistics
from pathlib import Path

import build as B

PHASE_RE = re.compile(r"^p(\d+)(deployed|territorypoints|deployedgp|combatattempts|specialattempts|waves)$")


def tb_columns(df) -> dict | None:
    cols = {B.norm(c): c for c in df.columns}
    if "totalterritorypoints" not in cols and not any(PHASE_RE.match(k) for k in cols):
        return None
    phases: dict[int, dict] = {}
    for k, c in cols.items():
        m = PHASE_RE.match(k)
        if m:
            phases.setdefault(int(m.group(1)), {})[m.group(2)] = c
    return {"name": cols.get("name") or cols.get("player") or cols.get("membername"),
            "total": cols.get("totalterritorypoints"), "platoons": cols.get("platoonunits"),
            "waves": cols.get("combatwaves"), "rogue": cols.get("rogueactions"),
            "phases": dict(sorted(phases.items()))}


def is_tb_file(path: Path) -> bool:
    try:
        df = B.with_header(B.read_raw(path), B.NAME_KEYS)
    except Exception:
        return False
    return bool(df is not None and tb_columns(df))


def demojibake(s: str) -> str:
    """'Obo NÃ¢m' -> 'Obo Nâm' (UTF-8 text that was read as Latin-1 somewhere along the way)."""
    if any(ch in s for ch in "ÃÂâ€"):
        try:
            return s.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return s


def read_tb(path: Path) -> dict | None:
    df = B.with_header(B.read_raw(path), B.NAME_KEYS)
    cols = tb_columns(df) if df is not None else None
    if not cols or not cols["name"]:
        B.warn(f"{path.name}: doesn't look like a Territory Battle export (no Name / Territory Points columns)")
        return None
    num = lambda r, c: (B.to_number(r[c]) or 0) if c else 0  # noqa: E731
    rows = []
    for _, r in df.iterrows():
        name = demojibake(B.cell(r[cols["name"]]))
        if not name or B.norm(name) in B.SKIP_NAMES:
            continue
        phases = []
        for p, pc in cols["phases"].items():
            dep_txt = B.cell(r[pc["deployed"]]).lower() if pc.get("deployed") else ""
            gp = num(r, pc.get("deployedgp"))
            phases.append({"p": p, "dep": dep_txt in ("yes", "y", "true", "1"), "gp": gp,
                           "tp": num(r, pc.get("territorypoints")), "att": num(r, pc.get("combatattempts")),
                           "spec": num(r, pc.get("specialattempts")), "waves": num(r, pc.get("waves"))})
        tp = num(r, cols["total"]) if cols["total"] else sum(x["tp"] for x in phases)
        waves = num(r, cols["waves"]) if cols["waves"] else sum(x["waves"] for x in phases)
        rows.append({"name": name, "tp": tp, "platoons": num(r, cols["platoons"]), "waves": waves,
                     "rogue": num(r, cols["rogue"]), "att": sum(x["att"] for x in phases),
                     "spec": sum(x["spec"] for x in phases), "phases": phases})
    return {"rows": rows, "n_phases": max(cols["phases"]) if cols["phases"] else 0}


def build_tb(gdir: Path, cfg: dict, current_norm: set[str]) -> dict | None:
    folder = gdir / "tb"
    files = B.data_files(folder) if folder.exists() else []
    if not files:
        return None
    tbs = []
    for path in files:
        d, label = B.name_date(path)
        if not d:
            B.warn(f"tb/{path.name}: no date at the start of the file name (e.g. 2026-10-05 RotE.csv) - skipped")
            continue
        parsed = read_tb(path)
        if parsed and parsed["rows"]:
            tbs.append({"date": d, "label": label or "TB", "file": path.name, **parsed})
            print(f"TB:     {path.name} - {len(parsed['rows'])} members, {parsed['n_phases']} phases")
    if not tbs:
        return None
    tbs.sort(key=lambda t: t["date"])

    trend_n = int(cfg.get("trend_over_last", 5))
    trend_thr = float(cfg.get("trend_threshold_pct", 3))
    cfg_max = [float(x) for x in (cfg.get("tb_max_waves") or [])]

    tbs_out, people = [], {}
    for i, t in enumerate(tbs):
        n = t["n_phases"]
        # Most waves a member could complete in each phase (guild setting, else the best seen)
        maxw, est = [], []
        for p in range(1, n + 1):
            best = max((ph["waves"] for r in t["rows"] for ph in r["phases"] if ph["p"] == p), default=0)
            if p - 1 < len(cfg_max) and cfg_max[p - 1] > 0:
                maxw.append(max(cfg_max[p - 1], best)); est.append(False)
            else:
                maxw.append(best or 1); est.append(True)
        total_max = sum(maxw)
        rows = t["rows"]
        med_tp = statistics.median([r["tp"] for r in rows]) if rows else 0
        med_pl = statistics.median([r["platoons"] for r in rows]) if rows else 0
        med_spec = statistics.median([r["spec"] for r in rows]) if rows else 0
        phase_tot = []
        for p in range(1, n + 1):
            ph = [x for r in rows for x in r["phases"] if x["p"] == p]
            phase_tot.append({"p": p, "tp": sum(x["tp"] for x in ph), "gp": sum(x["gp"] for x in ph),
                              "waves": sum(x["waves"] for x in ph), "att": sum(x["att"] for x in ph),
                              "spec": sum(x["spec"] for x in ph), "deployed": sum(x["dep"] for x in ph),
                              "partial": sum((not x["dep"]) and x["gp"] > 0 for x in ph),
                              "none": sum(x["gp"] <= 0 for x in ph), "max_waves": maxw[p - 1], "estimated": est[p - 1],
                              "wave_pct": round(sum(x["waves"] for x in ph) / (maxw[p - 1] * len(ph)) * 100, 1) if ph else 0})
        for r in rows:
            r["wave_pct"] = round(r["waves"] / total_max * 100, 1) if total_max else 0
        med_wave = statistics.median([r["wave_pct"] for r in rows]) if rows else 0
        ranked = sorted(rows, key=lambda r: -r["tp"])
        rank = {r["name"]: k + 1 for k, r in enumerate(ranked)}
        for r in rows:
            r["full_deploys"] = sum(x["dep"] for x in r["phases"])
            r["rank"] = rank[r["name"]]
            key = B.norm(r["name"])
            people.setdefault(key, {"name": r["name"], "hist": {}})
            people[key]["name"] = r["name"]
            people[key]["hist"][i] = r
        tbs_out.append({
            "id": t["date"].isoformat(), "date": t["date"].isoformat(), "label": t["label"], "file": t["file"],
            "phases": n, "max_waves": maxw, "members": len(rows),
            "tp": sum(r["tp"] for r in rows), "platoons": sum(r["platoons"] for r in rows),
            "waves": sum(r["waves"] for r in rows), "att": sum(r["att"] for r in rows),
            "spec": sum(r["spec"] for r in rows), "rogue": sum(r["rogue"] for r in rows),
            "wave_pct": round(sum(r["waves"] for r in rows) / (total_max * len(rows)) * 100, 1) if rows else 0,
            "all_deployed": sum(r["full_deploys"] == n for r in rows),
            "no_combat": sum(r["waves"] == 0 for r in rows),
            "median_tp": med_tp, "median_platoons": med_pl, "median_spec": med_spec, "median_wave_pct": med_wave,
            "phase": phase_tot,
        })

    latest_i = len(tbs) - 1
    lt = tbs_out[-1]
    in_latest = {k for k, v in people.items() if latest_i in v["hist"]}
    players = []
    for key, pinfo in people.items():
        hist = pinfo["hist"]
        series = [hist[i]["tp"] if i in hist else None for i in range(len(tbs))]
        played = [v for v in series if v]
        last_r = hist.get(latest_i)
        prev_r = next((hist[i] for i in range(latest_i - 1, -1, -1) if i in hist), None)
        tpct, tlabel = B.trend_of(played[-trend_n:], trend_thr)
        status, focus, tags = None, [], []
        if last_r:
            n = lt["phases"]
            missed = [x for x in last_r["phases"] if not x["dep"]]
            none = [x["p"] for x in missed if x["gp"] <= 0]
            part = [x["p"] for x in missed if x["gp"] > 0]
            if last_r["tp"] <= 0 or (last_r["full_deploys"] == 0 and last_r["waves"] == 0):
                status = "inactive"
            elif len(missed) >= 2 or last_r["wave_pct"] < 0.5 * lt["median_wave_pct"]:
                status = "partial"
            else:
                status = "active"
            if none:
                focus.append(f"Didn't deploy at all in {fmt_ph(none)}"); tags.append("No deploy " + ",".join(f"P{p}" for p in none))
            if part:
                focus.append(f"Only partly deployed in {fmt_ph(part)}"); tags.append("Part deploy " + ",".join(f"P{p}" for p in part))
            if last_r["wave_pct"] < 0.75 * lt["median_wave_pct"]:
                worst = sorted(last_r["phases"], key=lambda x: x["waves"] / lt["max_waves"][x["p"] - 1])[:2]
                focus.append(f"Combat missions: {int(last_r['waves'])} of {int(sum(lt['max_waves']))} waves "
                             f"({last_r['wave_pct']:.0f}% vs guild median {lt['median_wave_pct']:.0f}%), weakest in {fmt_ph(sorted(x['p'] for x in worst))}")
                tags.append(f"Combat {last_r['wave_pct']:.0f}%")
            if last_r["platoons"] == 0:
                focus.append("No platoon units placed"); tags.append("No platoons")
            elif lt["median_platoons"] and last_r["platoons"] < lt["median_platoons"] / 2:
                focus.append(f"Few platoon units ({int(last_r['platoons'])} vs guild median {int(lt['median_platoons'])})"); tags.append("Few platoons")
            if last_r["spec"] == 0 and lt["median_spec"] > 0:
                focus.append("No special missions attempted"); tags.append("No specials")
            if tlabel == "declining":
                focus.append(f"Territory points falling {abs(tpct):.0f}% per TB"); tags.append("Falling")
        players.append({
            "id": key, "name": pinfo["name"],
            "current": key in current_norm if current_norm else key in in_latest,
            "tp": series,
            "waves": [hist[i]["waves"] if i in hist else None for i in range(len(tbs))],
            "wave_pct": [hist[i]["wave_pct"] if i in hist else None for i in range(len(tbs))],
            "platoons": [hist[i]["platoons"] if i in hist else None for i in range(len(tbs))],
            "full_deploys": [hist[i]["full_deploys"] if i in hist else None for i in range(len(tbs))],
            "detail": {str(i): {k: v for k, v in hist[i].items() if k != "name"} for i in hist},
            "last": last_r["tp"] if last_r else None, "prev": prev_r["tp"] if prev_r else None,
            "delta_pct": round((last_r["tp"] - prev_r["tp"]) / prev_r["tp"] * 100, 1) if last_r and prev_r and prev_r["tp"] else None,
            "best": max(played) if played else None,
            "avg": sum(played[-trend_n:]) / len(played[-trend_n:]) if played else None,
            "tbs_played": len(played), "trend": tlabel, "trend_pct": tpct,
            "status": status, "focus": focus, "tags": tags, "rank": last_r["rank"] if last_r else None,
        })
    players.sort(key=lambda p: (-(p["last"] or 0), p["name"].lower()))
    cur = [p for p in players if p["current"] and p["status"]]
    return {"tbs": tbs_out, "players": players, "trend_over_last": trend_n,
            "status": {s: sum(p["status"] == s for p in cur) for s in ("active", "partial", "inactive")},
            "max_waves_from_config": bool(cfg_max)}


def fmt_ph(ps: list[int]) -> str:
    ps = [f"P{p}" for p in ps]
    return ps[0] if len(ps) == 1 else ", ".join(ps[:-1]) + " and " + ps[-1]
