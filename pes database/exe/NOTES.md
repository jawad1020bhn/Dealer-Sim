# What the code does: save file, edit data, overall rating

Read from the decompiled C (`output/`) and from the machine code. "Run" below means: the
game's own function was executed on real inputs in a CPU emulator (`tools/emu.py`), not in
the game. `tools/check_findings.py` repeats every such run (six checks, one minute).
Nothing here was tried in the real game.

Addresses and working names are in `names.tsv`.

## 1. The save file (`EDIT00000000`)

Reader `fcn_0378d643`, writer `fcn_0378cd8d`. `tools/savefile.py` does the same in Python
(`check`, `unpack`, `pack`, `fix`) and rewrites a file byte for byte.

| at | size | content |
|---|---|---|
| 0x000 | 320 | five SHA-512 hashes: description, logo, data, serial, file header. The first four are encrypted with the fifth |
| 0x140 | 176 | file header: master key, four sizes, 64 random bytes (new on each save), the type text `EDIT` |
| 0x1f0 | | description (0x180 bytes), logo (PNG), data, serial |

- **Master key** = SHA-512 of the text `Pro Evolution Soccer 2017` in UTF-16. It is computed
  when the game starts, so it is not in the exe as bytes. (Run.)
- **Encryption**: a Mersenne Twister (MT19937) seeded with 64 key bytes; the key of a part is
  the five hashes XORed together, with the part number mixed in. (Run.)
- **The hashes are not enforced.** The reader computes the SHA-512 of each part and compares
  it with the stored one, but the compare routine (`fcn_037892be`) is given the hash in its
  internal byte order, the stored one is in output order, so the two never match; the code
  goes on when they do not match. A right hash and a wrong hash take the same path. (Run.)
  A file with stale hashes is therefore loaded. `savefile.py pack` writes right ones anyway.
- **What the reader does refuse**: a description size other than 0x180, a type text other
  than `EDIT`, sizes that do not add up to the file size.
- **Serial** = the Windows user id (SID) of the account that saved, as text. The reader
  compares it with the current user's only when the save kind asks for it (bit 3 of a
  value from the kind's descriptor); a difference returns error 4. Whether the `EDIT` kind
  sets that bit was not found. Our file keeps the serial of the uploaded file unchanged.

## 2. The edit data (`data.dat`, 0x505b04 bytes)

The game keeps the block in memory as it is in the file. Same layout as `../tools/lib.py`.

| at | records | size | content |
|---|---|---|---|
| 0x000 | 1 | 0x78 | header: version numbers and the record counts |
| 0x78 | 21,000 | 0xbc | players |
| 0x3c3e58 | 650 | 0x1e0 | teams |
| 0x410118 | 850 | 0x58 | managers |
| 0x422548 | 50 | 0x7c | not read |
| 0x423d80 | 40 | 0x80 | not read |
| 0x425180 | 2,500 | 0x84 | not read |
| 0x475a90 | 650 | 0xa4 | squads (32 player ids + shirt numbers per team) |
| 0x48faf8 | 1 | 0xb48 | not read |
| 0x490640 | 650 | 0x274 | game plans |
| 0x4f40c8 | 1 | 0x11a3a | copied whole into the database |

### Fields

The game reads a record through a table of fields: number, reader, writer, minimum,
default, maximum, width. `tools/fields.py` runs each reader and writes where the field sits:
`output/edit_fields.tsv` (106 player, 32 team, 11 manager fields). All 106 player fields
are where `lib.py` has them. Two are one bit wider in the game than in `lib.py`: registered
position (5 bits, `lib.py`: 4 + spare `uC`) and injury resistance (3 bits, 2 + spare `uB`).

A value outside minimum..maximum is not applied: the game keeps its own value for that
field. Abilities must be 40-99. The save has 35 such values, all motion numbers that were
already in the uploaded file.

### Loading: edit data → the game's database

`fcn_0408ad62` after a load; `fcn_0409d032` walks the blocks; one function per record kind.

- **Version**: when a global switch is set, a header value must equal the game's, or nothing
  is applied.
- **Players** (`fcn_0409b819`): the id is looked up in the game's own database.
  - Found: every field of the record overwrites the database player (`fcn_0409ad9e`,
    `fcn_040a04b1`), with the one exception below.
  - Not found: the player is added only if the id is a created-player id (0x100000-0x10009f,
    0x1000ba) or field 11 of the record is 1 (`uD` in `lib.py`: "this player is new").
    Otherwise the record is skipped.
- **Managers** (`fcn_0409aedd`): the same; a manager the game does not know is added only if
  field 8 (bit 7 of byte 8) is 1.
- **Teams** (`fcn_040987c5`, `fcn_040aa421`), **squads** (`fcn_040990ed`), **game plans**
  (`fcn_04099214`): copied for the team id; no condition of this kind was seen (read
  quickly, not run).

### Names and the edited flags

On a load the **name** is taken from the edit file only if the record's edited flag is 1,
or the game's database has no name for that id. Everything else in the record (abilities,
positions, age, shirt name, nationality) is applied whatever the flags say. (Run, for
players and managers.)

| record | flag | name field |
|---|---|---|
| player | field 1, bit 7 of byte 0x17 (`e_player`) | name, 46 bytes at 0x34 |
| manager | field 1, bit 0 of byte 8 | name, 46 bytes at 9 |
| team | field 1, bit 4 of byte 0x19 | name, 70 bytes at 0x98 |
| team | field 4, bit 7 of byte 0x19 | a 121-byte text (probably the stadium name) |

The other eight player flags (fields 2-9: basic settings, registered position, playable
positions, abilities, skills, playing style, COM styles, motion) are stored on the database
player; this code does not test them. What else in the game tests them (a live update
would be the usual case) was not read.

This is why `../tools/task36.py` exists: 46 renamed players and 439 renamed managers of
our save had the flag at 0.

## 3. The overall rating

`fcn_04067af3(values, position)`; `tools/overall.py` is the same formula in Python, with the
tables read from the exe. The game, `overall.py` and `../tools/rate.py` give the same number
for all 20,157 players of the save at each of the 13 positions (262,041 results; run).

- Input: 39 numbers: registered position, 13 × playable (0 / 1 / 2), 25 abilities.
- Tables in the read-only data: weights 20 × 13 at `0x0222bc28`, registered-position bonus
  `0x0222c038`, curves `0x0222c06c` and `0x0222c0a0`, blend `0x0222c128`.
- The condition arrow scales the result by −14 % … +14 % in the caller `fcn_0383899a`.

## Not proven, not read

- Nothing was loaded in the real game.
- Which ids the game's database holds. It is not in this repository (the game archive has
  the exe only), so "found / not found" cannot be checked for any player. Our tasks added no
  id: players, teams and managers of the save have the ids of the uploaded file.
- The serial check for the `EDIT` kind (above).
- Blocks marked "not read"; the collect-before-save path (`fcn_0408ab90`, `fcn_0409c4d6`)
  beyond its outline; the two other callers of `fcn_0409d032` (they pass an argument that
  switches the name rule off, probably the data import of the Edit menu).
- Teams, squads and game plans were read, not run.
