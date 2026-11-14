# Sider Lua modules for Master League

Modules for the Sider that ships in `pes.7z` (`sider.dll` of 20 February 2022, Lua
enabled in `sider.ini`). They work on the running game; `PES2017.exe` is not edited.

| file | what it does |
|---|---|
| `MLCheck.lua` | **read-only test.** Reads the overall window of computer clubs by level (section 9.4 of `../MASTER_LEAGUE.md`) and four numbers of the transfer fee formula (section 6.2) from the running game and writes them to `sider.log`. It writes nothing to the game |
| `test_module.py <PES2017.exe>` | runs `MLCheck.lua` outside the game against the bytes of the exe file (needs `pip install lupa`) |
| `MLMoney.lua` | **changes the game.** Player values by rating, age, position and popularity, salaries by rating and age, and the transfer budget of a new career, from tables at the top of the file. Checks the game's code first and writes nothing if it differs. Not yet run in the game |
| `money_cave.py` | what `MLMoney.lua` writes (four small routines, with their source) and the same arithmetic as Python |
| `test_money.py <PES2017.exe>` | runs `MLMoney.lua` on the exe in the emulator, then runs the game's salary, fee and budget code with the changes in and compares it with `money_cave.py` (needs `pip install lupa unicorn`) |

## Install and run `MLCheck.lua`

1. Copy `MLCheck.lua` into the `modules` folder next to `sider.exe`.
2. Add this line to `sider.ini`, below the other `lua.module` lines:
   `lua.module = "MLCheck.lua"`
3. Start the game with Sider as usual, wait for the title screen, quit.
4. Open `sider.log` (next to `sider.exe`) and look for the lines with `MLCheck`.

Expected, on the exe of this repository:

```
MLCheck 1: read-only test, nothing is written to the game
club level       0  1  2  3  4  5  6  7  8  9
lowest overall  47 51 55 59 63 67 70 73 76 83   as expected
highest overall 74 75 76 77 78 79 80 83 86 99   as expected
fee: rating step 68             at 038ab8db = 83f844   as expected
fee: 9,000 per rating point     at 038ab8e6 = 69ff28230000   as expected
fee: factor 0.00027             at 0216ba48 = 00000020d9b1313f   as expected
fee: factor 2.2                 at 01f0f2b8 = 000000a099990140   as expected
RESULT: 6 of 6 as expected. The running game has the code the notes describe, at the same addresses.
```

To remove it, delete the line from `sider.ini`.

What the result means:

- **6 of 6**: the running game holds the same code at the same addresses as the exe
  file that was analysed. A module that changes these numbers can be tried next.
- **`DIFFERENT` or `??`**: the game that runs is not this exe, or its code is changed
  in memory. No tuning module made from these notes should be used.
- **No `MLCheck` line at all**: look for `MLCheck.lua` in `sider.log`. Sider writes
  there why it skipped the module (file not found, error in `init`).

## Result in the game (14 November 2026)

`MLCheck.lua` ran on the user's PC under Sider 3.6.0: **6 of 6 as expected**, with the
same nine lines as above. So the running game holds the analysed code at the analysed
addresses, and a Sider module reads it without trouble.

What else the same `sider.log` shows:

- `luajit.ext.enabled = 0`: modules have no `ffi`, `bit` or `require`. Modules here must
  not need them.
- Sider itself uses `0x026503E0` (`_tid_addr1`), the pointer `MASTER_LEAGUE.md` calls the
  mode object, and `0x04062701`, the competition id table function. Two addresses of the
  notes confirmed from another side.
- Sider changes code at 31 places of the running game (hooks and small patches). None of
  them lies in one of the 133 functions named in `../names.tsv`, so the salary, fee,
  fixture and computer-club code runs as analysed. A later module must check this again
  for every place it writes to.
- Sider's gameplay settings point at the constants `0x01F0F2A8` and `0x01F0F2C0`, the
  neighbours of the shared 2.2 at `0x01f0f2b8`. One more reason not to change that
  constant in place.
- Three other modules of that install are not active, for reasons of their own:
  `Script_Stadiums.lua` (file `map_teams.txt` missing), `PlayerDump.lua` (calls
  `memory.search_process`, which this Sider does not have) and `GrowthBridge.lua` (asks
  for events this Sider does not know: `key_down`, `overlay_on`, `set_teams`,
  `gamepad_input`).

## `MLMoney.lua`: values, salaries and budgets

### What the game does without it

`../MASTER_LEAGUE.md` section 6. The value of a player is
`salary x (2.2 to 3.3) + 9,000 x (rating - 68)`, and the screens show 100 times the
stored amount. There is no age and no position in it, and it rises in a straight line
with the rating. From the formula, for a club high in the ranking: rating 80 about 16
million, 85 about 23 million, 94 about 40 million. The one player measured in the user's
career, Bruno Fernandes (rating 89, captain's bonus in his salary), showed 36,743,200.

When a career starts, the transfer budget of the user's club is twice the mean value of
its 16 best players, and the salary budget is the wage bill plus twice the mean salary
of its 16 best paid players (section 6.4).

### What the module does

- **Value** = `VALUE[rating] x AGE[age] x POSITION[registered position]`, times the
  player's own fixed factor (`SPREAD`), plus `FAME` percent of that for every 1,000
  popularity points of the player (section 6.5). The salary no longer enters the value.
  The rest of the game's fee function is untouched: figures handed in by a deal, the
  random change of up to 20 or 49 percent, the limit.
- **The player's own factor**: without it, two players of the same rating, age and
  position cost exactly the same. Each player gets one of 256 steps between
  `100 - SPREAD` and `100 + SPREAD` percent, chosen by his id, so it is the same every
  time the game asks.
- **Salary**: the rating part (`30 x rating - 500` plus the steps at 65, 75, 85) becomes
  `SALARY[rating] x SALARY_AGE[age]`. Club ranking factor, role bonus, popularity part,
  band and award bonuses are the game's own, in the game's old amounts.
- **Transfer budget** at the start of a career: `BUDGET_TRANSFER` times the mean value
  of the 16 best players, in place of 2 times. `BUDGET_SALARY` does the same for the
  salary budget and is off by default.

Not changed: the second salary formula (`fcn_038ab5ea`, used for clubs of the league
numbers 60 to 62 and for some players in one mode), the yearly income of the club, the
choice of players by the computer clubs (it never looked at money).

### Settings (top of the file; amounts in millions as on the screen)

| setting | default |
|---|---|
| `VALUE` | rating 60: 0.3, 65: 0.8, 70: 2.5, 75: 8, 80: 25, 85: 65, 88: 110, 90: 150, 92: 185, 94: 215, 99: 260 |
| `AGE` (percent) | up to 19: 130, falling to 100 at 25 and 26, then 27: 97, 28: 90, 29: 80, 30: 65, 31: 50, 32: 36, 33: 26, 34: 18, 35: 12, 36: 8, 37: 6, from 38: 5 |
| `POSITION` (percent) | GK 45, CB 85, LB and RB 75, DMF 95, CMF 100, LMF and RMF 95, AMF 105, LWF and RWF 110, SS 105, CF 110 |
| `SPREAD` | 12 percent up and down; 0 switches it off |
| `FAME` | 10 percent per 1,000 points |
| `SALARY` (first club of the ranking; a club outside the first 250 pays half) | rating 60: 0.2, 65: 0.5, 70: 1.2, 75: 2.6, 80: 5.5, 85: 10, 88: 15, 90: 20, 92: 25, 94: 30, 99: 36; `false` leaves salaries alone |
| `SALARY_AGE` (percent) | 16: 45, 18: 50, 20: 62, 22: 76, 24: 90, 26 to 31: 100, 33: 92, 35: 80, 37: 65, 39: 50 |
| `BUDGET_TRANSFER` | 3 (the game: 2); `false` leaves the game's code |
| `BUDGET_SALARY` | `false` = the game's own 2 |
| `WRITE` | `true`; `false` = check and report only |

The defaults were set by hand against published figures of 2026: the most valuable
players at 200 to 220 million, the 25th at 100 million; Bruno Fernandes at about 42
million and 300,000 pounds a week; Manchester United's summer of 145 million pounds
spent and 99 million net. They are a starting point, not a fit to a data set.

What the defaults give for the players and squads of the edit file in this repository
(worked with `money_cave.py`, `SPREAD` left out, every club taken with club part 300 of
the popularity; not read from a career):

| | |
|---|---|
| most valuable | Lamine Yamal 238 million, Erling Haaland 204, Jude Bellingham 193, Michael Olise 183, Kylian Mbappé 183, Pedri 175, Vitinha 167 |
| 25th, 50th, 100th, 200th player | 93, 70, 51, 33 million |
| transfer budget | Manchester United 107 million (72 with the factor 2, 39 with the game's own formulas), Manchester City 208, Real Madrid 232, Paris Saint-Germain 254, Liverpool 147, Juventus 88, Brentford 59, Sevilla 29, Burnley 19 |

### Install

1. Copy `MLMoney.lua` into the `modules` folder next to `sider.exe`.
2. Add to `sider.ini`: `lua.module = "MLMoney.lua"`
3. Start the game. `sider.log` must show seven `check:` lines "as expected", the line
   "free memory ... empty", three `written:` lines "ok", the tables, and
   `RESULT: installed. Changed: values, salaries, transfer budget.`

To undo: remove the line from `sider.ini`. No file of the game is changed.

**A running career.** Salaries are stored in the contracts and the budgets were made
from the old numbers. With the module on, values change at once, salaries only at a new
contract, where they will be two to four times the old ones, and the budgets stay as
they are. For a running career set `SALARY = false`, or start a new career.

### The first test in the game

Nothing of this module has been compared with the game yet. One look settles most of it:

1. Set `SPREAD = 0` for this test, start the game, open a career and look at a player
   whose rating, age and registered position you know.
2. His value must be `VALUE x AGE x POSITION` of the tables (the log prints the first
   two), plus 10 percent per 1,000 popularity points, which you cannot see: for a known
   player at a big club that is 5 to 10 percent on top.

For Bruno Fernandes as he was in the user's career (rating 89, popularity 955), whose
value was 36,743,200 without the module:

| age | as AMF, `SPREAD = 0` | as AMF, `SPREAD = 12` | as CMF, `SPREAD = 0` |
|---|---|---|---|
| 31 | 73,877,500 | 65,012,200 to 82,668,900 | 70,359,500 |
| 32 | 53,191,700 | 46,808,700 to 59,521,500 | 50,658,800 |
| 33 | 38,416,200 | 33,806,200 to 42,987,700 | 36,586,900 |

An exact match with `SPREAD = 0` shows that the routine runs in the game and that age
and position are read from the right places. Then set `SPREAD` back: the same player
must show the same value on every screen and after leaving and opening the career
again. If it changes from one look to the next, the id is not where the routine reads
it; set `SPREAD = 0` and report it.

For the budget, start a new career with the module on and note the transfer budget of
the club. The game adds 3 times the mean value of the best 16 where it added 2 times;
if the budget starts from nothing, which is not known, the figure is 1.5 times what the
same club gets with `BUDGET_TRANSFER = false`.

### How it works

Up to four places of the game's code are changed and a piece of unused memory is filled
(`money_cave.py` has the layout and the source of the four routines):

| where | before | after |
|---|---|---|
| `0x038ab8db`, 17 bytes, fee function | `9,000 x max(0, rating - 68)` into `edi` | call to the value routine; it also sets the factor of the salary part to 0 |
| `0x038ac875`, 7 bytes, salary function | start of the 98 bytes that compute the rating part | call to the salary routine, jump over the rest |
| `0x038adc47`, 5 bytes, budget function | the mean value of the best 16, doubled | call to a routine that multiplies by `BUDGET_TRANSFER` |
| `0x038add08`, 8 bytes, budget function (only with `BUDGET_SALARY`) | wage bill + twice the mean salary of the best 16 | call to a routine that uses `BUDGET_SALARY` in place of the 2 |
| `0x047b0200`, 1,472 bytes | zero | five tables, seven numbers, four routines of 165, 53, 26 and 22 bytes |

The memory is the end of the code section `.trace`: its content ends at `0x047b005d` and
its last page runs to `0x047b0fff`. The section is readable, writable and executable in
the exe's header, so the routines can run there whatever Sider does with the page
protection. No call or jump of the exe goes into that range or into the changed places.

What the routines read of a player record: the age (6 bits at `+0x1c`, bit 7) and the
registered position (4 bits at `+0x04`, bit 28), which is where the game's own getter
`fcn_038278b0` reads fields `0x2b` and `0x00`; the popularity (`+0xb4`, bit 11) as the
fee function itself does; the id (`+0x2c`, `+0x30`) as the rating function does.

Order of the module's work: check the settings; build the tables; compare 785 bytes of
the game's code, in seven pieces, with what the exe file has (the code around the
changed places, the place where the salary function gets the player record, the two
getters); see that the memory is all zero; write tables and routines; read them back;
only then change the places one by one and read each back. If a comparison fails,
nothing more is written.

### What the test shows

```
python3 test_money.py ~/pes-work/game/PES2017.exe
ok 0: without the module the emulated game gives the amounts of ../tools/money.py, and its budget function adds twice the mean of the 16 highest fees and the wage bill plus twice the mean of the 16 highest salaries
ok 1: the module passes its checks, writes only its memory and the places it reports, and what it wrote is what money_cave.py builds from the same settings
ok 2: with the changes in, the game's salary, fee and budget code give the amounts of money_cave.py for 3000 + 3000 random players (ratings 40 to 255, ages 0 to 63, every position, with and without the random change) and 150 squads of 0 to 40 players
ok 3: SALARY = false and BUDGET_TRANSFER = false leave those places alone and the game's own amounts come out; BUDGET_SALARY changes the salary budget; with spread, position and salary age switched off the value is VALUE x AGE plus popularity; with every setting at its limit the code and money_cave.py still agree
ok 4: WRITE = false, one changed byte at 21 places of the checked code, memory not empty, 11 kinds of faulty settings: nothing is written; a write that does not stick: the code is not touched
ok 5: Bruno Fernandes as the user saw him (rating 89, salary 7,259,700, value 36,743,200): the game's formula gives exactly that value from that salary with popularity 955, and with no other rating from 60 to 99
```

The test was tried against ten planted faults in the routines and the changed places
(wrong shift for the position, wrong mask for the age, the id read with its unused upper
half, wrong table for the salary age, wrong step of the spread, wrong divisor of the
popularity bonus, wrong number slot or wrong sum in the budget routines, a call one byte
off). Nine made it fail. The tenth, leaving out the `test esi, esi` at the end of the
transfer budget routine, cannot be seen in the emulator: the jump after it reads the
zero flag, which a real processor leaves undefined after a division and the emulator
does not. The instruction is there for the real processor.

Not shown by the test: Sider's `memory.write` on the real game, the memory being empty
in the running game (the module checks it), that the records of a real career hold age,
position and id where the routines read them (the checked getters say so for age and
position), and the play of a season with the new numbers. The yearly income of a club
is not scaled; read from the code it is about 50 to 200 million a year by ranking place
(section 6.4), which should carry the new salaries, but no season was played.

## What was looked at in `sider.dll`

Read from the DLL's code and strings, not run:

- A module must return a table with an `init(ctx)` function. It gets these names:
  `log`, `memory` (`read`, `write`, `search`, `pack`, `unpack`), `string`, `table`,
  `math`, `pairs`, `ipairs`, `tostring`, `tonumber`, `type`, `unpack`, `assert`,
  `error`, `os` (`time`, `clock`, `date`), `audio`; with `luajit.ext.enabled` also
  `ffi`, `bit`, `require`. There is **no `pcall`**: an error in `init` makes Sider skip
  the module and log the error.
- `memory.read(address, count)` makes the pages readable and writable
  (`VirtualProtect`), copies the bytes, and asks for the old protection back with a
  call that Windows refuses (no place for the old value is passed). So **a read leaves
  the touched pages marked writable**. No byte changes. Every Sider module that reads
  memory does the same.
- `memory.write(address, bytes)` does the same and copies the other way, so it can
  change code. That is the route for the tuning modules. It gives the pages the
  protection "read, write, execute" (`0x40`) before the copy; if Windows refuses that,
  the module stops with an error and Sider skips it.

## Notes for the next module

- The exe has a fixed load address (no relocation table, no dynamic base), so the
  addresses of `MASTER_LEAGUE.md` are valid in the running game. `MLCheck.lua` tests
  exactly this.
- The level values are single bytes inside `mov eax, value` instructions; 68 and 9,000
  of the fee formula are numbers inside two instructions; 0.00027 is a constant with
  one user. All four can be changed in place.
- **The 2.2 of the fee formula is a shared constant** (`0x01f0f2b8`, 16 references in
  the exe). It must not be changed in place; the fee function has to be pointed to a
  constant of its own. (`MLMoney.lua` does not need it: its routine sets the factor of
  the salary part to 0 in the function's own stack frame.)
- Free memory for code and tables: `0x047b0200`-`0x047b0fff`, the end of `.trace`
  (3,584 bytes; `MLMoney.lua` uses the first 1,472). A module must see zeros there
  before it writes.
