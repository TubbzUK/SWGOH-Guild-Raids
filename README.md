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

## The side menu

Every page has a menu down the left-hand side with everything in one place:

- **Pages**, as a tree: click a page to open its sections underneath, then click a section to go
  straight to it (the page you're on starts open, with the section you're on highlighted):
  - Raids → Overview, Players, Readiness
  - Player status
  - Guild overview → Stats, Roster, Abilities
  - Territory battles → Overview, Members, Phases, Player, TB contribution
  - Territory wars → Overview, Members
  - Guild effectiveness → Overview, Raids vs TBs, Ranking, Members, How it's worked out
  - RotE platoons → Assignments, Summary, Requirements, Missing platoons, Simulate, Toon lookup

  Sections have their own links that can be shared (e.g. `…/platoons.html?guild=oanr#toon`,
  `…/tb.html?guild=oanr#members`), and links keep the guild you're looking at. In the folded icon
  strip, clicking a page's icon just opens that page.
- **Officers**, as a tree that's the same on every page. Pick a tool from anywhere: if it lives on
  another page, that page opens and the tool starts straight away.
  - 📣 Post to Discord → Raid results, Raid readiness, TB stats, TW stats, Guild effectiveness
    (officers' channel), Platoons: one phase, Platoons: whole guild
  - Raids → Score targets
  - Territory battles → Manage TB uploads, Set TB stars, Contribution settings
  - Territory wars → Set the TW result
  - Guild effectiveness → Effectiveness weighting
  - RotE platoons → Planner data, Operations to fill, Rules
  - Pull from the game now, and *Forget my officer login* for a shared computer

  They all ask for the officer password.
- **Upload**: upload a WookieeBot file (for the page you're on) and *Add a new guild*.
- **Theme**: System, Light or Dark, at the bottom.

The arrow at the top folds it down to a narrow strip of icons (hover for names) and back; each
device remembers your choice. On a phone it's tucked away behind the ☰ button at the top left.

## Player status

`player.html` (Player status in the side menu) is for members. Pick your name - the site remembers it on
that device - for your overall score and a score for each area:

- **Raids**: your score as a % of the guild's best in each of the last raids, plus your readiness for
  each raid.
- **Territory battles**: your TB contribution (deployment, combat and special missions, platoons).
- **Territory wars**: your banners as a % of the guild's best.

Below that is the member's **full roster**: GP, counts (GLs, R9+, R7+, G13, 7★ ships) and every character and ship with stars, relic or gear level and power, with search, sorting and a light/dark filter. **Zetas** and **Omicrons** buttons switch the roster to the member's upgraded abilities: one card per unit listing each zeta, and each omicron with its game mode (TW, TB, GAC, Raid, Conquest...), with a game-mode filter for omicrons. Ability names need the guild connected to the game; an uploaded WookieeBot roster gives the counts only. It comes from the latest roster (uploaded or pulled from the game); unit names come from the platoon plan and scripts/unit-names.csv.

Each shows your rank, the guild median and whether you're rising, steady or falling. Tap one for its
history: charts against the guild median, phase by phase for TBs, and a table of every event. The
scoring and weights are the same as the Guild effectiveness page. A link straight to someone's page:
`player.html?guild=oanr&player=<name>`.

## Pulling data from the game (no uploads)

Give a guild any member's ally code and the site fetches its data from the game itself every 4 hours,
through SWGoH Comlink (a free community tool that reads the game's public data; it runs inside the
GitHub Action, so there's nothing to host):

- **Roster** - every member's units, stars, gear and relics, plus GP (once a day, again within 4 hours whenever someone joins or leaves, and straight away with *Pull from the game now*). Readiness and the
  platoon planner stay current without roster uploads.
- **Raid scores** - each member's score in the guild's latest finished raid of each type, added as a
  new raid (and posted to Discord like an upload). The game only shows the latest raid, which is why it
  checks every 4 hours. A raid already uploaded for that date is left alone.
- **TW results** - win or loss and both scores for recent territory wars (a result an officer entered
  is never changed).

TB stats and TW banners per member aren't available from the game, so those still come from WookieeBot
uploads, and uploads of anything else still work as before.

**Connecting a guild:** side menu → Upload → **🔗 Connect a guild to the game**, pick the guild and enter
an ally code (or fill in the ally code when adding a new guild). It's saved as `ally_code:` in the
guild's config.yml; clear it to disconnect. **🔄 Pull from the game now** (Officers) fetches straight
away instead of waiting. To pull by hand on GitHub: Actions → Update raid site → Run workflow.

If the Action log warns about a raid ID that doesn't match, add it to that raid's file in raids/, e.g.
`game_ids: ["the_id_from_the_warning"]`. New ships are learned from WookieeBot rosters or can be added
to scripts/ships.txt.

On the raid page's **Readiness** tab, pick a member at the top (or click their row in the table, or
step through with ‹ ›) and the character cards switch from guild averages to that member's own relic
on each character: what they have, the target, how many relic levels to go, and the guild average for
comparison. Pick *Whole guild* to go back.

## Unit names and pictures

Character and ship portraits (on the raid readiness tab and in each member's roster on Player status)
and unit names come from the game itself (through Comlink); the site update saves the list in
`scripts/units.json` when it pulls from the game (and on the first run); the pictures themselves are
shown straight from swgoh.gg's image server, nothing is copied. The list is refreshed weekly, or when a
roster has a unit it doesn't know; if that fails the last list is kept, and without one the site shows
initials instead of pictures. The game artwork belongs to
EA and Lucasfilm.

## Uploading from the website (easiest)

Open **Upload** in the side menu on any page (or open `…/upload.html`). Pick the guild,
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
| **Current members** | whoever is in the newest file for that guild (any raid, or the roster if it is as new or newer - for a guild connected to the game that is the roster pulled from the game). Anyone else shows as "left". |

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

Each post includes a picture of the results panel (`site/card.html`: banner, totals, a chart of the last 10 raids, top 10, biggest jumps, the declining watch list and who didn't score), taken automatically on GitHub. If the picture can't be made, the text summary is posted instead.

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
across the guild. Everyone can see the saved assignments; officers open **Officers → ⚙ Platoon planner in the side menu** with the officer
password to choose operations, change the rules, run **Assign platoons** and **Save and share**.

- **Roster:** each guild's latest WookieeBot roster upload, the same one used for raid readiness.
  Upload a fresh roster before planning so relic levels are current.
- **Operations plan:** `guilds/_platoons/rote-plan.csv`, shared by every guild. Replace it from the
  side menu → ⚙ Platoon planner: data, or upload a new file over it on GitHub.
- **Saved assignments:** `guilds/<guild>/platoons.json`, written by **Save and share**. Members see
  the new assignments about two minutes after saving.
- **Missing platoons** lists everything the chosen operations are short of: each unit, the level needed,
  how many more members need it, which operations it blocks, and the members closest to getting there
  (with how many relic levels or stars they have to go). Each one has a box per member needed, so people
  can sign up by picking their name (closest first). Officers press **Save sign-ups** to share them
  (saved to guilds/<guild>/platoon-pledges.json); once a signed-up member's roster reaches the level it
  shows ✓ done. **Copy sign-ups for Discord** gives a ready-to-paste list.
- **Toon lookup**: pick a character or ship (with a filter box) to see every planet and operation it's in
  (copies, level needed, which phase it's filled in), then the members who have it ready (and where
  they're placed), those one level away, everyone marked for deployment with it in the plan, and those
  further below. When it's needed at several levels (e.g. R6 early, R9 on later planets), buttons switch
  which level the members are checked against.
- **Simulate** (button next to Missing platoons) plays the TB through phase by phase with the roster and
  rules: each phase it keeps the set of open operations the guild can fill completely and holds the rest
  for a later phase, then shows the suggested order, the operations nobody can fill yet (and why), and
  the upgrades that would close those gaps. Officers can press **Use this schedule** to apply it.
- On **Requirements**, click a character to open a card under its row: every member who has it at the
  required level or above, with their level and where the plan has them placing it (phase, planet,
  operation and row - this phase highlighted), or "Not placing it". A second section lists everyone one
  level below (one relic level, or one star for ships) who could upgrade quickly and fill it; members
  further below and those without it are listed underneath. Click again (or ✕) to close.
- **Squads stay together.** With *Keep squads together* on (Platoon planner: rules, on by default),
  whoever is given a squad's lead unit - Executor, say - also gets that squad's other units needed in
  the same phase, as far as they own them, so nobody else loses their fleet. The squads list is preset
  with common fleets and can be edited (lead: unit, unit, ... one per line; character squads work too).
  Those slots show a "with Executor" tag.
- **Character squads stay together** the same way (*Keep character squads together*, on by default):
  whoever is given a squad's leader - a GL such as Supreme Leader Kylo Ren, or a leader such as Darth
  Traya - also gets the rest of that squad needed in the same phase, as far as they have them at the
  level needed, so another member's team isn't broken up. The list is preset from the GAC 5v5 squads
  list (S tier first, then A to D; SLKR also keeps the First Order units) and can be edited in
  Platoon planner: rules. A unit in more than one squad goes with the squad higher up the list.
  Those slots show a "with <leader>" tag.
- **Each guild has its own planet and operation choices.** Officers pick them in side menu → ⚙ Platoon planner: operations
  to fill and press **Save selections** (saved to `guilds/<guild>/platoon-settings.json`). The rules
  (relic minimums, per-member limit, GL rules, tier balancing) are saved there too, per guild.
  **Save and share** also saves the choices the assignments were made with.
- **Two passes.** When a planet can't be finished in one phase - e.g. Malachor reached in phase 5
  without its first star - pick its operations in phase 5 and press **⇄ Two passes: P5 + P6** on that
  planet's row. The planner fills what it can in phase 5, then fills the rest of the same operations in
  phase 6, when everyone's roster has refreshed, so the same members can place the same units again
  (e.g. one Starkiller in phase 5 and the same Starkiller in the same operation in phase 6). Those
  operations show "+P6" in the picker, the slots are tagged *1st pass* / *2nd pass*, and the planet
  summary shows the split. Moving an operation to another phase turns its second pass off.
- The page shows which planets each guild is filling in each phase, and flags it when the choices
  have changed since the assignments were last made.

## TB phase assignments posted automatically

When each Rise of the Empire phase starts, that phase's platoon assignments are posted to the guild's
assignments channel as plain text - one block per member (name, then each planet and operation with
the units to place) - so members can search Discord for their name. It runs by itself every 15
minutes (`.github/workflows/tb-phase.yml` → `scripts/tb_phase.py`) and posts within about 15 minutes
of a phase starting, only once per phase. It uses the assignments saved with **Save and share**.

- **Webhook:** GitHub secret `<GUILD>_ASSIGN` - `OANR_ASSIGN` for OANR (GitHub stores secret names in
  capitals, so `OANR_assign` works). A guild's `config.yml` can name another with `discord_assign_secret`.
- **When phases start:** read from the game on each pull (the guild's running TB, or the TB event in the
  game's schedule) and saved in `guilds/<guild>/tb-schedule.json`. If that's wrong or missing, an officer
  sets the phase 1 start time under side menu → Officers → RotE platoons → **TB phase times (auto-post)**,
  which also lists when each phase will post. With **A new TB every 14 days** (the default) the time
  repeats: phase 1 of each TB starts 14 days after the last, each phase 24 hours. Set to 0 for a
  one-off time, used until that TB ends. A time set here wins over the game's. OANR is set to phase 1
  at 17:00 UK time on 26 Oct 2026, every 14 days.
- **Posted already:** kept in `guilds/<guild>/tb-posts.json`. A phase that started more than 20 hours ago
  isn't posted late.
- **By hand:** **📣 Post phase to Discord** in the planner (or Officers → Post to Discord → Platoons: one
  phase) posts the same text for the phase shown (or just the member picked in "Show"), and **Platoons:
  whole guild** posts every phase. Every platoon post goes to the `<GUILD>_ASSIGN` webhook (falling back
  to `DISCORD_WEBHOOK_<GUILD>_PLATOONS` if that isn't set).

### Each member's own platoons by DM (optional, members opt in)

A Discord bot can also DM each member just their own list when a phase starts. Members choose this themselves:

1. **Create the bot once (it serves every guild).** Go to discord.com/developers/applications → New Application → **Bot** → Reset Token → copy the token. No privileged intents are needed.
2. **Invite it to each guild's server:** open
   `https://discord.com/oauth2/authorize?client_id=<APPLICATION ID>&scope=bot&permissions=68672`
   (the Application ID is on the General Information page). 68672 = View Channel, Send Messages, Add Reactions, Read Message History. It must be able to use the assignments channel.
3. **Give the site the token:** Officers → 🔗 Discord webhooks → *Discord bot* → paste → Save. It's stored as the GitHub secret `DISCORD_BOT_TOKEN`.

Within 15 minutes the bot posts a message in the assignments channel: *react ✅ to get your platoon assignments by DM*. Anyone who reacts is DM'd their own list as each phase starts. Removing the reaction stops it.

Discord names are matched to in-game names automatically (server nickname, display name or username equal to the in-game name). Officers → RotE platoons → **Discord DMs (who gets them)** lists everyone who opted in. There officers can confirm a best guess, link someone whose name doesn't match, or unlink someone; the links are saved in `guilds/<guild>/discord-links.json`. A member who isn't linked gets no DMs. The page also shows anyone whose last DM failed, usually because their DMs from server members are switched off.

Only members who opted in are stored (`guilds/<guild>/discord.json`).

## Guild overview

The **▦ Guild overview** page (`…/guild.html?guild=oanr`) shows every current member side by side,
one section at a time. Members run down the left (click a name for their Player status); click any
column heading to sort, and the bottom row shows the guild total or average.

- **Stats** – GP, GA league and division, GA skill rating, Total score, Mod score, Gear score
- **Roster** – Galactic Legends, Conquest characters, G13, and R1 / R5 / R7 / R8 / R9 / R10 (switch
  between *at least* and *exactly* that relic). Conquest characters are listed in
  `scripts/conquest-units.txt`, plus any the game itself marks as Conquest units - add a new one
  to the file if it's missing (one unit ID per line).
- **Abilities** – zetas, omicrons, and omicrons for TW, TB and GAC

The roster and abilities come from the roster (uploaded or pulled from the game). GA and mods only
come from the game, so they appear for guilds connected with an ally code; they're
saved in `guilds/<guild>/profiles.json` (no ally codes) on the daily roster pull.

HotUtils doesn't publish how its scores are worked out, so the site uses its own (also explained on the page):
- **Mod score** – mods with +15 speed or more ÷ (character GP ÷ 100,000), like swgoh.gg's mod quality.
- **Gear score** – each character adds G12 = 1, G13 = 2, plus 1 per relic level; added up.
- **Total score** – 0-100: where the member ranks in the guild on GP, GA skill, mod score and gear
  score, averaged (50 = middle of the guild).

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
  **Stars earned by TB** charts the guild's stars in every TB with a dashed trend line (and an
  *improving / level / declining* badge once there are 3 TBs). For a guild connected to the game with
  an ally code the stars are read from the game on each pull; otherwise (or to correct one) an officer
  uses **★ Set TB stars** in the menu. Both are kept in `guilds/<guild>/tb-stars.json` (`set` = typed
  by an officer, wins; `game` = from the game, matched to a TB ending within 2 days). Add
  `tb_max_stars: 56` (or your figure) to the guild's `config.yml` to show stars "out of" a maximum.
- **Members** – everyone's points, change vs their last TB, trend (line of best fit over the last
  5 TBs, same rule as raids), waves completed %, combat mission attempts, platoon units, a square
  per phase for deployment (green full, amber partly, red none) and short *to work on* tags. Click a
  member for their per-phase breakdown and their points and wave % by TB against the guild median.
  **Waves done** is the total combat mission waves each member completed in that TB (sortable;
  hover for the most possible), and the **Total** row at the bottom adds up points, waves and CMs
  for the members shown.
- **Phases** – one phase at a time: points, GP deployed, waves and CM attempts for every member.
- **Player** – pick a member (or click a name anywhere on the page) for their full summary: a
  one-line verdict (trending up / level / down, what's improving or falling, which phases are getting
  stronger or slipping), seven measures (including total waves completed) with change vs their last TB, trend and guild median, charts
  of points and wave % by TB with a trend line, points and waves by phase for their last 5 TBs, a
  trend table per phase, charts for any one phase over time, rank by TB, CM attempts and platoons by
  TB, and their full TB history. Links can be shared: `…/tb.html?guild=oanr&player=taero#player`.

**How it's judged.** *Waves %* = waves completed ÷ the most a member could complete
(`tb_max_waves` in the guild's `config.yml`; change it if your guild opens different planets).
**Inactive** = no points, or no deployment and no combat at all. **Partial** = missed full deployment
in 2+ phases, or wave % under half the guild median. *To work on* flags phases not deployed or only
partly deployed, combat waves under ¾ of the guild median, few or no platoon units, no special
missions, and falling points.

## Territory wars

The **✦ Territory wars** page (`…/tw.html?guild=oanr`) tracks every TW: who joined, banners on defence
and offence, and the result.

**After each TW:** on the upload page choose **Territory war**, pick Won / Lost / Draw (and the scores if
you like) and drop in WookieeBot's `twstats.csv`. The date and opponent come from the file, which is
saved as `guilds/<guild>/tw/<date> TW.csv`. The export doesn't include the result, so it's saved in
`guilds/<guild>/tw/results.json`; officers can also set or change it later with **✎ Set result** on the
TW page.

- **Overview** – result and win/loss record, banners (vs the last TW), defence and offence banners,
  how many joined, charts of banners and participation by TW, and lists of who didn't join, who joined
  but set no defence, and who got no offence banners; top 10 banners and top offence.
- **Members** – everyone's banners, change vs their last TW, trend, defence, offence, times disobeyed,
  how many TWs they joined, and this TW's status (defence + offence, no offence, no defence, did
  nothing, didn't join). Click a member for their defence and offence in every TW.

"Didn't join" means current guild members (from the latest roster or raid upload) missing from the file.

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

Officers open **side menu → ⚙ Contribution settings** (officer password) to choose which phases count (e.g. untick
Phase 1) and how much each part is worth. **Preview** changes only their own view; **Save for
everyone** saves to `guilds/<guild>/tb-settings.json` and every member sees it about two minutes
later. Anyone with the link can view the ranking; only officers can change the settings.

### TB results from the game (tb-history.json)

For a guild connected to the game, the game's territory battle history can be used instead of the WookieeBot TB export. Upload `tb-history.json` as **Territory battle** on the Upload page. No date is needed. The next update looks up each player ID's name from the game and adds every TB in the file that isn't on the site yet, as `tb/<day it ended> RotE.csv` with stars, in the same columns as the old export. TBs already uploaded (any file dated from the TB's start to 3 days after its end) are left alone. The uploaded JSON isn't kept.

How the game's figures map to the columns: territory points = `summary`, deployed GP = `power`, combat attempts = `strike_attempt`, waves = `strike_encounter`, special missions = `covert_attempt`, platoon units = `unit_donated`, rogue actions = `disobey`, each per round for the phases. "Deployed" is Yes when a member deployed at least 95% of the most GP they deployed in any phase of that TB.

If the game includes these results in the guild data it shares, each pull from the game adds finished TBs by itself, with no upload needed.

### Uploading a TB phase by phase

On the upload page, a TB upload asks **Which territory battle is this?** Pick *Update the TB of …*
(pre-selected when the last TB is less than a week old) and the new export replaces that TB's file,
so the same TB just fills in as the phases go. Pick *A new territory battle* to start the next one.

Uploads that ended up as separate TBs can be tidied on the TB page: **Officers → ✎ Manage TB uploads**.
Tick the uploads of one TB and *merge* them (the one with the most phases is kept, the rest removed,
under the date you choose), *change the date* of a TB, or *remove* an upload. The site updates about
two minutes later; removed files stay in the repository history.

## Guild effectiveness (raids + territory battles)

**◎ Effectiveness** (`…/effectiveness.html?guild=oanr`) combines raid and TB performance into one
score per member.

- **Raid score** – in each of the last 5 raids (every raid type with results), the member's score as a
  % of the guild's best score in that raid, averaged. A raid they didn't score in counts as 0 once
  they'd joined.
- **TB contribution** – the overall score from the Contribution page (same phases and weighting the
  officers chose there), averaged over the last 3 TBs. A missed TB counts as 0 once they'd joined.
- **TW score** – in each of the last 3 territory wars, the member's banners as a % of the guild's best
  member in that TW. Not joining counts as 0 for members who were already in the guild.
- **Effectiveness** = raids 45% + TBs 45% + TWs 10% by default. Officers can change the weights, how
  many recent raids, TBs and TWs count, and switch territory wars on or off (side menu → ⚙ Effectiveness weighting).

The page shows a raids-vs-TBs chart (strong in both, stronger in one, or below the guild median in
both), a ranking, and a table with each member's raid and TB scores, trends and attendance. Click
a member for their raid scores and TB contribution over time. New members with only raid or only TB
results are listed but not ranked until they have both. Officers can change the weighting and how
many recent raids and TBs count under **side menu → ⚙ Effectiveness weighting** (saved to
`guilds/<guild>/stats-settings.json`).

## Posting to Discord

Each post is the whole page as pictures (cut between sections so they stay readable), plus a link, posted by GitHub after the site updates.

- **Raids** post automatically whenever new raid results are uploaded.
- Officers can post any time from **side menu → Officers → 📣 Post … to Discord**: on the raid page *Post raid results* (overview and players for the raid shown) and *Post raid readiness* (readiness on its own - handy for showing progress towards the next raid, e.g. Droid Destruction while you're still running Order 66),
  the Territory Battles page (the TB shown), the Effectiveness page, and the platoon planner
  (**📣 Post phase N to Discord** next to "Copy phase for Discord": the phase's planets, totals and
  every member's assignments). **Platoons: whole guild** (or **📣 Post whole guild to Discord** in the
  planner) posts one list per member covering every phase - e.g. "P1: Corellia op 2 – Darth Malgus ·
  …" - split over as many messages as it needs, to the platoons channel. Save and share the
  assignments first. The button asks for the officer password, then the post appears about 3 minutes later.

**Setting webhooks from the site:** side menu → Officers → **🔗 Discord webhooks**. Pick the guild, paste
the Discord webhook for each channel (main, officers', platoon assignments), optionally **Send a test
message**, and save. The site encrypts each one with the repository's public key and saves it straight
into the GitHub secrets below, so nobody needs to open GitHub; a saved webhook can't be read back, only
replaced or removed. This needs the GitHub token behind the officer password to have **Secrets: Read and
write** (a one-time change to the token on GitHub; the form says so if it's missing).

Webhooks are GitHub secrets (Settings → Secrets and variables → Actions):

| Posts | Secret |
|---|---|
| OANR raids, TBs and TWs | `DISCORD_WEBHOOK_OANR` |
| OANR effectiveness (officers' channel) | `OFFICER_OANR` (falls back to `DISCORD_WEBHOOK_OANR` if missing) |
| OANR platoons | `DISCORD_WEBHOOK_OANR_PLATOONS` |
| Endor Legacy raids and TBs | `DISCORD_WEBHOOK_ENDOR_LEGACY` |
| Endor Legacy effectiveness (officers' channel) | `OFFICER_ENDOR_LEGACY` (falls back to the main one) |
| Endor Legacy platoons | `DISCORD_WEBHOOK_ENDOR_LEGACY_PLATOONS` |

(A guild's `config.yml` can name different secrets with `discord_secret`, `discord_platoons_secret` and `discord_officer_secret`.)
How it works: the button saves a small request in `guilds/<guild>/posts/`; the next site update posts it
and removes the request.

## Choosing a guild

The guild is picked from the **Guild** dropdown in each page's banner. The choice is remembered on
the device and carried to every page (and the side menu's links), until a different guild is picked.
A link with `?guild=...` in it always opens that guild. A page with no data for the chosen guild yet
(e.g. no territory wars uploaded) shows the first guild that has some.

## Site update progress

Uploading a file, **Pull from the game now**, and the officer tools that save something (TB stars,
Manage TB uploads, settings…) show a progress bar in the bottom corner while GitHub updates the site:
waiting to start → getting ready → pulling from the game → working out the stats → publishing.
When the new site is live the page refreshes by itself (after an upload it opens the results). You
can move to another page meanwhile - the bar carries on there. If GitHub didn't need to rebuild
(the file was the same as before) or the update failed, it says so, with a link to GitHub.

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

Officers set each raid's **score target** from the site: side menu → Officers → Raids → **Score targets**
- pick the raid, type the score (3000000, 3M or 2.5m), save. It's saved per guild in
`guilds/<guild>/raid-targets.json` and wins over the other two places a target can be set.
The **Players** tab then shows *Target* (✓ on target, or ✗ how far below) and *Times below* (raids
they finished under the target, out of the raids they were in - a blank or zero counts), and the
**Overview** lists every current member below target in the latest raid, how far below (%) and how
many times they've been below. Times below uses the current target for every past raid.

A guild can also have its own target score for a raid in its `config.yml` under `target_scores`.

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
