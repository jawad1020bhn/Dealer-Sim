# Edit-file tools

Scripts used to update `EDIT00000000 (pes 2017 updated)`. They work on the decrypted `data.dat`.

Sources expected under `$PES_WORK` (default `/home/user/pes-work/`):

- `pesXdecrypter/` — `git clone https://github.com/the4chancup/pesXdecrypter`, then per tool
  `gcc -O2 -std=gnu99 -DUSE_PES17_MASTER_KEY -o dec17 src/decrypter.c src/crypt.c src/mt19937ar.c src/masterkey.c -Wl,--allow-multiple-definition`
  (`encrypter.c` for `enc17`, `-DUSE_PES21_MASTER_KEY` for `dec21`; the Football Life save also needs its key file).
- `src/pesforge` (Binz120/pesforge), `src/flko` (choepd/FL27-player-names-ko), `src/fc27repo`
  (narendradarel/Praktikum-Dataset-EAFC27), `src/fc26.csv` (`data/players.csv` of ismailoksuz/EAFC26-DataHub).

Files:

- `lib.py` — readers for the PES 2017 edit file and the Football Life 27 save.
- `fldb.py` — Football Life 27 player database.
- `rate.py` — PES 2017 overall formula and FC 27 / FC 26 tables. Self-check: `python3 rate.py <data.dat>`.
- `task11.py` — missing players, youngsters, wing starters, managers and tactics.
  `python3 task11.py <in data.dat> <FL data.dat> <out data.dat>`; ends with a self-check of the written file.
