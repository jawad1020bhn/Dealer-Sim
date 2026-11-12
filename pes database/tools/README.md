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

Files:

- `lib.py` — readers for the PES 2017 edit file and the Football Life 27 save.
- `fldb.py` — Football Life 27 player database.
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
