# SWGOH Guild Statistics

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
    tb/                      ← territory battle results, one file per TB
  endor-legacy/              ← same layout, waiting for its first files
  _template/                 ← starter config for adding more guilds (ignored by the site)
```

## Uploading from the website (easiest)

Click **⬆ Upload results** at the top right of the site (or open `…/upload.html`). Pick the guild,
raid results or roster, and the raid, then drop the file in. The page checks the file first
(right type, raid date, player count, players belong to that guild, file name matches the raid),
uploads it, and shows progress until the site has updated.

Officers log in with the **officer password**, which the repository owner sets up once:

1. Create a fine-grained token at https://github.com/settings/personal-access-tokens/new:
   **Only select repositories →** this repository; **Contents: Read and write**, **Actions: Read-only**.
   Copy it with the copy button (don't screenshot it).
2. On the upload page click **Repository owner: set up or change the officer password**, paste the
   token, choose a password of at least 12 characters (four random words works well) and click
   **Save officer password**.
3. About two minutes later the upload page asks for the password. Share it with officers privately.

The token is locked with the password in your browser (PBKDF2 + AES-256) and only the locked copy
(`site/upload-key.json`) is saved, so the password must be long: anyone can download the locked copy
and try to guess it.

**Changing the password or removing someone's access:** create a new token, run the setup again
with a new password, then delete the old token on GitHub (Settings → Developer settings → Personal
access tokens). Deleting the old token matters, because older locked copies stay in the repository's
history. To stop password uploads completely, just delete the token.

You can also upload with a GitHub token directly (*Use a GitHub token instead* on the upload page).

## After every raid (uploading on GitHub instead)

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

## Platoon planner (Rise of the Empire)

The **⚑ Platoons** page (`…/platoons.html?guild=oanr`) assigns every territory battle platoon slot
across the guild. Everyone can see the saved assignments; officers open **Menu** with the officer
password to choose operations, change the rules, run **Assign platoons** and **Save and share**.

- **Roster:** each guild's latest WookieeBot roster upload, the same one used for raid readiness.
  Upload a fresh roster before planning so relic levels are current.
- **Operations plan:** `guilds/_platoons/rote-plan.csv`, shared by every guild. Replace it from the
  planner's Menu → Data, or upload a new file over it on GitHub.
- **Saved assignments:** `guilds/<guild>/platoons.json`, written by **Save and share**. Members see
  the new assignments about two minutes after saving.
- **Each guild has its own planet and operation choices.** Officers pick them in Menu → Operations
  to fill and press **Save selections** (saved to `guilds/<guild>/platoon-settings.json`). The rules
  (relic minimums, per-member limit, GL rules, tier balancing) are saved there too, per guild.
  **Save and share** also saves the choices the assignments were made with.
- The page shows which planets each guild is filling in each phase, and flags it when the choices
  have changed since the assignments were last made.

## Territory battles

The **◈ Territory battles** page (`…/tb.html?guild=oanr`) tracks how each member does in every
Rise of the Empire TB and how that changes over time.

**After each TB:** on the upload page choose **Territory battle**, set the date the TB ended and drop
in the export (one row per member with `Name`, `Total Territory Points`, `Platoon Units`,
`Combat Waves`, and per phase `P1 Deployed`, `P1 Territory Points`, `P1 Deployed GP`,
`P1 Combat Attempts`, `P1 Special Attempts`, `P1 Waves` …). It's saved as
`guilds/<guild>/tb/<date> RotE.csv`; uploading again with the same date replaces it. You can also
upload into `guilds/<guild>/tb/` on GitHub: name it `2026-10-05 RotE.csv`, or it gets today's date.

- **Overview** – guild territory points per TB, wave completion by phase, platoon units, who fully
  deployed, how many members were active / partial / inactive, a *needs attention* list and the top 10.
- **Members** – everyone's points, change vs their last TB, trend (line of best fit over the last
  5 TBs, same rule as raids), waves completed %, combat mission attempts, platoon units, a square
  per phase for deployment (green full, amber partly, red none) and short *to work on* tags. Click a
  member for their per-phase breakdown and their points and wave % by TB against the guild median.
- **Phases** – one phase at a time: points, GP deployed, waves and CM attempts for every member.
- **Player** – pick a member (or click a name anywhere on the page) for their full summary: a
  one-line verdict (trending up / level / down, what's improving or falling, which phases are getting
  stronger or slipping), six measures with change vs their last TB, trend and guild median, charts
  of points and wave % by TB with a trend line, points and waves by phase for their last 5 TBs, a
  trend table per phase, charts for any one phase over time, rank by TB, CM attempts and platoons by
  TB, and their full TB history. Links can be shared: `…/tb.html?guild=oanr&player=taero#player`.

**How it's judged.** *Waves %* = waves completed ÷ the most a member could complete
(`tb_max_waves` in the guild's `config.yml`; change it if your guild opens different planets).
**Inactive** = no points, or no deployment and no combat at all. **Partial** = missed full deployment
in 2+ phases, or wave % under half the guild median. *To work on* flags phases not deployed or only
partly deployed, combat waves under ¾ of the guild median, few or no platoon units, no special
missions, and falling points.

## TB contribution ranking (for officers)

**★ Contribution** on the Territory Battles page (`…/ranking.html?guild=oanr`) ranks members by a
contribution score from 0 to 100%, overall and for each phase, for one TB or averaged over all TBs.

- **Deployment** – 100% for each phase fully deployed; partly deployed counts the share of GP placed.
- **Combat missions** – waves completed ÷ the most possible in the counted phases (`tb_max_waves`).
- **Special missions** – attempts per phase, where the typical number for those who did them = 100%.
- **Platoons** – platoon units ÷ the guild's top quarter, capped at 100%. The export only has one
  platoon total per TB, so platoons count in the overall score, not the phase columns.

**Score trend by member** shows how many points each member gains or loses per TB (line of best fit
through their overall score, last 5 TBs; ±2 or more counts as getting better or declining). Click a
bar, a ranking bar or a table row to see that member's overall score by TB against the guild median,
each part (deployment, combat, specials, platoons) by TB, and each counted phase by TB.

Officers press **⚙ Officer settings** (officer password) to choose which phases count (e.g. untick
Phase 1) and how much each part is worth. **Preview** changes only their own view; **Save for
everyone** saves to `guilds/<guild>/tb-settings.json` and every member sees it about two minutes
later. Anyone with the link can view the ranking; only officers can change the settings.

## Guild effectiveness (raids + territory battles)

**◎ Effectiveness** (`…/effectiveness.html?guild=oanr`) combines raid and TB performance into one
score per member.

- **Raid score** – in each of the last 5 raids (every raid type with results), the member's score as a
  % of the guild's best score in that raid, averaged. A raid they didn't score in counts as 0 once
  they'd joined.
- **TB contribution** – the overall score from the Contribution page (same phases and weighting the
  officers chose there), averaged over the last 3 TBs. A missed TB counts as 0 once they'd joined.
- **Effectiveness** = raids 50% + TBs 50% by default.

The page shows a raids-vs-TBs chart (strong in both, stronger in one, or below the guild median in
both), a ranking, and a table with each member's raid and TB scores, trends and attendance. Click
a member for their raid scores and TB contribution over time. New members with only raid or only TB
results are listed but not ranked until they have both. Officers can change the weighting and how
many recent raids and TBs count under **⚙ Officer settings** (saved to
`guilds/<guild>/stats-settings.json`).

## Look and feel

The site has a dark space theme and a light theme. Everyone can switch with the **System / Light /
Dark** button at the top right; the choice is remembered on their device.

Each raid has its own banner artwork. To use your own picture instead, upload an image named after
the raid into the `raids/` folder, e.g. `raids/order-66.jpg` or `raids/droid-destruction.png`
(a wide image, about 1200×260 or larger, works best). Only use images you have the right to share.

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

**From the website (easiest):** on the upload page, under *Guild*, click **+ Add a new guild**, type
the guild's name, pick UK or US dates, enter the officer password at step 5 and press
**Create guild**. It creates `guilds/<name>/config.yml` and selects the new guild, so you can upload
its roster (and any raid or TB results) straight away. The guild appears on the site with its first
file. For Discord posts, add the secret it shows (e.g. `DISCORD_WEBHOOK_REBEL_SCUM`) under
**Settings → Secrets and variables → Actions** with the channel's webhook URL.

To rename a guild or change its settings later, edit its `config.yml` on GitHub (pencil icon).
To add one by hand on GitHub instead, see `guilds/_template/README.md`.

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
