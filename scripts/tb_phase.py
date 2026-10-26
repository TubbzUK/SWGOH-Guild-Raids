#!/usr/bin/env python3
"""
Posts each Rise of the Empire phase's platoon assignments to Discord as text (one block per member,
so people can search for their name), automatically, as soon as each phase starts.

When does a phase start? From guilds/<guild>/tb-schedule.json:
    "manual": {"start": "2026-10-27T17:30:00Z", "phases": 6, "hours": 24}   one TB, set by an officer on the site
    "repeat": {"start": "2026-10-26T17:00:00Z", "every_days": 14, ...}      a TB every 14 days from that start
    "game":   {"start": ..., "end": ..., "id": ...}                         read from the game by sync_game.py
An officer's one-off time wins, then the repeating one, then the game's. Phase N starts at start + (N-1) x hours.

What gets posted? The saved assignments (guilds/<guild>/platoons.json, from the planner's Save and share).
Where? The guild's assignments webhook: GitHub secret <GUILD>_ASSIGN (e.g. OANR_ASSIGN), or the name in
config.yml under discord_assign_secret. What's been posted is kept in guilds/<guild>/tb-posts.json so
nothing is posted twice.

    python scripts/tb_phase.py                 # post any phase that has started and not been posted
    python scripts/tb_phase.py --dry-run       # print what would be posted
    python scripts/tb_phase.py --phase oanr 3  # build the text for one guild and phase (prints it)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUILDS = ROOT / "guilds"
LATE_HOURS = 20          # don't post a phase that started more than this long ago (missed runs, old TBs)


def load(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def when(v) -> dt.datetime | None:
    if v in (None, ""):
        return None
    try:
        n = float(v)
        return dt.datetime.fromtimestamp(n / 1000 if n > 1e11 else n, dt.timezone.utc)
    except (TypeError, ValueError):
        pass
    try:
        d = dt.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def schedule(gdir: Path) -> dict | None:
    """{'start': datetime, 'phases': 6, 'hours': 24, 'source': 'officer'|'game', 'id': ...} or None."""
    s = load(gdir / "tb-schedule.json", {}) or {}
    m = s.get("manual") or {}
    now = dt.datetime.now(dt.timezone.utc)
    if when(m.get("start")) and now < when(m["start"]) + dt.timedelta(hours=float(m.get("hours") or 24) * int(m.get("phases") or 6)):
        return {"start": when(m["start"]), "phases": int(m.get("phases") or 6), "hours": float(m.get("hours") or 24),
                "source": "officer", "id": "manual:" + when(m["start"]).isoformat()}
    r = s.get("repeat") or {}
    if when(r.get("start")) and float(r.get("every_days") or 0) > 0:   # a TB every N days from a known start
        first, period = when(r["start"]), dt.timedelta(days=float(r["every_days"]))
        phases, hours = int(r.get("phases") or 6), float(r.get("hours") or 24)
        k = max(0, int((now - first) / period)) if now >= first else 0
        start = first + k * period
        return {"start": start, "phases": phases, "hours": hours, "source": "every %g days" % float(r["every_days"]),
                "id": "repeat:" + start.isoformat()}
    g = s.get("game") or {}
    if when(g.get("start")):
        start, end = when(g["start"]), when(g.get("end"))
        phases = int(g.get("phases") or 6)
        hours = float(g.get("hours") or ((end - start).total_seconds() / 3600 / phases if end else 24))
        return {"start": start, "phases": phases, "hours": hours, "source": "game", "id": str(g.get("id") or start.isoformat())}
    return None


def current_phase(sch: dict, now: dt.datetime) -> tuple[int, dt.datetime] | None:
    if not sch or now < sch["start"]:
        return None
    n = int((now - sch["start"]).total_seconds() // (sch["hours"] * 3600)) + 1
    if n > sch["phases"]:
        return None
    return n, sch["start"] + dt.timedelta(hours=sch["hours"] * (n - 1))


def phase_text(gdir: Path, phase: int) -> tuple[str, int, int] | None:
    """The phase's assignments as text, one block per member A-Z. Returns (text, members, slots)."""
    st = load(gdir / "platoons.json")
    if not st or not st.get("plan") or not st.get("res"):
        return None
    plan, players = st["plan"], st["players"]
    by: dict[str, list] = {}
    for r in st["res"]:
        i, pi, d = r[0], r[1], (r[4] if len(r) > 4 else 0)
        if pi is None or pi < 0 or d != phase:
            continue
        p = plan[i]
        by.setdefault(players[pi], []).append((p[1], str(p[2]), p[3] if p[3] is not None else 0, p[5]))
    if not by:
        return None
    op_key = lambda o: (float(o) if re.fullmatch(r"\d+(\.\d+)?", o) else 1e9, o)  # noqa: E731
    blocks = []
    for name in sorted(by, key=str.lower):
        items = sorted(by[name], key=lambda x: (x[0], op_key(x[1]), x[2]))
        ops: dict[str, list[str]] = {}
        for planet, op, _row, unit in items:
            ops.setdefault(f"{planet} op {op}", []).append(unit)
        lines = [f"• {k}: {', '.join(v)}" for k, v in ops.items()]
        blocks.append(f"**{name}** ({len(items)})\n" + "\n".join(lines))
    head = (f"RotE phase {phase} platoon assignments · {len(by)} members, "
            f"{sum(len(v) for v in by.values())} units. Search for your name (Ctrl+F) and place these this phase.")
    return head + "\n\n" + "\n\n".join(blocks), len(by), sum(len(v) for v in by.values())


def webhook(slug: str) -> tuple[str, str]:
    import yaml
    cfg = (yaml.safe_load((GUILDS / slug / "config.yml").read_text(encoding="utf-8")) or {}) if (GUILDS / slug / "config.yml").exists() else {}
    name = cfg.get("discord_assign_secret") or re.sub(r"[^A-Z0-9]", "_", slug.upper()) + "_ASSIGN"
    try:
        secrets = json.loads(os.getenv("SECRETS_JSON") or "{}")
    except json.JSONDecodeError:
        secrets = {}
    # secret names aren't case-sensitive on GitHub (OANR_assign is stored as OANR_ASSIGN)
    found = next((v for k, v in secrets.items() if k.upper() == name.upper()), None) or os.getenv(name) or os.getenv(name.upper())
    return name, (found or "").strip()


def post_text(hook: str, title: str, text: str, link: str = "") -> int:
    """Post as plain messages (Discord's search finds names in message text, not in embeds), each up to
    ~1,900 characters, never splitting a member's block."""
    import urllib.request
    parts = [b for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    head = parts.pop(0) if parts and not parts[0].startswith("**") else ""
    first = f"## {title}\n{head}".strip()
    chunks, cur = [], first
    for b in parts:
        b = b if len(b) <= 1900 else b[:1890] + " …"
        if cur and len(cur) + len(b) + 2 > 1900:
            chunks.append(cur)
            cur = ""
        cur = f"{cur}\n\n{b}" if cur else b
    if link and len(cur) + len(link) + 30 <= 1990:
        cur += f"\n\n[Open the planner](<{link}>)"
    if cur:
        chunks.append(cur)
    for c in chunks:
        body = {"content": c, "allowed_mentions": {"parse": []}, "flags": 4}   # 4 = no link previews
        req = urllib.request.Request(hook, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "User-Agent": "swgoh-guild-raids (github actions)"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30):
                    break
            except Exception as e:  # rate limits: wait and retry
                if attempt == 2:
                    raise
                print(f"  Discord said {e} - retrying")
                time.sleep(3 + attempt * 4)
        time.sleep(1.2)
    return len(chunks)


def guild_name(slug: str) -> str:
    try:
        import yaml
        return (yaml.safe_load((GUILDS / slug / "config.yml").read_text(encoding="utf-8")) or {}).get("guild_name") or slug
    except Exception:
        return slug


def main() -> int:
    args = sys.argv[1:]
    if args[:1] == ["--phase"] and len(args) >= 3:
        r = phase_text(GUILDS / args[1], int(args[2]))
        print(r[0] if r else "No assignments for that phase.")
        return 0
    dry = "--dry-run" in args
    now = dt.datetime.now(dt.timezone.utc)
    site = os.getenv("SITE_URL", "").rstrip("/")
    for gdir in sorted(p for p in GUILDS.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
        slug = gdir.name
        sch = schedule(gdir)
        if not sch:
            continue
        cur = current_phase(sch, now)
        if not cur:
            continue
        phase, started = cur
        state_f = gdir / "tb-posts.json"
        state = load(state_f, {}) or {}
        done = state.setdefault(sch["id"], [])
        if phase in done:
            continue
        if (now - started).total_seconds() > LATE_HOURS * 3600:
            print(f"{slug}: phase {phase} started {started:%d %b %H:%M} UTC - too long ago to post now")
            continue
        r = phase_text(gdir, phase)
        if not r:
            print(f"{slug}: phase {phase} has started, but the saved assignments have nothing for it - nothing posted")
            done.append(phase)
            if not dry:
                state_f.write_text(json.dumps(state, indent=1), encoding="utf-8")
            continue
        text, n_mem, n_slots = r
        name, hook = webhook(slug)
        title = f"{guild_name(slug)} · RotE phase {phase} platoons"
        if dry:
            print(f"--- {slug}: would post phase {phase} ({n_mem} members, {n_slots} units) to {name} [{sch['source']} schedule]\n{text[:1500]}…")
            continue
        if not hook:
            print(f"::warning::{slug}: phase {phase} has started but there's no GitHub secret called {name} - "
                  f"add the Discord webhook under Settings > Secrets and variables > Actions")
            continue
        try:
            n = post_text(hook, title, text, f"{site}/platoons.html?guild={slug}" if site else "")
        except Exception as e:
            print(f"::warning::{slug}: posting phase {phase} assignments failed: {e}")
            continue
        done.append(phase)
        state["last"] = {"phase": phase, "posted_at": now.isoformat(timespec="seconds"), "messages": n}
        state_f.write_text(json.dumps(state, indent=1), encoding="utf-8")
        print(f"{slug}: posted phase {phase} assignments ({n_mem} members, {n_slots} units, {n} messages) [{sch['source']} schedule]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
