"""
Potential raid score: the best score a member's roster could reach, from the squads and tiers in a raid's
definition (raids/<raid>.yml, under "potential:").

How it works, for each member:
  * Each character is given the highest tier it meets (e.g. R8 -> Tier 5). A squad is only as good as its
    weakest character, so a squad's tier is the lowest tier among its five.
  * Each squad is its lead plus the best of the characters listed for it. Five characters are needed for
    Tier 2 and up; a short squad (fewer than five) can only be used on the tiers in short_max_tier and below.
  * A character can only be used once, so the best set of attempts (5 for Droid Destruction) is chosen
    across the squads without reusing anyone.
  * The potential score is the points of each chosen attempt's tier, added up.
These are the points for clearing each tier, so the potential is a ceiling: what the roster allows,
not what the member will score.
"""
from __future__ import annotations

from itertools import permutations


def _norm(s) -> str:
    return "".join(ch for ch in str(s or "").upper() if ch.isalnum())


def load_config(cfg: dict) -> dict | None:
    pc = (cfg or {}).get("potential") or {}
    tiers, squads = [], []
    for t in pc.get("tiers") or []:
        try:
            tiers.append({"tier": int(t["tier"]), "points": float(t["points"]),
                          "stars": int(t.get("stars") or 0), "gear": int(t.get("gear") or 0),
                          "relic": int(t["relic"]) if t.get("relic") is not None else None})
        except (KeyError, TypeError, ValueError):
            continue
    tiers.sort(key=lambda t: t["tier"])
    for s in pc.get("squads") or []:
        if not s.get("lead"):
            continue
        squads.append({"name": str(s.get("name") or s["lead"]), "lead": _norm(s["lead"]),
                       "pool": [_norm(x) for x in s.get("pool") or [] if x]})
    if not tiers or not squads:
        return None
    return {"attempts": int(pc.get("attempts") or 5), "size": int(pc.get("squad_size") or 5),
            "short_max_tier": int(pc.get("short_max_tier", 1)), "tiers": tiers, "squads": squads,
            "max": max(t["points"] for t in tiers) * int(pc.get("attempts") or 5),
            "good_pct": float(pc.get("good_pct", 75)), "ok_pct": float(pc.get("ok_pct", 50))}


def char_tier(lv: tuple | None, tiers: list[dict]) -> int:
    """The highest tier this character meets, or -1. lv = (stars, gear, relic)."""
    if not lv:
        return -1
    stars, gear, relic = lv
    best = -1
    for t in tiers:
        if t["relic"] is not None:
            ok = (gear or 0) >= 13 and (relic or 0) >= t["relic"]
        elif t["gear"]:
            ok = (gear or 0) >= t["gear"]
        else:
            ok = (stars or 0) >= (t["stars"] or 1)
        if ok:
            best = t["tier"]
    return best


def potential_for(levels: dict | None, pc: dict | None) -> dict | None:
    """levels: {BASEID: (stars, gear, relic)} for one member."""
    if not levels or not pc:
        return None
    lv = {_norm(k): v for k, v in levels.items()}
    tiers = pc["tiers"]
    points = {t["tier"]: t["points"] for t in tiers}
    ct = {k: char_tier(v, tiers) for k, v in lv.items()}

    def build(sq: dict, used: set) -> dict | None:
        lead = sq["lead"]
        if lead in used or ct.get(lead, -1) < 0:
            return None
        pool = sorted((k for k in dict.fromkeys(sq["pool"]) if k != lead and k not in used and ct.get(k, -1) >= 0),
                      key=lambda k: -ct[k])[: pc["size"] - 1]
        members = [lead] + pool
        tier = min(ct[k] for k in members)
        if len(members) < pc["size"]:
            tier = min(tier, pc["short_max_tier"])
        if tier not in points:
            return None
        return {"squad": sq["name"], "tier": tier, "points": points[tier], "members": members,
                "weakest": min(members, key=lambda k: ct[k])}

    best, best_total = [], -1.0
    squads = pc["squads"]
    n = min(pc["attempts"], len(squads))
    for order in permutations(range(len(squads)), n):
        # greedy: each squad in turn takes its best available characters
        used, picks, total = set(), [], 0.0
        for i in order:
            b = build(squads[i], used)
            if b:
                picks.append(b)
                used.update(b["members"])
                total += b["points"]
        if total > best_total or (total == best_total and len(picks) > len(best)):
            best, best_total = picks, total
    best.sort(key=lambda b: -b["points"])
    return {"score": int(best_total), "pct": round(best_total / pc["max"] * 100, 1) if pc["max"] else 0.0,
            "attempts": [{"squad": b["squad"], "tier": b["tier"], "points": int(b["points"]),
                          "members": b["members"], "weakest": b["weakest"]} for b in best]}
