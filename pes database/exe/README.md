# PES2017.exe decompiled

Static decompilation of the `PES2017.exe` in `pes.7z.001`-`.005` (110,179,840 bytes,
sha256 `44b0caaa…954f`, 32-bit Windows, built 2 September 2016). Nothing was run: the
file was read with [REA](https://github.com/morluto/rea) driving Rizin 0.9.1 and its
Ghidra decompiler plugin (`rea execute-rizin-command`, set-up in `../../rea-setup.sh`).

Every function that could be found is decompiled to C with machine names
(`fcn_038e77af`). Three parts are understood so far and written up in **`NOTES.md`**:
the save file, how the edit data is loaded, and the overall rating. What was found
about Master League (year plan, league fixtures, salary, transfer fee, negotiations,
transfers of the computer clubs) is in **`MASTER_LEAGUE.md`**. The 133 functions
behind them have working names in `names.tsv`.

## Look something up

Python 3 only, no set-up:

```
cd "pes database/exe/tools"
python3 find.py show 0x038e77af        # the C of one function
python3 find.py string editSaveData    # functions that refer to a string containing the text
python3 find.py import CreateFileW     # functions that use a Windows import
python3 find.py callers 0x0378b253     # who calls it        (callees: what it calls)
python3 find.py name save              # working names (names.tsv); `show save_read` works too
python3 find.py grep 'overall_value'   # search all the C (a few seconds)
```

## What is in `output/`

| file | content |
|---|---|
| `c/02a.c.xz` … `c/047.c.xz` | the C: one file per 1 MB of code, functions in address order. 105,225 functions, 4,970,411 lines, 187 MB unpacked |
| `functions.tsv.xz` | 200,750 code starts: address, shape, size, blocks, call sites, data pointers, callees, lines of C, status, hint |
| `calls.tsv.xz` | 329,610 caller → callee pairs (direct calls between functions) |
| `string_refs.tsv.xz` | 43,510 function → string references |
| `import_refs.tsv.xz` | 10,426 function → import references |
| `strings.tsv.xz` | 151,820 strings of the two data sections (address, kind, text) |
| `sections.tsv`, `imports.tsv`, `exports.tsv` | 14 sections, 682 imports, 41 exports |
| `evidence.tsv` | the 132 REA Evidence ids: 3 inventory commands, 112 decompile batches |
| `edit_fields.tsv` | the 149 fields of a player, team and manager record (`tools/fields.py`) |
| `classes.tsv.xz` | 9,814 function tables of 6,932 classes: table address, class name, offset, entries, functions (`tools/rtti.py`) |

`*.xz` opens with 7-Zip, `xz -d`, or Python's `lzma`.

## Tools for the findings

They need `pip install unicorn capstone` and the exe (`rea-setup.sh` puts it in
`~/pes-work/game/`). Run from `tools/`.

| tool | what |
|---|---|
| `savefile.py check\|unpack\|pack\|fix` | the save container in Python: checks a save as the game does, takes it apart, puts it together with new data |
| `overall.py` | the game's overall rating in Python, tables read from the exe |
| `fields.py <exe>` | where each field of a player, team and manager record sits → `output/edit_fields.tsv` |
| `emu.py` | runs single functions of the exe on chosen inputs (CPU emulator, no Windows); `Game.replace` answers a game function from Python |
| `x86dis.py <exe> <address> <bytes>` | disassembly, for code the C output lacks |
| `check_findings.py <exe> <save>` | self-check of `NOTES.md` and `MASTER_LEAGUE.md`: eleven checks that run the game's code against the Python (one and a half minutes) |
| `money.py` | Master League salary and transfer fee in Python (checks 7, 8) |
| `prize.py <exe> [check]` | prize money of every cup stage and league place; `check` runs the game's cup function on all pairs |
| `yearplan.py <exe> [july\|january]` | the Master League year: which event falls on which day (check 9) |
| `fixtures.py <teams>` | the rounds of a home-and-away league as the game pairs them (check 10) |
| `clubai.py` | overall window of the players a computer club looks for, by club level (check 11) |
| `rtti.py <exe>` | class names and their function tables from the exe's type records → `output/classes.tsv.xz` (9,814 tables of 6,932 classes) |

## Sider modules

`sider/` holds Lua modules for the Sider of this game and how to install them
(`sider/README.md`):

- `MLCheck.lua`, a read-only test that writes the level table of the computer clubs and
  the fee numbers of the running game to `sider.log` (6 of 6 on the user's game).
  `sider/test_module.py <exe>` runs it outside the game against the exe file.
- `MLMoney.lua` (version 3), which changes the running game: player values by rating,
  age, position and popularity with a fixed spread per player, salaries by rating and
  age, the transfer budget of a new career, the prize money of cups and leagues, a share
  of each prize for the transfer budget, the pay gap between clubs, the salary bonuses
  and the contract limit of young players, from tables in the file.
  `sider/test_money.py <exe>` runs the game's salary, fee, budget, prize and
  contract-limit code with its changes in the emulator. Version 2 (values and transfer
  budget) ran on the user's game with the expected numbers; the parts added in version
  3 have not run in the game.

## What the file looks like

- The exe is protected. The original code section (`.srdata`, at `0x00401000`) is blanked
  in the file: 93 % zero bytes, only the padding between functions is left.
- The code that runs is in `.trace` and `.xcode` (`0x02a00000`-`0x047d3e00`, 31.3 MB).
  All addresses here are addresses in that code.
- `.xtls` is the read-only data (strings, vtables, constants), `.code` the writable data.
- `.data` (38.7 MB) is encrypted (8.00 bits of entropy per byte). Not read.
- Calls to Windows go through an ordinary import table (`.xtext`).
- It is Konami's Fox Engine: source paths such as
  `f:\soccer\pes17\patch10100\pes17\sdk\…` and names such as `fox::PropertyInfo` are in the strings.

## How the functions were found

`tools/find_functions.py`, without Rizin: an address in the code is a start when a direct
call in the code targets it or a pointer in the data holds it, and the byte before it
ends a function, or it is called from two places, or it opens with a frame set-up
(`push ebp; mov ebp, esp`: a function that follows the jump table of a `switch` has no
padding before it).

| shape | starts | what |
|---|---|---|
| `function` | 110,579 | ordinary code: decompiled |
| `atexit` | 48,390 | 12-byte stubs that register a destructor |
| `unwind` | 39,573 | C++ exception clean-up stubs |
| `dtor` | 1,768 | destructor of one global |
| `thunk` | 439 | a jump to another function |
| `ehandler` | 1 | exception handler stub |

Result for the 110,579:

| status | starts | |
|---|---|---|
| `ok` | 105,225 | C in `c/` |
| `inside fcn_X` | 3,905 | not a start: the address lies inside that function |
| `not analysed` | 909 | Rizin found no function there (mostly padding) |
| `not decompiled` | 523 | the decompiler gave an error |
| `skipped` | 17 | over 45 seconds or over the 1.4 GB memory ceiling |

The decompiled functions cover 25.56 MB of the 31.28 MB of code (81.7 %; 87.0 % without
the padding bytes). The rest is the stubs above, the import names, and code no direct
call or data pointer leads to.

## How to read the C

- It is decompiler output: it shows what the machine code does, with invented variable
  names and guessed types. It does not compile.
- `fcn_XXXXXXXX` is the function at that address. `(**(code **)(*piVar + 4))()` is a
  virtual call: the target is not known from the file alone.
- Three changes were made to the decompiler text (`tools/assemble.py`): function names in
  one form; a call through an import slot shows the import's name; a constant that is the
  address of a string gets the string as a comment.
- `hint` (57 functions) is a guess: the first `Class::Method` string the function refers to.

## Rebuild

```
bash rea-setup.sh                         # repository root: REA, the game files, Rizin (15 min)
bash "pes database/exe/tools/run.sh"      # 50 minutes on 2 cores
```

`run.sh` runs `inventory.py` → `find_functions.py` → `decompile.py` → `assemble.py` →
`check.py`. `decompile.py` ends with a second look: a start on a padding byte makes Rizin
read the bytes after it as code, and such a piece can cover real functions that follow;
the 64 starts hidden that way are analysed again on their own. The raw answers of Rizin stay in `~/pes-work/out` (not in the repository).

`check.py` is the self-check: every function has a status and every `ok` one its C; the
stack-cookie routine `fcn_038e77af` names its five Windows imports; for 300 functions the
callees are confirmed by a byte scan that does not use Rizin; 300 string references are
read back from the exe; the import slots match the file.

## Not done

- 142 functions are named (`names.tsv`); the rest is not understood. Of Master League
  five pieces are proven and many rules are only located (`MASTER_LEAGUE.md`, section 14). Of the edit data, the
  player, team and manager fields are mapped; five blocks are not read (`NOTES.md`).
- Virtual calls are not resolved, so `calls.tsv.xz` misses every call through a vtable.
- The 17 skipped functions include `0x02e8c729`, which is called from 237 places.
- The encrypted `.data` section and anything the game unpacks at run time.
