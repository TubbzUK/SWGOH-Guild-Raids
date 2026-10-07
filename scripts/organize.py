#!/usr/bin/env python3
"""
Files uploads so every raid keeps its own file, for every guild in guilds/.

Where files can be uploaded:
  guilds/<guild>/<raid>/     a raid export for that raid (e.g. guilds/oanr/order-66/)
  guilds/<guild>/            a raid export (the raid is recognised from the file name, see
                             file_names in raids/*.yml) or a roster export (recognised from its columns)
  guilds/<guild>/roster/     a roster export

What it does:
  * moves loose files into roster/ or the right raid folder;
  * renames raid files to '<raid date> <raid name>.csv' from the Date inside the file, so the
    next 'Order66_Raid_1.csv' never overwrites the last one. Same date = replaced (a correction);
  * keeps only the newest roster (old ones stay in git history).

    python scripts/organize.py                      # just file everything
    python scripts/organize.py --new "<paths>"      # also report which guild/raid got a NEW raid file
With --new it writes 'post=<guild>/<raid> ...' to $GITHUB_OUTPUT for the Discord step.
"""
import argparse
import datetime as dt
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

DATED = re.compile(r"^\d{4}-\d{2}-\d{2}( |$)")


def safe(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "", s).strip() or "Raid"


def is_roster(path: Path) -> bool:
    """Roster exports have a unit column (BaseId) and a relic column; raid exports don't."""
    try:
        raw = build.read_raw(path)
    except Exception as e:  # unreadable: leave it for the build to report
        print(f"Couldn't read {path.name}: {e}")
        return False
    df = build.with_header(raw, build.NAME_KEYS + build.ALLY_KEYS)
    if df is None:
        return False
    return bool(build.find_col(df, build.UNIT_KEYS) and build.find_col(df, build.RELIC_KEYS))


def organize_guild(gdir: Path, defs: list[dict], log: list[str]) -> dict[str, str]:
    """Returns {uploaded path: final path} for every raid file it moved or renamed (repo-relative)."""
    build.use_guild(gdir)
    cfg = build.load_config()
    day_first = cfg.get("date_format", "dmy").lower() != "mdy"
    rel = lambda p: p.relative_to(build.ROOT).as_posix()  # noqa: E731
    moves: dict[str, str] = {}

    # 1) loose files in the guild folder -> roster/, tb/ or a raid folder
    import tb as TB
    for path in build.data_files(gdir):
        if TB.is_tb_file(path):
            (gdir / "tb").mkdir(exist_ok=True)
            dest = gdir / "tb" / path.name
        elif is_roster(path):
            build.ROSTER_DIR.mkdir(exist_ok=True)
            dest = build.ROSTER_DIR / path.name
        else:
            rdef = build.raid_for_filename(path.name, defs)
            if rdef is None:
                rdef = next((d for d in defs if d["slug"] == cfg.get("current_raid")), None)
            if rdef is None:
                build.warn(f"{gdir.name}/{path.name}: can't tell which raid this is - "
                           f"upload it into the raid's folder instead (e.g. {gdir.name}/{defs[0]['slug'] if defs else 'order-66'}/)")
                continue
            (gdir / rdef["slug"]).mkdir(exist_ok=True)
            dest = gdir / rdef["slug"] / path.name
            moves[rel(path)] = rel(dest)
        if dest.exists():
            dest.unlink()
        path.replace(dest)
        log.append(f"{gdir.name}: {path.name} -> {dest.parent.name}/")

    # 2) raid files without a date in the name -> '<date> <raid name>.ext'
    for d in defs:
        rdir = gdir / d["slug"]
        for path in build.data_files(rdir):
            if DATED.match(path.stem):
                continue
            info = build.read_raid_file(path, day_first)
            if not info:
                continue
            target = path.with_name(f"{info['date'].isoformat()} {safe(d['name'])}{path.suffix.lower()}")
            for old in build.data_files(rdir):
                if old != path and old.stem == target.stem:
                    old.unlink()
            path.replace(target)
            for k, v in moves.items():
                if v == rel(path):
                    moves[k] = rel(target)
            moves.setdefault(rel(path), rel(target))
            log.append(f"{gdir.name}/{d['slug']}: {path.name} -> {target.name}")

    # 3) TB exports without a date in the name -> '<today> RotE.ext'
    tb_dir = gdir / "tb"
    for path in build.data_files(tb_dir) if tb_dir.exists() else []:
        if DATED.match(path.stem):
            continue
        target = path.with_name(f"{dt.date.today().isoformat()} RotE{path.suffix.lower()}")
        if target.exists():
            target.unlink()
        path.replace(target)
        log.append(f"{gdir.name}/tb: {path.name} -> {target.name}")

    # 4) newest roster only, dated today
    today = dt.date.today().isoformat()
    new_rosters = [p for p in build.data_files(build.ROSTER_DIR) if not DATED.match(p.stem)]
    if new_rosters:
        newest = max(new_rosters, key=lambda p: p.stat().st_mtime)
        target = newest.with_name(f"{today} roster{newest.suffix.lower()}")
        for old in build.data_files(build.ROSTER_DIR):
            if old != newest:
                old.unlink()
                log.append(f"{gdir.name}: removed older roster {old.name}")
        newest.replace(target)
        log.append(f"{gdir.name}: {newest.name} -> roster/{target.name}")
    return moves


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", default="", help="newline-separated paths added in the last commit")
    args = ap.parse_args()
    added = [a.strip() for a in args.new.splitlines() if a.strip()]

    defs = build.load_raid_defs()
    log: list[str] = []
    post: set[str] = set()
    for gdir in build.guild_dirs():
        moves = organize_guild(gdir, defs, log)
        for a in added:
            final = moves.get(a, a)
            parts = final.split("/")
            # guilds/<guild>/<raid>/<file>
            if (len(parts) == 4 and parts[0] == "guilds" and parts[1] == gdir.name
                    and any(parts[2] == d["slug"] for d in defs)
                    and Path(final).suffix.lower() in build.TABLE_EXTS):
                post.add(f"{gdir.name}/{parts[2]}")

    for line in log:
        print("Filed:", line)
    if not log:
        print("Nothing to file")
    if added:
        print("New raid results for:", " ".join(sorted(post)) or "none")
        out = os.getenv("GITHUB_OUTPUT")
        if out:
            with open(out, "a") as f:
                f.write(f"post={' '.join(sorted(post))}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
