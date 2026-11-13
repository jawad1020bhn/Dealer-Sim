# Edit-file tools

Scripts used to update `EDIT00000000 (pes 2017 updated)`. They work on the decrypted `data.dat`.

Sources expected under `$PES_WORK` (default `/home/user/pes-work/`):

- `pesXdecrypter/` — `git clone https://github.com/the4chancup/pesXdecrypter`, then per tool
  `gcc -O2 -std=gnu99 -DUSE_PES17_MASTER_KEY -o dec17 src/decrypter.c src/crypt.c src/mt19937ar.c src/masterkey.c -Wl,--allow-multiple-definition`
  (`encrypter.c` for `enc17`, `-DUSE_PES21_MASTER_KEY` for `dec21`; the Football Life save also needs its key file).
- `src/pesforge` (Binz120/pesforge), `src/flko` (choepd/FL27-player-names-ko), `src/fc27repo`
  (narendradarel/Praktikum-Dataset-EAFC27), `src/fc26.csv` (`data/players.csv` of ismailoksuz/EAFC26-DataHub).
- `src/mouhbnms_football-player-scouting` (mouhbnms/football-player-scouting): `Data/players.csv`, EA's complete FC 27
  list (17,849 men, ratings 47–91, snapshot 2026-09-12). Used by task 12.
- `src/fpl` (olbauday/FPL-Core-Insights): Premier League 2026/27 player statistics per gameweek. Used by task 14 and task 15.
- `src/wyscout` (btgriff/Wyscout_Data, `git clone --depth 1`, 1.3 GB): Wyscout exports per league and season, state of
  12 November 2026. Used by tasks 30 to 33 through `wyscout.py`.
- `src/optiscout-football-dss`, `src/asta-fantacalcio` (FBref / Understat tables of task 23; task 33 reads the first).

Files:

- `lib.py` — readers for the PES 2017 edit file and the Football Life 27 save.
- `fldb.py` — Football Life 27 player database.
- `wyscout.py` — Wyscout league tables of 2026-27: loader, link to the file players, club map.
- `rate.py` — PES 2017 overall formula and FC 27 / FC 26 tables. Self-check: `python3 rate.py <data.dat>`.
- `task11.py` — missing players, youngsters, wing starters, managers and tactics.
  `python3 task11.py <in data.dat> <FL data.dat> <out data.dat>`; ends with a self-check of the written file.
- `task12.py` — players aged 23 or under: EA FC 27 rating and Football Life 27 info. Run it on the output of `task11.py`:
  `python3 task12.py <in data.dat> <out data.dat>`; ends with a self-check of the written file.
- `task13.py` — five classic teams (World Cup Heroes, Modern Champions, FC Icons, UCL Legends, Cult Heroes) from the
  Football Life 27 classic players the file lacks. Run it on the output of `task12.py`:
  `python3 task13.py <in data.dat> <out data.dat>`; ends with a self-check of the written file.
- `task12.py --older` — the same for players aged 24 or over (EA FC 27 rating where EA lists the player, no estimate;
  nationality only where the national squad or EA agrees with Football Life 27). Run it on the output of `task13.py`:
  `python3 task12.py <in data.dat> <out data.dat> --older`.
- `task14.py` — realism pass: duplicates, five national managers, national squads, estimates for older club players
  without an EA rating, form values, registered positions of starters, Premier League form rises and nine hand-built
  legends. Run it on the output of `task12.py --older`:
  `python3 task14.py <in data.dat> <out data.dat>`; ends with a self-check of the written file.
- `task15.py` — squads and line-ups, no rating of an existing player changes: transfers (Football Life 27 squads, the
  "has joined" notes of the fantasy data, EA FC 27 for clubs FL 27 lacks), missing players written into unused records,
  Premier League line-ups from minutes, starters out of position at top-five clubs, Premier League set-piece takers and
  shirt numbers as in FL 27. Run it on the output of `task14.py`:
  `python3 task15.py <in data.dat> <out data.dat>`; ends with a self-check of the written file.
- `task16.py` — more missing players. A record may be overwritten if it is a free agent, no source knows its name, it is
  rated 69 or lower, and the player written into it is rated 70 or higher. Football Life 27 squad members join their
  club (starting elevens stay), the others become free agents. It runs the set-up part of `task15.py` from its source,
  so both files must stay in this folder. Run it on the output of `task15.py`:
  `python3 task16.py <in data.dat> <out data.dat>`; ends with a self-check of the written file.
- `task17.py` — appearance of every player that was written into another player's record (skin colour, face shape,
  facial hair, hair, build) from `PlayerAppearance` of the Football Life 27 database (`pesdb.py` of pesforge reads it),
  and the "edited" flags of those records. It needs the original save decrypted too, to see who each record used to be:
  `dec17 "pes database/EDIT00000000 (pes 2017)" orig`. Run it on the output of `task16.py`:
  `python3 task17.py <in data.dat> <orig/data.dat> <out data.dat>`; ends with a self-check of the written file.
  Scanned faces are files of the game tied to the player id; an edit file cannot add them.
- `task18.py` — the 22 clubs whose main formation had three centre-backs with a full-back on one side and a winger on
  the other: both wide men become RMF / LMF at the same depth (RB / LB where Football Life 27 plays full-backs), and a
  starter not rated A for the new role is raised to A. Needs the decrypted Football Life 27 save
  (`dec21 EDIT00000000 fl FL_key.bin`). Run it on the output of `task17.py`:
  `python3 task18.py <in data.dat> <out data.dat> <fl/data.dat>`; ends with a self-check of the written file.
- `task19.py` — registered positions set by hand (table `NAMED`: Gnabry and Karl of Bayern to RMF); the overall stays.
  Run it on the output of `task18.py`: `python3 task19.py <in data.dat> <out data.dat>`; ends with a self-check.
- `task20.py` — 15 free agents go back to the club they last belonged to (table `NAMED`): Real Zaragoza, Bari, Spezia,
  Amiens and AVS, clubs that Football Life 27 and EA FC 27 no longer carry. Evidence: FC 26 and the Transfermarkt
  profiles of `salimt/football-datasets` (both September 2025), no other club in either 2026/27 source.
  Run it on the output of `task19.py`: `python3 task20.py <in data.dat> <out data.dat>`; ends with a self-check.
- `task21.py` — 10 free agents join their real 2026/27 club (table `NAMED`, from a web check in November 2026 of the
  best-rated free agents). In a full squad the weakest reserve is released.
  Run it on the output of `task20.py`: `python3 task21.py <in data.dat> <out data.dat>`; ends with a self-check.
- `task22.py` — check of player skills, playing styles and COM playing styles, with corrections: the two goalkeeper
  skills (bit 18 is Low Punt Trajectory, bit 20 is GK Long Throw; the source save had them crossed) are swapped on every
  record, and Orchestrator (stored as Anchor Man) or Creative Playmaker on a player who plays CMF or AMF becomes
  Classic No. 10, the style PES 2017 switches on there. Prints the comparison with Football Life 27 and the styles
  that still have no effect. Later tasks must call `fldb.to17(q, fixed=True)`.
  Run it on the output of `task21.py`: `python3 task22.py <in data.dat> <out data.dat>`; ends with a self-check.
- `task23.py` — playing styles, skills and COM styles from real matches of 2025-26 and 2026-27, for the 264 club
  players of the five leagues whose style PES 2017 never switches on where they play. It applies `task23.tsv` (one row
  per player with the figures that decided): 136 new styles, 89 skills and 28 COM styles on 155 players; nothing is
  removed. `task23_research.py <task22 data.dat> <out tsv>` wrote the table and holds the rules; it needs, under
  `$PES_WORK/src`, `lucianomurr/asta-fantacalcio` (FBref and Understat 2025-26), `turkensar/optiscout-football-dss`
  (FBref 2026-27) and `mouhbnms/football-player-scouting` (EA FC 27 PlayStyles).
  Run it on the output of `task22.py`: `python3 task23.py <in data.dat> <out data.dat>`; ends with a self-check.
- `task24.py` — club managers as of 12 November 2026 (table `NAMED`): all clubs of the Premier League, La Liga,
  Serie A, Bundesliga and Ligue 1 were compared with the Transfermarkt 2026/27 manager lists and the Wikipedia
  "managerial changes" tables, the second divisions of the same five countries in part. 32 clubs change (14 in the
  five leagues, 18 below); name and nationality are written into the club's manager record. A club without a head
  coach keeps the last one (Manchester United, Crystal Palace, Lens).
  Run it on the output of `task23.py`: `python3 task24.py <in data.dat> <out data.dat>`; ends with a self-check.
- Tasks 25 to 28 take what is worth taking from `EDIT00000000 (another save i found online)`, for the five leagues.
  That save was built on our first upload, so it was compared with that upload (commit `9968a9c`), not with the
  current file. Each item is kept only where a 2026/27 source confirms it; `fotmob.py` reads the FotMob first-team
  squads of 12 November 2026 (numbers, positions played) from `src/xr-football` (Savowai/xr-football, commit `13dbadf`)
  and matches them to the squads of the file. Not taken: ratings, ages, managers, line-ups, playing styles, stadium
  names, form (older than ours or not verifiable).
- `task25.py` — shirt numbers: every squad member found in his club's FotMob list gets the number of the list (115
  numbers at 43 clubs, Real Madrid's eleven checked against the club's official list); a team-mate outside the list who
  wore that number moves to the lowest free one from 30 up.
  Run it on the output of `task24.py`: `python3 task25.py <in data.dat> <out data.dat>`; ends with a self-check.
- `task26.py` — positions (tables `REG`, `PLAY`): 19 reserves get the registered position they play in 2026/27
  (FotMob and the EA FC 27 card agree; overall kept as in task 19), 10 players get extra playable positions.
  Starters are not moved.
  Run it on the output of `task25.py`: `python3 task26.py <in data.dat> <out data.dat>`; ends with a self-check.
- `task27.py` — skills (table `SKILLS`): of the 196 skills the other save adds, the 23 that pass the rules of
  `task23_research.py` (19 players); none is removed. Goal celebrations of Mbappé and Vinícius Júnior (`CELEB`).
  Run it on the output of `task26.py`: `python3 task27.py <in data.dat> <out data.dat>`; ends with a self-check.
- `task28.py` — squads (table `NAMED`): 13 free agents that the other save and FotMob both have at a club of the five
  leagues join it as reserves; in a full squad the weakest reserve outside the FotMob list is released (9). Kendry
  Páez, left without a club by mistake, joins River Plate (on loan for 2026).
  Run it on the output of `task27.py`: `python3 task28.py <in data.dat> <out data.dat>`; ends with a self-check.
- `task29.py` — the rest of the other save, all leagues, after a quality check of each kind of difference (figures in
  the docstring): 56 playable positions on 50 players that EA FC 27 or FotMob list (`PLAY`), 16 playing styles where
  ours had no effect at the player's position and the task 23 rule gives the other save's style (`STYLE`), 2 shirt
  numbers (`NUM`). Its shirt numbers outside the five leagues are last season's and are not taken.
  Run it on the output of `task28.py`: `python3 task29.py <in data.dat> <out data.dat>`; ends with a self-check.
- Tasks 30 to 33 bring the clubs outside the five leagues up to November 2026 with `wyscout.py`: the Wyscout tables of
  2026-27 (and 2026 for calendar-year leagues) list every player with league minutes this season, his team, minutes,
  positions and set-piece counts; 202 competitions, 83,330 players, no shirt numbers, no Colombia or Iran. file players
  are tied to a Wyscout player by name, age, height and nationality, and 471 of the 496 clubs to a Wyscout team.
  Checked on the web before use: Vavro (Plzeň), Tavernier, Ounahi, Vasilj, Cillessen, Jullien, Jenz, Ander Herrera,
  Gastón Suárez: Wyscout was right each time, the EA FC 27 card twice out of date.
- `task30.py` — squads: 736 players leave their club (67 with minutes there and now at another team, 643 with minutes
  for other teams only, 21 aged 38 or more whom no source has at the club, 5 Leicester players by web check); 283 join
  the club they play for (137 of the leavers, 146 free agents such as Cillessen, Ander Herrera, Cavani); 19 reserves
  are released for them, 27 joins find no room. Where a starter leaves, the best-fitting reserve steps in.
  Run it on the output of `task29.py`: `python3 task30.py <in data.dat> <out data.dat>`; ends with a self-check.
- `task31.py` — missing goalkeepers and short squads: every club is filled to two goalkeepers and 20 players from the
  Wyscout list of the club (most minutes first), then EA FC 27, then Football Life 27. 45 players are built (15
  goalkeepers; Empoli, Kayserispor, Viborg, Huesca, Mirandés, Dender among the clubs) into unused records, most of
  them the game's made-up free agents. Abilities of a Wyscout-only player are those of the nearest file player of his
  position, rated at the median of his club: an estimate. Left: Al Zawraa with one goalkeeper (no source has a second).
  Run it on the output of `task30.py`: `python3 task31.py <in data.dat> <out data.dat>`; ends with a self-check.
- `task32.py` — line-ups, takers and captains outside the Premier League: 862 starters change at 384 clubs (180
  minutes more than the starter, at most 3 rating points less), set-piece takers from the Wyscout counts at 415 clubs,
  captains of the four other big leagues from the table `CAPTAIN` (press lists of August and September 2026): 46 were
  right, 7 are set, 7 are reserves in the file and 7 are at another club in the file; no change for those 14.
  Run it on the output of `task31.py`: `python3 task32.py <in data.dat> <out data.dat>`; ends with a self-check.
- `task33.py` — playing styles outside the five leagues: the rules of `task23_research.py` with Wyscout figures in
  place of FBref and Understat. Wyscout counts lower than those two (shot assists 0.67 per 90 where Understat has 0.94
  key passes for the same 756 players), so each figure is multiplied by a factor fitted on the five-league players
  both sources have: key passes 1.33, xA 1.30, xG without penalties 1.15, shots 1.13, crosses 1.19, goals 1.07. After
  that the two sources put 93 to 99 % of those players on the same side of the thresholds the rules use (crosses and
  tackles + interceptions 88 to 91 %, on 100 and 34 players). Of 1,467 squad members whose style is None or never
  switches on where they play, 596 get one (142 of them on the EA card alone, under 450 minutes); 376 have no
  evidence and 495 are centre-backs the rules leave alone, as in task 23. Only the style is set, no skills.
  Run it on the output of `task32.py`: `python3 task33.py <in data.dat> <out data.dat>`; ends with a self-check.
- `rate.match_cards` breaks equal scores by player id since task 30 (before, the order of a Python set decided, so
  two runs could differ by a player).
- `task34.py` — the classic players are removed again: the 130 of task 13 and the nine hand-built legends of task 14.
  The five slots hold what they held before task 13 ("The Old Boys" empty, "Pleasure Horn", the three Master League
  default teams with their own players); 32 records are unused free agents again. The seven classic teams the save
  came with stay. The old content is read from the file of commit `d5341d7` (the state before task 13), decrypted.
  Run it on the output of `task33.py`: `python3 task34.py <in data.dat> <before/data.dat> <out data.dat>`; ends with
  a self-check. `task13.py` and step 9 of `task14.py` stay in the folder: the chain needs them to rebuild the file.
- `task35.py` — ratings outside the five leagues, checked and corrected. Of 10,942 club players there, 6,292 have an
  EA FC 27 card and 6,275 already carried its rating; 15 more get it now: six built by task 31 at the median of their
  club although EA rates them (Seghetti 68 to 61, Hübel 64 to 52; his card was checked on fut.gg and ea.com), seven
  matched since, and two whose card is at the club they left this season (Sevikyan, Matías Pérez: Wyscout has their
  minutes for both clubs). Two cards belong to namesakes and are left alone.
  The 4,650 without a card are compared with what their share of the club's Wyscout minutes and their age suggest, a
  fit on the rated players that misses a held-out one by 3.4 points. No group stands out: the mean gap is +0.3. 21
  regulars (45 % of the minutes of the club's most-used player) are rated 7 or more below the expectation; 19 of them
  rise to its lower edge, capped by the Football Life 27 estimate and at +5 (Vavassori 60 to 64, Julloux 61 to 66,
  Sangalli 66 to 69), two stay because Football Life 27 rates them no higher. Nobody is lowered, and a player with a
  card keeps EA's rating whatever he plays. Limits: 2,942 of the players without a card are at clubs with fewer than
  6 rated players, where the level is that of their own squad (a club rated too high or too low as a whole does not
  show); 683 players are at clubs without a Wyscout team. Run it on the output of `task34.py`:
  `python3 task35.py <in data.dat> <out data.dat>`; ends with a self-check; the list of gaps is in `<out>.log.pkl`.
