# African Football Scouting Tool

A Streamlit app that helps scouts and recruitment analysts find, profile, compare and track players in South Africa's **Betway Premiership**, using open data only.

**Live app:** 

![Shortlist page](data/images/shortlist.png)

---

## Research question

**How can player performance data help identify promising recruitment targets in African football?**

African leagues get little public analytics coverage, and most advanced data sits behind commercial providers. This project asks how far open data can take a recruitment workflow, and is explicit about where it runs out.

## The scouting workflow

The app follows the steps a recruitment analyst actually takes: **find** players, **understand** them, **compare** them with alternatives, and **decide** who is worth following up.

| Step | Page | What it does |
|---|---|---|
| Find | **Shortlist** | Pick a role, weight the stats that matter and filter by age, minutes and club. Returns a ranked list with a plain-language reason for every player, top picks as cards, and a one-click link to compare the top three. |
| Understand | **Player profile** | Role, minutes and the player's three strongest stats, then role percentiles, role history, this season's form against last season, and the five most similar players (each one clickable). |
| Compare | **Compare** | Two or three players side by side: percentiles, per-90 values with the best value highlighted, and an automatic written summary of who leads on what. |
| Decide | **Watchlist** | Save players with a status (To watch, Watch live, Shortlisted, Rejected) and notes. Download and reload as CSV. |
| | **Methodology** | How roles, percentiles, similarity and fit scores are built, what was tested and rejected, and the limitations. |

**Moving between pages.** Every player you come across is one click from the next step, so you never have to search for the same player twice:

- Names on the **Shortlist** cards, in **Similar players** and on the **Watchlist** open that player's profile at the right season.
- **Compare the top 3** (Shortlist) and **Compare with the top 2 matches** (Player profile) open the Compare page with the players already selected.
- **Add to watchlist** on the Shortlist, Player profile and Compare pages saves a player straight from wherever you found them.

Example explanation from the Shortlist page (strikers):

> **Flávio Silva** (Kaizer Chiefs, 2025-26)
> - Top 4% for non-penalty goals per 90
> - Top 4% for shots on target per 90
> - Top 7% for goals per 90 among strikers
> - One qualifying full season only

| Player profile | Compare |
|---|---|
| ![Player profile](data/images/profile.png) | ![Compare](data/images/compare.png) |

---

## Data

- **Source:** [FBref](https://fbref.com) player and squad tables, exported manually using FBref's CSV tools. FBref's data is provided by Data Sports Group.
- **Seasons:**
  - **2024-25 and 2025-26** are full seasons used for player rankings. The **2026-27** season is treated as current form only. 
- **Minimum minutes:** 900 for full seasons and 450 for 2026-27. 
- **Volume:** 1,532 player-season rows before filtering; 573 after minimum minutes; 408 outfield player-seasons in the two profiling seasons. The Home page shows qualifying player-season records by club and season. A dash indicates that the club was not in the league that season. Royal AM has no 2024–25 player data available on FBref.
- **Checks:** every season's row counts, goal totals and spot-checked players match FBref's league pages.
- **Ages:** current year minus birth year. Where FBref has no birth year, it was filled in by hand from a checked source and recorded in `data/manual/birth_years.csv`.

**Available stats:** minutes, goals, assists, shots, shots on target, crosses, tackles won, interceptions, fouls committed and drawn, offsides, cards and on-pitch goal difference.

**Not available in open data:** passing, dribbling, duels, clearances and expected goals (xG).

### Why only FBref?

Why only FBref?

Richer sources such as Sofascore, FotMob and Transfermarkt were not used as data sources because I did not have permission to extract and reuse their data. Sofascore was contacted directly and declined to provide data. These platforms were used only for manual reference checks of individual players, never as sources for the statistical dataset. Raw FBref exports are not included in this repository.

---

## Method

```
one_season.py  →  roles.py  →  percentiles.py  →  similarity.py  →  shortlist.py  →  Streamlit app
```

### 1. Building the dataset (`one_season.py`)
Merges four FBref player tables per season on FBref's player ID and club, computes per-90 stats, and checks each season against FBref's totals. Players at two clubs in a season are combined before the minutes filter.

### 2. Role classification (`roles.py`), rules v1.0
FBref only gives broad positions (GK/DF/MF/FW), so scouting roles are inferred: **CB, FB, DM, CM, W/AM (wide or attacking midfielder) and ST**.

- **The source position sets the allowed roles.** A `DFMF` can be CB, FB or DM, but never a winger.
- **Several stats decide together.** Each role has a weighted score built from multiple stats, standardised within each season and position group (defenders against defenders, and so on).
- **The source position is the starting point.** Roles matching a player's first-listed position get a small head start; CM is the default for midfielders unless their stats clearly point to DM or W/AM.
- **Every assignment has a confidence margin.** Near-ties are flagged and shown as "borderline" in the app.
- **36 documented manual overrides** correct clear errors, each with its evidence (mostly season-level position appearances).

**Validation:** Forward roles were checked against independently sourced main positions for 28 regular forwards. The classifier alone agreed in **24 of 28 cases (86%)**. Three of the four disagreements were flagged as low confidence, while one was a more confident misclassification. Documented manual overrides corrected the four disagreements in this validation sample. Transfermarkt positions were used as an independent reference, not as definitive ground truth.

### 3. Possession adjustment: tested and rejected
A standard adjustment (scaling tackles and interceptions to 50% opponent possession) was tested. In this league, team possession had little relationship with defensive output:

| Role | Correlation before | After adjustment |
|---|---|---|
| CB | -0.26 | +0.22 |
| FB | -0.18 | +0.40 |
| DM | **+0.21** | +0.65 |
| CM | 0.03 | +0.35 |

The adjustment over-corrected every role, creating a link with possession that wasn't there before. Defensive midfielders at dominant clubs actually make *more* defensive actions, consistent with high pressing. **v1 therefore uses unadjusted stats.** The test is kept in `possession.py`.

### 4. Percentiles (`percentiles.py`)
Each player is ranked **only against players in the same role**, pooled across both full seasons (pools of 35–94 players). The pool includes the player being ranked, which moves a percentile by at most a few points. Current-season players are ranked against the same full-season pool. For fouls, cards and offsides, lower is better. Shot accuracy and goals per shot are left blank for players with fewer than 10 shots.

The top-ranked players per role match FBref's own 2025-26 league leaders (e.g. tackles won, interceptions, crosses, assists per 90).

### 5. Similar players (`similarity.py`)
Weighted distance between percentile profiles within the same role, shown as a **profile similarity score** (0–100). It ranks matches; it is not a percentage of likeness.

- **On-pitch goal difference is excluded**, because it says more about the team than the player. With it included, players from strong clubs were mostly matched with each other.
- **Discipline stats are down-weighted (0.25)**, so two centre-backs aren't matched mainly on rarely being booked.
- A player is never matched with himself, and each similar player appears once (their closest season).

### 6. Shortlists (`shortlist.py`)
The **fit score** is the weighted average of a player's percentiles on the stats the scout prioritises. It is not an overall rating or a probability of success. Discipline stats default to a quarter weight, because few fouls can mean low involvement rather than good defending. Each player is scored on their most recent full season, and the explanation covers:

- their standout stats (leading with the scout's priorities)
- consistency with their other full season
- current form, flagged as a small sample
- whether their last qualifying season was 2024-25 ("check current status")

---

## Findings

- **Thin markets show up quickly.** The pool of young ball-winning defensive midfielders is small. Under the selected age, minutes and performance criteria, only around three strong candidates emerged outside Sundowns and Orlando Pirates across the two profiling seasons.
- **Possession doesn't work the way the standard adjustment assumes in this league**, especially for defensive midfielders.
- **Role versatility is common.** Several players change role between seasons (e.g. wide to central forward), which the role history makes visible.

## Limitations

- **No passing, dribbling, duel or xG data.** Creative, build-up and aerial qualities are under-represented. **Centre-back profiles are the thinnest** (interceptions, tackles, fouls and cards only).
- **Fouls drawn stands in for ball-carrying**, which can pull target strikers towards the wide/attacking role.
- **Set-piece crosses aren't separated** from open-play crosses, which can make central set-piece takers look like wide players.
- **Roles are inferred** from stats, not from watching matches. Borderline cases are flagged rather than hidden.
- **Ages are approximate** (current year minus birth year).
- **The watchlist is stored in a file on the machine running the app.** On the public demo it is shared and resets when the app restarts, so it can be downloaded as CSV.
- **Goalkeepers are not yet included.**

The numbers are a starting point for scouting, not a replacement for watching players.

## Future work

- Goalkeeper profiles from FBref's goalkeeping tables
- Other African leagues, using within-league percentiles (raw stats aren't comparable across leagues of different strength)
- A partial possession adjustment calibrated for centre-backs only
- Scout-weighted similarity
- Contract and market-value data, if a licensed or permitted source becomes available

---

## Project structure

```
african_scouting_tool/
├── Home.py                     # app home: overview, start cards, data coverage
├── pages/
│   ├── 1_Shortlist.py
│   ├── 2_Player_Profile.py
│   ├── 3_Compare.py
│   ├── 4_Watchlist.py
│   └── 5_Methodology.py
├── src/
│   ├── config.py               # seasons, minute thresholds, rules version
│   ├── one_season.py           # build and verify each season
│   ├── roles.py                # role classification (v1.0)
│   ├── review_roles.py         # flags borderline roles for review
│   ├── validate_forwards.py    # forward role validation
│   ├── possession.py           # possession adjustment test (not used in v1)
│   ├── percentiles.py
│   ├── similarity.py
│   ├── shortlist.py
│   ├── missing_ages.py         # lists players with no birth year
│   ├── watchlist.py            # watchlist storage and button
│   └── app_data.py             # shared app loading, labels and styling
├── data/
│   ├── manual/                 # role overrides, review log, hand-checked birth years
│   └── processed/              # pipeline outputs used by the app
├── outputs/                    # exploration charts and the role review list
└── requirements.txt
```

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run Home.py
```

To rebuild the data, export the FBref player tables into `data/raw/fbref/` (see the docstring in `src/one_season.py`), then run the pipeline scripts in order.

Club crests are not included in the repository. To show them locally, add PNGs to `static/crests/` named after each club (e.g. `kaizer-chiefs.png`). The app works without them.


Data: [FBref.com](https://fbref.com). Club crests, where shown in screenshots, are the property of their respective clubs and used for identification only. This is a non-commercial portfolio project.