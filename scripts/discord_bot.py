#!/usr/bin/env python3
"""
Discord DMs of each member's own platoon assignments, sent by a bot when each TB phase starts.

Opting in is up to each member: the bot posts one message in the guild's assignments channel
("react ✅ to get your platoons by DM") and only DMs people who reacted. Removing the reaction stops it.
Each Discord account is matched to an in-game name automatically (server nickname, display name or
username equal to the in-game name); officers confirm or fix the rest on the site (Officers → RotE
platoons → Discord DMs), saved in guilds/<guild>/discord-links.json.

Needs:  GitHub secret DISCORD_BOT_TOKEN (one bot for every guild), invited to the guild's server with
        View Channel, Send Messages, Add Reactions and Read Message History; and the guild's
        assignments webhook (<GUILD>_ASSIGN), which tells the bot which channel and server to use.
Keeps:  guilds/<guild>/discord.json - channel, opt-in message, who opted in, automatic matches,
        and who couldn't be DM'd. Only people who opted in are stored.

Called by tb_phase.py; on its own:
    python scripts/discord_bot.py sync          # refresh opt-ins and matches for every guild
    python scripts/discord_bot.py dm oanr 3     # DM phase 3 to everyone opted in (careful: real DMs)
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUILDS = ROOT / "guilds"
API = "https://discord.com/api/v10"
OK = "%E2%9C%85"   # ✅
UA = "DiscordBot (https://github.com/TubbzUK/swgoh-guild-raids, 1.0)"


def bot_token() -> str:
    try:
        secrets = json.loads(os.getenv("SECRETS_JSON") or "{}")
    except json.JSONDecodeError:
        secrets = {}
    t = next((v for k, v in secrets.items() if k.upper() == "DISCORD_BOT_TOKEN"), None) or os.getenv("DISCORD_BOT_TOKEN") or ""
    return t.strip()


class DiscordError(Exception):
    def __init__(self, status: int, body: dict | str):
        self.status, self.body = status, body
        self.code = body.get("code") if isinstance(body, dict) else None
        super().__init__(f"Discord said {status}: {body}")


def call(method: str, path: str, token: str | None, body=None, tries: int = 4):
    url = path if path.startswith("http") else API + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"User-Agent": UA, **({"Authorization": f"Bot {token}"} if token else {}), **({"Content-Type": "application/json"} if data is not None else {})}
    for attempt in range(tries):
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read().decode() or "null"
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            try:
                b = json.loads(raw)
            except ValueError:
                b = raw
            if e.code == 429 and attempt < tries - 1:       # rate limited: wait as long as Discord asks
                wait = float((b or {}).get("retry_after", 2)) if isinstance(b, dict) else 2
                time.sleep(min(wait, 30) + 0.2)
                continue
            raise DiscordError(e.code, b)
    raise DiscordError(429, "rate limited")


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", str(s or "")).lower())


def load(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def current_members(gdir: Path) -> list[str]:
    """In-game names from the newest roster (the guild as it is now)."""
    import csv
    files = sorted((gdir / "roster").glob("*.csv"))
    if not files:
        return []
    with open(files[-1], encoding="utf-8-sig", newline="") as fh:
        return sorted({(r.get("Name") or "").strip() for r in csv.DictReader(fh) if (r.get("Name") or "").strip()}, key=str.lower)


def auto_match(display_names: list[str], members: list[str]) -> tuple[str | None, bool]:
    """(in-game name, sure). Sure = a name equals the in-game name; unsure = one in-game name inside it."""
    by = {norm(m): m for m in members}
    for d in display_names:
        if norm(d) in by:
            return by[norm(d)], True
    hits = {m for d in display_names for m in members if len(norm(m)) >= 4 and norm(m) in norm(d)}
    return (hits.pop(), False) if len(hits) == 1 else (None, False)


def sync_guild(slug: str, hook: str, token: str) -> bool:
    """Refresh the opt-in message, who opted in and their matches. Returns True if discord.json changed."""
    gdir = GUILDS / slug
    f = gdir / "discord.json"
    st = load(f, {}) or {}
    before = json.dumps(st, sort_keys=True)
    try:
        info = call("GET", hook, None)          # a webhook says which channel and server it posts to
    except DiscordError as e:
        print(f"::warning::{slug}: couldn't read the assignments webhook ({e.status}) - DMs skipped")
        return False
    ch, server = str(info.get("channel_id") or ""), str(info.get("guild_id") or "")
    if not ch:
        return False
    if st.get("channel_id") != ch:
        st.pop("optin_message_id", None)
    st["channel_id"], st["server_id"] = ch, server
    mid = st.get("optin_message_id")
    if mid:
        try:
            call("GET", f"/channels/{ch}/messages/{mid}", token)
        except DiscordError as e:
            if e.status == 404:
                mid = None
            elif e.status == 403:
                print(f"::warning::{slug}: the bot can't see the assignments channel - give it View Channel and Read Message History there")
                return False
    if not mid:
        try:
            m = call("POST", f"/channels/{ch}/messages", token, {
                "content": "📬 **Want your platoon assignments by DM?** React ✅ to this message and you'll get your own list "
                           "privately when each territory battle phase starts. Remove the reaction to stop.\n"
                           "-# Your Discord name is matched to your in-game name; if it doesn't match, an officer links it for you.",
                "allowed_mentions": {"parse": []}})
            mid = m["id"]
            call("PUT", f"/channels/{ch}/messages/{mid}/reactions/{OK}/@me", token)
            print(f"{slug}: posted the DM opt-in message in the assignments channel")
        except DiscordError as e:
            print(f"::warning::{slug}: couldn't post the DM opt-in message ({e.status}) - check the bot is in the server "
                  f"and can Send Messages and Add Reactions in the assignments channel")
            return False
        st["optin_message_id"] = mid
    # who reacted ✅ (the bot's own reaction aside)
    users, after = [], None
    while True:
        try:
            page = call("GET", f"/channels/{ch}/messages/{mid}/reactions/{OK}?limit=100" + (f"&after={after}" if after else ""), token)
        except DiscordError as e:
            print(f"::warning::{slug}: couldn't read the opt-in reactions ({e.status})")
            return False
        users += [u for u in page if not u.get("bot")]
        if len(page) < 100:
            break
        after = page[-1]["id"]
    old = st.get("optin") or {}
    optin = {}
    for u in users:
        uid = str(u["id"])
        rec = dict(old.get(uid) or {})
        rec.update({"user": u.get("username") or "", "name": u.get("global_name") or u.get("username") or ""})
        if "nick" not in rec and server:                 # server nickname, looked up once per person
            try:
                rec["nick"] = (call("GET", f"/guilds/{server}/members/{uid}", token) or {}).get("nick") or ""
            except DiscordError:
                rec["nick"] = ""
        optin[uid] = rec
    st["optin"] = optin
    members = current_members(gdir)
    auto = {}
    for uid, rec in optin.items():
        m, sure = auto_match([rec.get("nick"), rec.get("name"), rec.get("user")], members)
        if m:
            auto[uid] = {"player": m, "sure": sure}
    st["auto"] = auto
    st["members"] = len(members)
    changed = json.dumps(st, sort_keys=True) != before
    if changed:
        f.write_text(json.dumps(st, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        print(f"{slug}: {len(optin)} opted in to DMs, {len(auto)} matched automatically")
    return changed


def links(slug: str) -> dict[str, str]:
    """Discord id -> in-game name, for everyone opted in: an officer's link wins, then a sure automatic match."""
    gdir = GUILDS / slug
    st = load(gdir / "discord.json", {}) or {}
    officer = (load(gdir / "discord-links.json", {}) or {}).get("links") or {}
    out = {}
    for uid in st.get("optin") or {}:
        if uid in officer:
            if officer[uid]:
                out[uid] = officer[uid]
        elif (st.get("auto") or {}).get(uid, {}).get("sure"):
            out[uid] = st["auto"][uid]["player"]
    return out


def dm_phase(slug: str, phase: int, token: str, title: str, link: str = "") -> tuple[int, int]:
    """DM each opted-in, linked member their own phase assignments. Returns (sent, failed)."""
    import tb_phase
    gdir = GUILDS / slug
    st = load(gdir / "discord.json", {}) or {}
    failed = st.setdefault("dm_failed", {})
    sent = bad = 0
    for uid, player in sorted(links(slug).items(), key=lambda x: x[1].lower()):
        r = tb_phase.phase_text(gdir, phase, player)
        if not r:
            continue
        body = r[0].split("\n\n", 1)[1] if "\n\n" in r[0] else r[0]
        text = f"## {title}\n{body}" + (f"\n\n[Open the planner](<{link}>)" if link else "")
        try:
            chan = call("POST", "/users/@me/channels", token, {"recipient_id": uid})
            call("POST", f"/channels/{chan['id']}/messages", token, {"content": text[:1990], "allowed_mentions": {"parse": []}, "flags": 4})
            failed.pop(uid, None)
            sent += 1
        except DiscordError as e:
            failed[uid] = "DMs closed" if e.code == 50007 else f"error {e.status}"
            bad += 1
        time.sleep(0.6)
    (gdir / "discord.json").write_text(json.dumps(st, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return sent, bad


def main() -> int:
    import tb_phase
    token = bot_token()
    if not token:
        print("No DISCORD_BOT_TOKEN secret - Discord DMs are off")
        return 0
    if sys.argv[1:2] == ["dm"] and len(sys.argv) >= 4:
        s, b = dm_phase(sys.argv[2], int(sys.argv[3]), token, f"{tb_phase.guild_name(sys.argv[2])} · your RotE phase {sys.argv[3]} platoons")
        print(f"sent {s}, failed {b}")
        return 0
    for gdir in sorted(p for p in GUILDS.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
        _, hook = tb_phase.webhook(gdir.name)
        if hook:
            sync_guild(gdir.name, hook, token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
