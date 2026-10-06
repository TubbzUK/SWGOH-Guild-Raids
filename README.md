# SWGOH Guild Raid Tracker

Drop a WookieeBot raid export into a folder → the website updates itself → a summary posts to that
guild's Discord. No copy-and-paste and no formulas. It does what the raid management workbook did
(guild totals per raid, each player's score history and trend, raid readiness from relic levels)
for several guilds and several raids, with switchers at the top of the site.

```
raids/                       ← one file per raid type, shared by every guild
  order-66.yml               ← name, 3M target, Order 66 readiness characters
  droid-destruction.yml      ← name, target, Droid Destruction readiness characters
guilds/
  oanr/
    config.yml               ← guild name, Discord secret, trend settings
    order-66/                ← OANR's Order 66 results (24 raids from 30 Jun 2025 already in)
    droid-destruction/       ← OANR's Droid Destruction results, when it starts
    roster/                  ← newest WookieeBot roster export (for readiness)
  endor-legacy/              ← same layout, waiting for its first files
  _template/                 ← starter config for adding more guilds (ignored by the site)
```

## After every raid

1. Export the raid results from WookieeBot (e.g. `Order66_Raid_1.csv`).
2. On GitHub open the guild and raid folder, e.g. **guilds → oanr → order-66** →
   **Add file → Upload files** → drop the file in **as it is** → **Commit changes**.

Within about two minutes:
- the file is renamed by the raid date inside it (e.g. `2026-10-06 Order 66.csv`), so next week's
  `Order66_Raid_1.csv` never overwrites this week's;
- the site is rebuilt;
- a summary is posted to that guild's Discord channel (other guilds aren't touched).

Uploading a second file with the same raid date replaces the first (handy for corrections).

Uploading straight into the guild folder (e.g. `guilds/oanr`) also works when the file name contains
the raid name, as WookieeBot's do (`Order66…`, `DroidDestruction…`). If it can't tell, the file is
left where it is and the site's **Data notes** say so; delete it and upload into the raid folder.

**Updating relic levels:** export the guild roster from WookieeBot and upload it into the guild's
folder (e.g. `guilds/oanr`). It's recognised as a roster automatically and replaces the old one.
One roster serves every raid's readiness.

## What the site shows

Pick the guild and the raid at the top right. Each page link includes both
(`…/?guild=oanr&raid=order-66`), so you can share a direct link in each Discord.

**Overview** – guild total per raid, participation, average/median, top 10, who's improving, the
declining watch list, members with no score, and who scored under the target.

**Players** – every member with latest score, change vs their previous raid, trend, a sparkline of
recent raids, average of their last 5, best, actual vs WookieeBot's estimate, raids played, readiness.
Click a player to see their whole history against the guild average and the target.

**Readiness** – each player's relic level on every character the raid needs, coloured from
not unlocked → relicked → at R10, plus the guild's average relic per character. A raid with no
results yet (Droid Destruction for now) opens straight on this tab.

### How the numbers are worked out

| | |
|---|---|
| **Score** | `lastActualScore` from the WookieeBot file. `estimatedScore` is shown as "vs estimate". |
| **Raid date** | the `Date` column in the file (UK day/month/year). |
| **Trend** | the line of best fit through a player's last 5 scores in that raid, as % change per raid. +3% or more = **Improving**, −3% or less = **Declining**, otherwise **Level**. Fewer than 3 scores = **New**. Set in the guild's `config.yml`. |
| **Avg (last 5)** | average of their last 5 raids where they scored above zero. |
| **Readiness %** | sum of relic levels across the raid's characters ÷ (characters × 10). Not unlocked or not relicked counts as 0. Ready / Close / Building bands are set in the raid's `.yml`. |
| **Current members** | whoever is in the newest WookieeBot file for that guild (any raid, or the roster if that's newer). Anyone else shows as "left". |

## One-time setup (about 10 minutes)

1. **Create the repo.** On github.com: **New repository** → name it e.g. `guild-raids` → **Public**
   → Create. Then **uploading an existing file** → drag in everything from this folder, including
   the hidden `.github` folder (on a Mac press `Cmd+Shift+.` to show it; GitHub Desktop is easier).
2. **Turn on the website.** Repo **Settings → Pages → Source: GitHub Actions**.
3. **Let it file uploads.** **Settings → Actions → General → Workflow permissions →
   Read and write permissions** → Save.
4. **Connect Discord** (one webhook per guild). In Discord: channel **Edit Channel → Integrations →
   Webhooks → New Webhook** → **Copy Webhook URL**. In GitHub: **Settings → Secrets and variables →
   Actions → New repository secret**. Use the name from that guild's `config.yml`
   (`discord_secret`): `DISCORD_WEBHOOK_OANR` for OANR and `DISCORD_WEBHOOK_ENDOR_LEGACY` for
   Endor Legacy. Paste the URL and save.
5. **Run it once.** **Actions** tab → *Update raid site* → **Run workflow**. The site appears at
   `https://<your-github-name>.github.io/<repo-name>/`.

Discord posts only when a **new raid file** is uploaded, and only for that guild; roster and settings
changes update the site quietly. To re-post each guild's latest raid: Actions → *Update raid site* →
Run workflow → tick *Post to Discord*.

**Letting your friend upload Endor Legacy's files:** **Settings → Collaborators → Add people** → their
GitHub username. Collaborators can upload to any guild's folder, so only add people you trust.
A guild doesn't appear on the site until it has at least one file.

## Adding a raid

When a new raid arrives, create `raids/<short-name>.yml` (copy `droid-destruction.yml` and change the
name, `file_names`, target and characters). Then upload results into the guild folder: files whose
name matches `file_names` are moved into `guilds/<guild>/<short-name>/` automatically. (To make the
folder by hand: in the guild folder **Add file → Create new file**, name it `<short-name>/README.md`.)

## Changing readiness characters or targets

Edit the raid's file in `raids/` on GitHub (pencil icon). Characters use the **BaseId** from the
roster export (e.g. `VADERDUELSEND`). To show a friendlier name or use a lower target than R10:

```yaml
    - id: VADERDUELSEND
      label: "Vader (Duel's End)"
      relic: 9
```

A guild can have its own target score for a raid in its `config.yml` under `target_scores`.

## Adding another guild

See `guilds/_template/README.md`.

## If something looks wrong

The yellow **Data notes** bar on the site lists anything the build couldn't read (a file with no
date, a file it couldn't match to a raid, a readiness character nobody has in their roster, a player
listed twice). The full log is under the **Actions** tab.

## Preview on your own computer (optional)

```
pip install -r requirements.txt
python scripts/organize.py
python scripts/build.py
python -m http.server -d site 8000
```
then open http://localhost:8000
