# Master League in `PES2017.exe`: what the code does

This file collects everything found so far about the Master League code of
`PES2017.exe`: where the mode keeps its data, how a day is processed, the year plan
(calendar), salaries, transfer fees, negotiations, scouts, the squad planning of the
computer clubs, team roles, and the save file. It is written from the decompiled C in
`output/`, from disassembly where the C lacks the arithmetic, and from running single
functions of the exe in an emulator.

**Read this first: how sure each part is.** The code of the career day is
large: the 72 step functions of appendix A alone are 27,010 lines of C, and they call many
more. Three pieces are proven, a larger part is read, and most of the rules are only
located. Each section says which of these four levels applies:

| level | meaning |
|---|---|
| **proven** | the game's own machine code was run on thousands of inputs and gave the same result as the Python in `tools/` (`check_findings.py`, checks 7 to 9) |
| **read** | the C or the disassembly was read and the text below follows it; not run |
| **inferred** | the purpose is concluded from what the code touches, when it runs and who calls it; the name may be wrong |
| **located** | the function is found and listed, its body is not read |

Nothing here was seen in the running game. The exe cannot run in the work environment,
and no Master League save file is in the repository, so no number below has been
compared with a real career. Function names are working names of mine
(`names.tsv`); the exe has no symbols. Field meanings marked "?" are not established.

Contents: [1 Proven](#1-what-is-proven) · [2 Frame](#2-the-frame-mode-data-records-random-numbers) ·
[3 Day](#3-how-a-day-is-processed) · [4 Year plan](#4-the-year-plan-calendar) ·
[5 Fixtures](#5-fixtures-and-match-days) · [6 Money](#6-money-salary-fee-wage-bill) ·
[7 Negotiations](#7-negotiations-of-the-users-club) · [8 Scouts](#8-scouts) ·
[9 Computer clubs](#9-transfers-of-the-computer-clubs) · [10 Strength](#10-team-strength) ·
[11 Roles](#11-team-roles) · [12 Growth](#12-growth-team-spirit-youth-retirement) ·
[13 Save](#13-the-master-league-save-file) · [14 Not found](#14-not-found-not-read) ·
[15 How to go on](#15-how-to-go-on) · [Appendices A to F](#appendix-a-steps-of-a-day)

## 1 What is proven

```
python3 check_findings.py ~/pes-work/game/PES2017.exe "../../EDIT00000000 (pes 2017 updated)"
7 ok: the game's salary code (fcn_038ac66e) and money.salary give the same amount for 3000 random players (awards and title bonuses not run)
8 ok: the game's transfer fee code (fcn_038ab832) and money.fee give the same amount for 3000 random cases, with and without the random change
9 ok: the game's year-plan code (fcn_038b0b21) and yearplan.events put the same events on each day (8928 days: four modes, both season kinds, flags on and off)
```

- **Salary formula** (section 6.1), `tools/money.py`.
- **Transfer fee formula** (section 6.2), `tools/money.py`.
- **Year plan**: which event falls on which day, for Master League, Become a Legend,
  League mode and the other modes, for both kinds of season (section 4),
  `tools/yearplan.py`.

How the proof works: `emu.py` runs the function's machine code. The functions it would
call to fetch a player, a ranking place or a random number are answered with chosen
values (`Game.replace`), so the arithmetic that runs is the game's. What this does
**not** prove: that the inputs I name (rating, ranking place, …) are what the game feeds
in during a career. That part is read, not run. Each check was also tried
against a wrong formula (one event dropped, one fee rule dropped, one salary off by
1) and failed as it should.

## 2 The frame: mode data, records, random numbers

Level: **read**.

### 2.1 Where the mode lives

| what | where | note |
|---|---|---|
| mode object | pointer at `0x026503e0` (`mode_object`, `fcn_0381c0e5`, 3,003 callers) | `+0x30` = pointer to the **mode data**, one block of more than 15 MB |
| menu / mode selector | pointer at `0x0264f3e8` (`fcn_03808865`) | `+0x20` = number of the running mode, 0 to 69 |
| mode kind | `mode_kind` (`fcn_038093f1`): table `0x0251d408[mode number]` | **11 = League, 12 = Master League, 13 = Become a Legend**; the other values are the other modes |

Mode numbers 19 and 40 give kind 12; 18 and 39 give 11; 20 and 41 give 13. That 12 is
Master League is concluded from the code: the kind-12 branches are the ones that run
negotiations, scouts and club accounts, and kind 13 reads one player id at
`+0xe4a528` (the Become a Legend player).

### 2.2 The mode data (offsets from the pointer at `+0x30`)

| offset | size | what |
|---|---|---|
| `0x552e80` | 300 × `0x224` | competition records; count at `0x5fece8`; empty record at `0x5fe840` |
| `0x5fe320` | | empty team record (returned when a team id is not found) |
| `0x6f154c` | 9,000 × `0x24c` | match records (every fixture of the season) |
| `0xbfd52c` | 365 × `0x214` | **calendar**: one record per day of the year (section 4) |
| `0xc2cbb0` | u16 | today, as day number of the year, 0 to 364 |
| `0xc2cbb2` | u16 | the year |
| `0xcc84cc` | | club ranking: rows of `0x10` bytes, count at `+0x28a0`; `fcn_03138333(club)` returns the number stored for the club (taken to be its place) |
| `0xccb80c` | 851 × `0x118` | squad plan of each club (section 9); count at `0xd06434` |
| `0xd06438` | 70 × `0x1dc` | **deal records** of the user's club (section 7) |
| `0xd0f154` | 3 × `0x1e4` | three search slots with 16 results each; taken to be the scouts (section 8) |
| `0xdcb68c` | date | a stored date compared with today in many steps (meaning ?) |
| `0xddce6d` | byte | when set, most Master League steps of the day are skipped (meaning ?) |
| `0xddcf02` | u16 | **seed of the mode's random numbers** |
| `0xddcf04` | u32 | when not 0, the transfer and report steps are skipped (meaning ?) |
| `0xdddef0` … `0xddf74c` | | club accounts; `0xddf74c` low 24 bits = a money figure set each day from `fcn_03878855` |
| `0xe4a528` | id | the Become a Legend player |
| `0xed3620` | | empty player record |

A date is four bytes: year (u16), month, day. `today` (`fcn_038ae451`) builds it from
the day number with the month table at `0x0216bb60` (12 rows: month, first day number,
last day number; February has 28 days, there is no leap day).

### 2.3 Records

Look-up functions:

| function | returns |
|---|---|
| `player_record` (`fcn_03822835(id, id2)`, 502 callers) | player record; a player id is two numbers |
| `team_record` (`fcn_03822969(id)`, 500 callers) | team record; a team id has 14 low bits and a high part |
| `competition_record` (`fcn_03822ab9(id)`, 403 callers) | competition record |
| `match_record` (`fcn_03822b3f(number)`, 183 callers) | match record |
| `player_value` (`fcn_038278b0(field, out)`, 302 callers) | one of 98 packed fields of a player |

Fields seen in use (offsets inside the record; "?" = meaning not established):

| record | offset | what |
|---|---|---|
| player | `+0x2c`, `+0x30` | the id pair |
| player | `+0xb4` bits 0-3 | status (the values 2, 3, 4 and 6 are tested) ? |
| player | `+0xb4` bits 11-22 | **a number 0 to 4095, called `x` below**: it raises salary and fee. Meaning ? (candidates: fame, popularity) |
| player | `+0xb8` bits 26-27 | level of the team role, 0 to 3 |
| player | `+0xb8` bit 28 | a mark, called "own" bit below: players with it are left out of the wage bill, and it changes the fee (section 6.2). Meaning ? |
| player | `+0xb8` bits 29, 30 | marks set by the squad planning of computer clubs (section 9) |
| player | `+0xc4` | team role, one byte (section 11) |
| player | `+0xcc` | **salary** (the wage bill sums it; the fee starts from it) |
| team | `+0x4a` | name |
| team | `+0xf8` | squad: 8 bytes (id pair) per player |
| team | `+0x328` bits 9-15 | number of players in the squad |
| competition | `+0x21c` bits 30-31 | a kind used when the fixtures are made (section 5) |

Player fields used by the money and negotiation code (`player_value`): field `0x2b` =
age (the code tests it against 36, 37 and 45), field `0x20` ?, field `0x2e` ? (0 to 7). The numbering is the game's own, not that of the edit
file, so `output/edit_fields.tsv` does not name them.

### 2.4 Random numbers

`mode_random` (`fcn_03855998(&n)`, 141 callers) returns a number from 0 to n-1:

```
seed = u16 at mode data + 0xddcf02
srand(seed)
r    = (rand() * rand()) mod n            # the result
seed = ((r + 1) * n + seed) mod 65535     # stored back
```

Every chance in the mode goes through this one function and one 16-bit seed that is
part of the mode data. So the same save, continued the same way, draws the same
numbers. (Read; whether the seed is saved with the career is not checked.)

The 141 callers are a map of where chance enters the mode; the large ones are listed
in appendix A.

## 3 How a day is processed

Level: **read** for the frame; the steps themselves are **located** or **inferred**.

Four task classes (names from the exe's own type records) drive the career day:

| class | worker | body |
|---|---|---|
| `process::CmnUpdateDayBegin` | `process::UpdateDayBeginThread` | `day_begin` `fcn_0360a350` (531 lines) |
| `process::CmnUpdateDayEnd` | `process::UpdateDayEndThread` | `day_loop` `fcn_0360dbf0` → `day_end` `fcn_0360bf0c` (1,032 lines) |
| `process::CmnUpdatePostMatch` | `process::UpdatePostMatchThread` | `fcn_03611162` → `fcn_03611277`, `fcn_036101d9` |
| `process::CmnUpdateSeasonEnd` | | `fcn_035feb08` (not read) |

The day-end worker also advances the days on which the user has nothing to do:

```
day_end()
while not day_loop_stop():        # fcn_0360b713: stops when day_state() == 2
    day_begin()                   # the next day
    after_matches_1()             # fcn_03611277
    after_matches_2()             # fcn_036101d9
    day_end()
```

`day_state` (`fcn_03877938`, 525 lines, 17 callers) is asked by almost every step. The
value 2 stops the loop, so it means "the user has to act today"; the other values are
not worked out.

Each step is an object that is created, run once and freed. The steps that run only in
Master League (kind 12), in the order of the code:

**Day begin** (`fcn_0360a350`):

1. Each of the 70 deal records whose state is not 3 or 4 gets a new number from 1
   to 100 (`+0x1d4`); taken to be the record's chance number for the day.
2. On event 48 a byte (`+0xddce81`) is cleared. On event 1 (first day of the
   season): the year plan is written (`fcn_035d8b2e`, section 4) and `fcn_036336b0`
   runs.
3. `fcn_03640d19` (1,280 lines): the money step. It asks for events 3, 23, 25 and 49
   and uses the wage bill and team strength (not read). Then, for all modes,
   `fcn_0387585e(1)` when the test at `0x03671c55` says so (section 5).
4. On events 3 and 6 (a window opens): `fcn_0382e072`.
5. `fcn_03664a3d`; `negotiation_day_begin` (`fcn_0365c89a`) which on events 3 and 6
   runs the negotiation step once for all records; `fcn_03661f6b`; `fcn_036e20d2`;
   `fcn_036dfd10`; `fcn_03656fa5` (449 lines, uses random numbers, rating, salary,
   team strength); `fcn_0364b81c` (event 11).
6. On events 31 and 45: `fcn_03676016`.
7. `mode data + 0xddf74c` is set from `fcn_03878855`; `fcn_0362579a`; `fcn_036523fb`.

**Day end** (`fcn_0360bf0c`):

1. On events 5 and 8 (a window closes) a mark is set for the screens.
2. `fcn_036696e1` and `fcn_0362eb70` (events 41 to 44; they belong to the
   `process::SpecialTitle…` classes). Not read.
3. `fcn_03664d29` (event 9) → `fcn_0366365b` (769 lines; section 9.3).
4. `fcn_0365692c`, only when `day_state` is 2: for each deal record with state 2, 3
   or 12 that is not of kind `0x20`, thirteen numbers (26 to 38) are tried. Each has
   a chance in thousandths from `fcn_0365293e`, lowered by 150 (by 300 in April and
   October, by 1,000 in March and September); it passes if `rand(1000)` is not above
   the rest. What passes is collected and handed on (`fcn_03655628`, 203 lines, uses
   random numbers). What the 13 numbers stand for: not read.
5. `negotiation_day_end` (`fcn_0365cbbc`): on event 9 (a window day) the negotiation
   step runs (section 7). Then `fcn_036e2d84` (event 9) → `fcn_036e2557`.
6. `fcn_0365df66`, `fcn_036e1568`, `fcn_036e067a`, `fcn_0364c065`, `fcn_0366f4bb`.
7. `fcn_0366d620`, `fcn_03640686`, `scout_step` (`fcn_03652198`, section 8).
8. On event 8 (second window closes): `fcn_0385e248` builds a list for team **4971**
   and `move_players` (`fcn_0389734b`) runs on it. Team 4971 is the empty slot
   "The Old Boys" of the edit file. What is moved is not read.
9. `fcn_0363beba` (event 48, report), `fcn_03634561`.
10. On event 23 (last day of the season): the byte `+0xdd064d` is set and the
    season-end block follows (about 400 lines of the same function, not read; near
    its end the year plan is written again and `fcn_0387585e(1)` is called).

Appendix A lists every step with its size, the events it asks for and what it uses.

## 4 The year plan (calendar)

Level: **proven** for the dates; the meaning of each event is **read** or **inferred**
as marked.

### 4.1 The calendar record

`mode data + 0xbfd52c` holds 365 records of `0x214` bytes, one per day:

| offset | what |
|---|---|
| `+0x000` | up to 200 match numbers (i16) played that day; `-1` = empty |
| `+0x190` | number of matches (u16) |
| `+0x194` | 16 event slots of 8 bytes: event number (u16), a mark (i16), a date; at most 9 are written per day |

`event_on_date` (`fcn_038ae7ca(&event, &date)`, 66 callers) and `event_on_day`
(`fcn_038558cc(&event, &day number)`, 31 callers) answer "is this event on that day".
All timed rules of the mode hang on these two questions.

### 4.2 Where the events come from

One table in the exe, `0x0216bc20`, 169 rows of `0x14` bytes:

| offset | what |
|---|---|
| `+0x00` | month (u8) |
| `+0x02` | day (u16) |
| `+0x04` | event number |
| `+0x08` | 1 = only in the career modes (Master League, Become a Legend) |
| `+0x09` | 1 = not in Become a Legend |
| `+0x0c` | a number written with the event (meaning ?) |
| `+0x10` | kind of season: 0 = season from 1 July, 1 = season from 1 January, 3 = both |

On the first day of a season (event 1) `year_plan_write` (`fcn_035d8b2e`) walks from
today to day 364 and on from day 0, and for each day calls
`year_plan_day` (`fcn_038b0b21`), which picks the rows of that date:

- the row's season kind is 3 or equals the season kind of the user's league;
- Master League takes every row; Become a Legend takes rows with `+0x09` = 0; all
  other modes take rows with `+0x08` = 0;
- event 29 only if the byte at mode data `+0xdcb686` is set;
- events 32 to 39 (draws) not if mode data `+0xdc9d78` is `0x56` (and, outside the career
  modes, not if the byte at `+0xdc9cbc` is 2 or more);
- events 19 and 20 not in May and June of a year with `year mod 4 = 1`;
- event 48 not in February and September if the byte at `+0xddce71` is set.

The season kind comes from `season_kind` (`fcn_0385adf6`): a table of 92 league ids at
`0x021687d0` (appendix D). Kind 0 = the season runs from 1 July to 30 June; any other
kind = from 1 January to 31 December. Outside the three career modes the January
season is always used.

`python3 yearplan.py <exe> july` (or `january`) prints the year.

### 4.3 The Master League year, season from 1 July

Event 9 is on every day of July, August and January.

| date | event | what |
|---|---|---|
| 1.7. | 1 | first day of the season: the year plan is written |
| 1.7. | 3 | first transfer window opens |
| 26.7. | 45 | asked by fcn_03676016 (not read) |
| 4.8. | 10 | asked by fcn_0364c065 and the staff report (not read) |
| 20.8. | 19 | taken to be a national team day (six a year) |
| 21.8. | 20 | the day after event 19 |
| 26.8. | 42 | title step of fcn_0362eb70 (process::SpecialTitleSetUEFA, not read) |
| 27.8. | 32 | draw day (process::ProcessCmnLotCheck) |
| 27.8. | 27 | asked by fcn_0366f4bb and news functions (not read) |
| 30.8. | 4 | day before the first window closes (the daily scout step is left out) |
| 31.8. | 5 | first transfer window closes |
| 1.9. | 30 | day after a window closes: computer clubs plan their squads (fcn_036602e5) |
| 21.9. | 19 | taken to be a national team day (six a year) |
| 22.9. | 20 | the day after event 19 |
| 25.9. | 48 | report step fcn_0363beba (writes a staff report; not read) |
| 26.10. | 19 | taken to be a national team day (six a year) |
| 27.10. | 20 | the day after event 19 |
| 7.11. | 11 | asked by fcn_0364b81c (not read) |
| 10.12. | 33 | draw day (process::ProcessCmnLotCheck) |
| 10.12. | 34 | draw day (process::ProcessCmnLotCheck) |
| 12.12. | 11 | asked by fcn_0364b81c (not read) |
| 28.12. | 44 | title step of fcn_0362eb70, fcn_036696e1 (not read) |
| 29.12. | 43 | title step of fcn_0362eb70, fcn_036696e1 (not read) |
| 29.12. | 31 | asked by fcn_03676016 (not read) |
| 29.12. | 11 | asked by fcn_0364b81c (not read) |
| 30.12. | 28 | asked by fcn_0366f4bb and news functions (not read) |
| 31.12. | 12 | half-year step of fcn_036e1665 (not read) |
| 31.12. | 24 | asked by fcn_03649f1f, 616 lines (taken to be the closing of the accounts) |
| 31.12. | 15 | half-year step of fcn_036e067a, fcn_036e1568 (not read) |
| 31.12. | 22 | asked by fcn_0314910f only (not read) |
| 1.1. | 25 | money step fcn_03640d19; asked by process::ProcessCmnFinanceReportCheck |
| 1.1. | 6 | second transfer window opens |
| 8.1. | 41 | title step of fcn_0362eb70, fcn_036696e1 (process::SpecialTitle, not read) |
| 11.1. | 26 | asked by fcn_0366f4bb and news functions (not read) |
| 30.1. | 7 | day before the second window closes (the daily scout step is left out) |
| 31.1. | 8 | second transfer window closes |
| 1.2. | 30 | day after a window closes: computer clubs plan their squads (fcn_036602e5) |
| 6.3. | 17 | asked by fcn_036f5728 (not read) |
| 7.3. | 16 | asked by the staff report and a transfer news function (not read) |
| 15.3. | 19 | taken to be a national team day (six a year) |
| 16.3. | 20 | the day after event 19 |
| 19.3. | 35 | draw day (process::ProcessCmnLotCheck) |
| 19.3. | 36 | draw day (process::ProcessCmnLotCheck) |
| 16.4. | 37 | draw day (process::ProcessCmnLotCheck) |
| 16.4. | 38 | draw day (process::ProcessCmnLotCheck) |
| 9.5. | 11 | asked by fcn_0364b81c (not read) |
| 25.5. | 19 | taken to be a national team day (six a year) |
| 26.5. | 20 | the day after event 19 |
| 28.5. | 39 | draw day (process::ProcessCmnLotCheck) |
| 13.6. | 11 | asked by fcn_0364b81c (not read) |
| 22.6. | 19 | taken to be a national team day (six a year) |
| 23.6. | 20 | the day after event 19 |
| 25.6. | 48 | report step fcn_0363beba (writes a staff report; not read) |
| 28.6. | 11 | asked by fcn_0364b81c (not read) |
| 28.6. | 31 | asked by fcn_03676016 (not read) |
| 28.6. | 49 | money step fcn_03640d19 |
| 30.6. | 14 | half-year step of fcn_036e1665 (not read) |
| 30.6. | 24 | asked by fcn_03649f1f, 616 lines (taken to be the closing of the accounts) |
| 30.6. | 13 | half-year step of fcn_036e067a, fcn_036e1568 (not read) |
| 30.6. | 23 | last day of the season: season-end processing |

For a league with a January season the two halves change places: the first window is
1 to 31 January, the second 1 July to 31 August, the season ends on 31 December
(`yearplan.py <exe> january`).

### 4.4 What the dates say

- **Two transfer windows**: 1 July to 31 August and 1 to 31 January (events 3-5 and
  6-8), with the daily step (event 9) on every day inside them.
- **1 September and 1 February** (event 30): the computer clubs plan their squads.
- **30 June and 31 December** (events 12 to 15, 24): half-year steps. Contract ends,
  loan returns and the closing of the accounts are expected here; the functions are
  located, not read.
- **Six dates with a day after** (events 19, 20), dropped in May and June every
  fourth year: taken to be the national team days.
- **Eight draw days** (events 32 to 39, asked by `process::ProcessCmnLotCheck`) and
  four title days (41 to 44).
- **25 June and 25 September** (event 48): a report step.

Appendix F lists, for each event, the functions that ask for it. That table is the
map from a date to the code that acts on it.

## 5 Fixtures and match days

Level: **located**, a little **read**. This part is the least understood.

- Every fixture of the season is a match record (9,000 × `0x24c` at `0x6f154c`). A day
  of the calendar holds the numbers of its matches (up to 200).
- Competitions are records of `0x224` bytes (300 at `0x552e80`).
  `process::LeagueCreation` (`fcn_037741b4`) picks one of four functions by
  competition id: ids 600-607, 1000-1011 and 3000-3007 → `fcn_03773791`; ids
  1800-1807 and 15400-15407 → `fcn_037738c1`; ids 6800-6807 → `fcn_037739f1` or
  `fcn_03773791` by two bits of the competition record (`+0x21c`, bits 30-31); all
  others → `fcn_03774035`. `process::KnockOutCreation` is `fcn_0376ee12`. These are
  not read, so **how the rounds are paired and put on dates is not known**.
- `process::CmnScheduleProcessCheck` (`fcn_03607db9`, `fcn_03607e8c`) and
  `process::CmnMonthlyScheduleCheck` belong to the schedule screens (not read).
- `fcn_0387585e` (1,085 lines, 9 callers, uses random numbers and `move_players`,
  called from the day begin and from the season end) is not read. What it does is
  open. It runs for all modes and is the second caller of `move_players`.
- `fcn_038a7cf9(competition)` (37 callers) is asked before most competition steps;
  it walks the parent competitions (meaning ?).

## 6 Money: salary, fee, wage bill

Amounts are whole numbers; the largest is **99,999,900** (`0x5f5e09c`).
`money_text` (`fcn_03869870`) prints a 64-bit amount with thousands separators and no
scaling. Whether the screens add a unit or a factor is not checked.

### 6.1 Salary: `salary` = `fcn_038ac66e(player, club, …)`

Level: **proven** (check 7) for the formula below; the award and title bonuses are
**read**.

```
o  = overall rating of the player (best position, with condition)
x  = the 12-bit number of the player record (+0xb4, bits 11-22)

A  = 30*o - 500
B  = 300*max(0, o-65) + 500*max(0, o-75) + 700*max(0, o-85)
X  = x
     + 2*(5*x - 4000)   if x > 800
     + 4*(5*x - 9000)   if x > 1800
R  = role bonus (below)
f  = 1 + 0.004*(251 - rank)   if rank <= 250, else 1
T  = (0, 0, 0, 1000, 3000, 5000, 10000, 15000)[band];  if T > 0: T += 20 * field 0x20
salary = trunc((R + X + B + A) * f) + T + awards        limited to 1 … 99,999,900
```

- `rank` is the place of the club in the mode's club ranking (`fcn_03138333`); 300 if
  the club is not in it. So the first club of the ranking pays twice what a club
  below place 250 pays for the same player.
- `R`, by the role byte (`+0xc4`) and the role level (1 to 3): roles 5, 6, 8 →
  1,000 / 2,000 / 3,000; roles 7, 9, 14 → 5,000 / 7,500 / 10,000; role 18 → 3,000;
  role 19 → 15,000; other roles → 0.
- `band` comes from `fcn_0385400e` (29 callers): field `0x2e` of the player, at most
  7; when that is 6 or 7 the band is counted from the rating against the steps 50,
  55, 60, 70, 80, 85, 88. Read; the exact count is not settled. In the proof the band
  was a free input from 0 to 7.
- `awards` (read, not run; skipped for status 6): +10,000, +5,000, +5,000, +5,000 if
  the player holds one of four awards (`fcn_0318c209(0 … 3)`), and +2,000 for each
  entry of his in the lists of finished competitions (`fcn_035e5fa7`).
- Clubs whose league number (`fcn_03879e04`) is 60, 61 or 62, and in mode number 40
  players with status 3 (or status 2 and a certain mark) who have an entry number at
  `+0xbc`, use another formula, `fcn_038ab5ea`:
  `700*(o-70)` above rating 71,
  `(x-150) * club factor` above x = 500 (factor from `fcn_038aaad2`, table
  `0x0216b8f8` of 42 clubs with a tier 1 to 5), `10*o`, a ranking factor
  `1 + 0.01*(101 - rank)` up to place 100, and a band bonus
  (0, 0, 1,000, 2,000, 3,000, 5,000, 10,000, 20,000). Read, not run.

Worked example (rank 1, no role, band 0): rating 80, x = 0 →
`A = 1900`, `B = 4500 + 2500 = 7000`, `f = 2.0` → **17,800**. Rating 90, x = 2,000 →
`A = 2200`, `B = 7500 + 7500 + 3500 = 18,500`, `X = 2000 + 12,000 + 4,000 = 18,000`,
→ `38,700 * 2` = **77,400**.

### 6.2 Transfer fee: `transfer_fee` = `fcn_038ab832(player, &figure, &kind, &random, &flag)`

Level: **proven** (check 8).

```
base   = the figure handed in, or the player's salary (+0xcc) if it is 0
factor = 2.2 + 0.00027 * x
fee    = trunc(base * factor) + 9000 * max(0, o - 68)
if kind != 0 and the player's "own" bit is clear:  fee = base
if random:
    kind 1:  p = -rand(50)          # down by up to 49 %
    kind 2:  p = +rand(50)          # up by up to 49 %
    else:    p = +rand(20) or -rand(20), sign from rand(2)
    if p == 0: p = 1
    fee += trunc(fee * p / 100)
limited to 1 … 99,999,900
```

So the fee is the **salary times 2.2 to 3.3** (by `x`) plus **9,000 for every rating
point above 68**. With the two examples above: 17,800 → `39,160 + 108,000` =
**147,160**; 77,400 with x = 2,000 → `77,400 * 2.74 + 198,000` = **410,076**.
What `kind` stands for (values 0 to 3) is not established.

### 6.3 Wage bill: `wage_bill` = `fcn_038ad7a8(club, recompute)`

Level: **read**. Sum of the salaries (`+0xcc`) of the squad, leaving out players with
the "own" bit. For one club (the id comes from a setting; taken to be the user's
club) the players of deal records in state 13 are added.
With `recompute` the salary formula is run for each player instead of the stored
figure. 8 callers, among them the money step and the closing of the accounts.

### 6.4 Club money

Level: **located**. `fcn_03640d19` (money step, events 3, 23, 25, 49),
`fcn_03649f1f` (616 lines, event 24), `fcn_038adf0c`, `fcn_038ad9c4`,
`process::ProcessCmnFinanceReportCheck` (`fcn_035e69ce`, event 25),
`fcn_03878855` and about twenty small functions at `0x038aa000`-`0x038ab400` that
add and read account lines. Income, prize money, sponsors and the budget rule are
**not read**.

## 7 Negotiations of the user's club

Level: **read** in part; arithmetic on fractions is lost in the C at several places,
so the numbers below are what could be followed. Not run.

### 7.1 The deal record

70 records of `0x1dc` bytes at `mode data + 0xd06438`. One record is one player the
user's club is dealing with. Dwords of the record:

| dword | what |
|---|---|
| 0, 1 | player id |
| 5, bits 0-3 | **state**, 0 to 13 |
| 5, bits 4-7 | kind of deal; `0x20` is treated apart (taken to be a loan) |
| 5, bits 8-11 | a small number from `fcn_0388a1be` (taken to be contract years) |
| 10, 11 | the two money figures of the club's answer |
| 14, 15, 16 | three extra figures, each made by `fcn_038a9dc5` from figure 11 |
| 18-21 | two more player ids (players offered in exchange) |
| 25 | date on which the other side answers |
| 28 | the `kind` handed to the fee formula |
| `+0xf8` | five entries of `0x20` bytes: other clubs in the same deal, each with a day counter |
| `+0x1d4` | the day's chance number, 1 to 100 |

### 7.2 The step

`negotiation_step` (`fcn_03659b50`, 1,621 lines) walks the 70 records. It runs at the
day end of every window day (event 9) and at the day begin of the days a window opens
(events 3, 6). On the daily run the day counters of the five other clubs go down by 1.
Then a switch on the state (13 cases). For state 2, when the answer date is reached:

1. The deal ends at once (state → 8) if the player's record has bit 31 of `+0xb4`
   set, if his status is 4, or if his age is 45 or more.
2. The salary formula is run for the player at the user's club, the fee formula for
   the fee, and `fcn_0388a1be` for the years.
3. `n` = how many of the five other-club entries are in use; a factor
   `0.9 + 0.1 * n` enters one of the figures. More clubs after the player, higher
   price.
4. If the player is in one of the 3 × 16 result lists at `+0xd0f154` (section 8), the
   first figure is cut to **70 %**.
5. Two scores from 0 to 100 are computed (`fcn_0389b3f8`, 352 lines, and
   `fcn_0389bd94`, 276 lines; both use rating, the squad and `fcn_0389a28a`); the
   lower one counts. Below 100 it raises the first figure by
   `(100 - score) / 100` of something (operands lost).
6. Unless the player's status is 2: three draws of `rand(100)` against
   `fcn_03896290`, `fcn_03896c26` and `fcn_0389675b` (three functions of 169 lines
   each; not read) decide whether the three extra figures are asked.
7. Two more draws of `rand(100)`. The first is compared with the score; if the score
   is 40 or less and the second draw is below 10, the marks `2` or `4` are set in
   dword `0x76` and a figure is raised. On the paths the C shows, the state becomes 5
   and the figures are stored. **What a draw above the score leads to cannot be told
   from the C** (the decompiler drops branches here); the disassembly was not read.
8. The figures are stored in dwords 10 and 11 after `money_clamp`
   (`fcn_038a9d95`), the years in dword 5.

States seen being set: 5 (with a "new" mark at `+0x1ce`, as for 6 and 11) and 8
(the mark is cleared). So 5 is taken to be "answer received" and 8 "ended". The other
cases of the switch are not read. In case 0, `fcn_03658eda` (422 lines) is called; it
tests events 5 and 8, reads the club plan records and uses the salary and fee
formulas. Case 3 follows the pattern of case 2 with `fcn_03657dcd` and
`fcn_03658371`. `fcn_03658821` (225 lines, event 9) calls `complete_transfer`.

The screens: `menu::MenuModeMLNegociationMenu`, `…List`, `…Detail`, `…Adjust`,
`…CountDown`, `…Dialog` (appendix B). `MenuModeMLNegociationDialog` calls
`fcn_0388d7fb` (633 lines) and `fcn_03898af6` (720 lines; uses salary, fee and
`complete_transfer`). `complete_transfer` (`fcn_0389840a`, 11 callers) →
`fcn_038913b5` (745 lines). Not read.

## 8 Scouts

Level: **inferred** that these are the scouts; the step is **read**.

`mode data + 0xd0f154` holds three records of `0x1e4` bytes: a player id pair, a byte
"in use" at `+0x1c`, 16 results of `0x1c` bytes from `+0x20`, and a date at `+0x1e0`.
Three slots with a list of 16 players each, a search that takes days, and the 30 %
cut in the negotiation fit the scouts of the menu (`menu::ModeMLScoutMenu`,
`ModeMLScoutingSettings`).

`scout_step` (`fcn_03652198`) runs at each day end when the byte `+0xdd0655` is set
and today is not the date at `+0xdcb68c`, except on the day before a window closes
(events 4, 7):

```
n = number of slots in use (1 to 3)
for each slot in use:
    if rand(1000) < 30 / n:          # 3 %, 1.5 % or 1 % a day
        scout_search(slot)           # fcn_0364f2ca
    else if 14 days or more have passed since the slot's date:
        (a second branch; what it does was not followed)
```

`scout_search` (`fcn_0364f2ca`, 1,381 lines) uses ratings, player fields, team
strength, the fee formula, `squad_needs` and random numbers, and writes a staff
report. Its selection rule is not read.

## 9 Transfers of the computer clubs

Level: **read** in part, **inferred** as marked. The full rule by which a computer
club picks and buys a player is **not decoded**.

### 9.1 The plan record

`mode data + 0xccb80c`: up to 851 records of `0x118` bytes, one per club (count at
`+0xd06434`):

| offset | what |
|---|---|
| `+0x000` | club id |
| `+0x004` | a kind, 0 to 3 (meaning ?) |
| `+0x008` | 16 slots of `0x10` bytes: a player id pair and a word whose bits 7-13 hold a position; position 13 = the slot is empty |
| `+0x10c` | "done" mark |
| `+0x114` | a counter |

### 9.2 The planning step

`club_squad_plan` (`fcn_036602e5`, 392 lines) tests event 30 (1 September,
1 February); the last day of a window (`fcn_03889a55`: 31 January, 31 August)
changes some limits. It is called from `fcn_03661f6b` at the day begin. It handles
**at most five clubs per call**, and only clubs whose record is not marked done.
Per club:

1. The marks 29 and 30 of `+0xb8` are cleared for every player of the squad.
2. `squad_needs` (`fcn_0389440a`, 647 lines, not read) returns a list of entries of
   `0x10` bytes: a player id and a position. Entries without a player are taken to be
   the positions the club lacks.
3. Surplus = squad size (`fcn_03888d9e`) − 23. While there is a surplus, players who
   are not in the list of step 2 and whose band (`fcn_0385400e`) is below 6 (below 8
   with a chance of 1 in 5 on the last day of a window) are marked: with a chance of
   1 in 5 mark 30, else mark 29. **Taken to be "for loan" and "for sale"**; which is
   which is not established.
4. The positions without a player are written into empty slots of the plan record.
   Then, while squad size − marked players + new slots stays under 25, more
   positions from the list are added. By the record's kind a word of the slot is set
   to 20 (kind 2) or 23 (kind 3), or the kind becomes 1 with the value 6 (on the last
   day of a window). What these numbers stand for is not established.

So a computer club aims at a squad of 23 to 25, keeps the players its plan names and
those of the top bands, and marks the rest.

### 9.3 The deals themselves

- Steps of the day end that test event 9 (window day): `fcn_03664d29` →
  `fcn_0366365b` (769 lines; tests events 5 and 8; uses random numbers, the salary
  formula and `complete_transfer`), `fcn_0365df66`, and `fcn_036e2d84` →
  `fcn_036e2557` (320 lines; event 8; salary, `complete_transfer`). Not read. The
  deals between computer clubs are expected in one of these.
- `fcn_036e067a` (232 lines; events 5, 13, 15) also calls `complete_transfer`.
- `complete_transfer` (`fcn_0389840a`) has 11 callers; `fcn_038913b5` (745 lines)
  under it uses the salary and fee formulas and the club plan records.
- `move_players` (`fcn_0389734b`, 466 lines) is the only function found that writes
  the squad count of a team record together with the squad list. It has two callers:
  the day end (event 8, team 4971) and `fcn_0387585e`.

What is missing: how a computer club chooses its target, what it pays, and how often
deals between two computer clubs happen.

## 10 Team strength

Level: **read**.

`team_strength_of` (`fcn_03865b0a(&club, &kind, …)`, 34 callers) collects one value
per player of the squad (up to 32) and hands them to `team_strength`
(`fcn_04067cfa`):

```
sort the values, highest first
s = sum of the first 11
kind 6 (overall):  s / 11, limited to 40 … 99
other kinds:       s / 11 (rounded up in one mode), limited to 1 … 9, times 10
```

For kind 6 the value of a player is his overall rating at his best position with the
condition arrow (`fcn_03838c18`, the rating code of `NOTES.md`); for the other kinds
`fcn_03865a43(player, kind) / 10`. So a club's strength is the **mean rating of its
eleven best players**, whatever their positions.

## 11 Team roles

Level: **read** in part.

The role of a player is the byte at `+0xc4` (1 to 22; 0 and 23 = none) with a level 1
to 3 in `+0xb8`. Table `0x0216f85c` has one row of `0x14` bytes per role: three effect
numbers (10 = none) and a kind (appendix E). `role_effects` (`fcn_038ba942`) lists the
effects of a role.

`role_multiplier` (`fcn_038bb0f0(club)`) returns a factor for a club, starting at 1.0.
For one player of the squad (the index is the byte `+0x271` of a second club
record, taken to be the captain) the effects of his role count:

- effect 3: × (1 + 0.05 × level) → 1.05, 1.10, 1.15;
- effect 4: × 1.3; effect 5: × 1.4;
- and for every player whose role has kind 6 (role 16) and who has an entry in a second table
  (`fcn_0329d8e5`): a 7-bit value below 51 → × 0.7; 56 to 60 → × 1.1; 61 to 65 → × 1.2;
  66 and up → × 1.3.

What the factor is applied to (one caller, `fcn_038b4368`) is not read. Roles also raise the salary (section 6.1).
`menu::ModeMLTeamRoleList` is the screen; `fcn_038bbe67` (222 lines) and
`fcn_038b9378` (191 lines, a table of dates at `0x0216f518`) assign roles. Not read.

## 12 Growth, team spirit, youth, retirement

Level: **located**. None of these rules is read.

| topic | where to start |
|---|---|
| growth | `process::CmnGrowthCheck` (`fcn_0360f02d`, `fcn_0360f0fc`), `process::CmnSeasonGrowthCheck` (`fcn_0360df60`, `fcn_0360e02f`), `process::InfoNewsGrowth`; `menu::MenuModeGrowthReport`; `fcn_038b805c` (15 callers), `fcn_038679a9` (16 callers). Large bodies next to the role code, purpose not established: `fcn_038b9827` (736 lines; called from the day-end step `fcn_036365e6`; constants 0.5, 2, 3, 16; random numbers; tables `0x0216f510`, `0x0216f518`) and `fcn_038b765b` (156 lines; constants 0.7, 3.1, 100) |
| report day | event 48: `fcn_0363beba` |
| team spirit | the strings `teamSpirit_value` and `teamSpirit_decrease` are used by myClub screens (`menu::OnlineMyClubSquadTacticsTrainingItemResult`), `PERFECT_TEAM_SPIRIT` by `fcn_04682dc2`; no Master League code for team spirit was found |
| youth | strings `PlayerList::CreateObjectYouth` (`0x01f69540`), `ML/MLYouthMemberList` (`0x01f69560`); no class of its own in the type records; the rule that makes youth players is not found |
| retirement, new players | string `RETIREMENT_PLAYER` (`0x01f21500`); on the first day of a season the Become a Legend branch of the day begin sets a mark on the user's player from age 37 (from 36 with a condition); the Master League rule is not found |
| contracts | events 12 to 15 on 30 June and 31 December: `fcn_036e1665` (405 lines), `fcn_036e20d2`, `fcn_036e067a`, `fcn_036e1568`; string `PlayerList::CreateObjectUpdateContract`; years of a deal: `fcn_0388a1be` (96 lines, 9 callers) |
| draws, titles, awards | draws, events 32 to 39: `process::ProcessCmnLotCheck` (`fcn_035e6c9a`), `fcn_036cdb49`; titles, events 41 to 44: `fcn_0362eb70`, `fcn_036696e1`, `process::SpecialTitle…`; award holders: `fcn_0318c209` (12 callers) |
| news, staff reports | `process::InfoNews…`, `process::InfoStaffReportML`, `process::InfoEventML`; `fcn_038551f2(&kind, &value)` posts a news item, `fcn_031538bf(…)` a staff report |

## 13 The Master League save file

Level: **read** (table), the content **not seen**.

The save-kind table at `0x0213d1a8` (see `NOTES.md`) has Master League in **row 10**:
name `ML`, folder key `ml` (row 11 is `BL`, row 9 `LG`). The
container is the one `savefile.py` reads: same header, same cipher, same hashes. What
is inside (the mode data of section 2.2, in which order, packed or not) is not read,
and no `ML…` file is in the repository to look at.

One consequence of section 2: a career keeps its own player and team records in the
mode data. That is read from the look-up functions (they search tables inside the mode
data), not checked with a save. It means a change of the edit file reaches a running
career only where the mode reads the database again; where that happens is not found.

## 14 Not found, not read

- How fixtures are paired and dated (section 5).
- How computer clubs choose, price and close deals among themselves (section 9.3).
- Growth, team spirit, youth, retirement, new players, contracts (section 12).
- Club income, prize money, sponsors, budget (section 6.4).
- The meaning of `x` (player `+0xb4`, bits 11-22), of the "own" bit, of field `0x2e`,
  of the fee formula's `kind`, of the 13 deal states and of `day_state`.
- The other twelve cases of the negotiation step, and the lost fraction arithmetic in
  the one that was read.
- Season end (`fcn_035feb08` and the event-23 block).
- Calls through tables of function pointers are not resolved in `calls.tsv.xz`.
  `output/classes.tsv.xz` (new: 9,814 tables of 6,932 classes) gives the class and
  the slot of each such function, which is enough to follow a call by hand.

## 15 How to go on

```
cd "pes database/exe/tools"
python3 find.py show salary                  # C of a named function
python3 find.py callers 0x038ac66e           # who calls it
python3 x86dis.py <exe> 038ac66e 1940        # disassembly, for the fractions the C drops
python3 rtti.py <exe>                        # class names and their function tables
python3 yearplan.py <exe> july               # the year
python3 -c "import money; print(money.salary(90, 2000, rank=1), money.fee(77400, 90, 2000))"
```

The pattern that worked for the two formulas: read the C, take the arithmetic from
the disassembly, write it in Python, then run the game's code in `emu.py` with the
look-up functions answered (`Game.replace`) and compare. The next candidates, in the
order of what they would explain: `fcn_0385400e` (band), `fcn_038ab5ea`,
`fcn_0388a1be` (years), `fcn_0389b3f8` / `fcn_0389bd94` (willingness),
`fcn_03896290` (fit to the squad), `fcn_0389440a` (squad needs), `fcn_038b9827`
(growth).

What would settle the open meanings fastest is one Master League save file: the
fields of section 2.3 could be read for known players and compared with what the
screens show.

## Appendix A: steps of a day

Steps called from the four bodies of section 3 (60 C lines and more), in the order of
the code. "events asked" = the event numbers the function itself tests.

| function | called from | C lines | events asked | uses |
|---|---|---|---|---|
| `fcn_035d8b2e` | day begin | 181 | - | - |
| `fcn_03640d19` | day begin | 1280 | 3, 23, 25, 49 | random, wage bill, team strength |
| `fcn_03664a3d` | day begin | 111 | 1, 3, 6 | - |
| `fcn_0365c89a` | day begin | 177 | 3, 6 | day state, negotiation step |
| `fcn_03661f6b` | day begin | 144 | 1, 3, 6, 30 | day state |
| `fcn_036e20d2` | day begin | 114 | 1, 3, 6, 12, 14 | - |
| `fcn_03656fa5` | day begin | 449 | - | random, rating, salary, team strength, day state |
| `fcn_0364b81c` | day begin | 302 | 11 | random, staff report |
| `fcn_03676016` | day begin | 115 | 31, 45 | staff report |
| `fcn_0362579a` | day begin | 174 | 3, 6 | rating |
| `fcn_03632aa8` | day begin | 89 | - | - |
| `fcn_0363e8bb` | day begin | 930 | - | - |
| `fcn_035f51fe` | day end | 81 | - | - |
| `fcn_036fc11a` | day end | 240 | - | - |
| `fcn_03701dd5` | day end | 306 | - | - |
| `fcn_036696e1` | day end | 233 | 41, 43, 44 | - |
| `fcn_0362eb70` | day end | 139 | 41, 42, 43, 44 | - |
| `fcn_03664d29` | day end | 77 | 9 | day state |
| `fcn_0365692c` | day end | 266 | - | random, rating, team strength, day state |
| `fcn_0365cbbc` | day end | 86 | 9 | day state, negotiation step |
| `fcn_036e067a` | day end | 232 | 5, 13, 15 | complete transfer, staff report, news |
| `fcn_036fbe88` | day end | 115 | - | - |
| `fcn_0366f4bb` | day end | 60 | 6, 19, 23, 26, 27, 28, 29 | - |
| `fcn_0366d620` | day end | 228 | 23 | - |
| `fcn_03640686` | day end | 276 | 23 | - |
| `fcn_03652198` | day end | 111 | 4, 7 | random, scout search |
| `fcn_0363beba` | day end | 77 | 48 | staff report |
| `fcn_03634561` | day end | 85 | - | - |
| `fcn_03633690` | day end | 372 | - | - |
| `fcn_036f9395` | day end | 566 | - | - |
| `fcn_036f5728` | day end | 145 | 17 | - |
| `fcn_03621fab` | day end | 66 | - | - |
| `fcn_0360b189` | day end | 107 | - | - |
| `fcn_036e469b` | day end | 218 | - | - |
| `fcn_036365e6` | day end | 379 | - | staff report |
| `fcn_03708fd5` | after matches 1 | 128 | - | - |
| `fcn_03705515` | after matches 2 | 339 | - | random, staff report |
| `fcn_03637230` | after matches 2 | 167 | - | team strength |
| `fcn_0363c32e` | after matches 2 | 1400 | - | - |
| `fcn_036e3f46` | after matches 2 | 258 | - | - |
| `fcn_0370403e` | after matches 2 | 156 | - | - |
| `fcn_036793c1` | after matches 2 | 73 | - | - |
| `fcn_0364418c` | after matches 2 | 206 | - | - |
| `fcn_0362af8a` | after matches 2 | 284 | - | team strength |
| `fcn_03633f22` | after matches 2 | 222 | - | - |
| `fcn_03631f2d` | after matches 2 | 313 | - | - |
| `fcn_03627f98` | after matches 2 | 385 | - | rating |

Large functions (250 C lines and more) called by these steps:

| function | called by | C lines | events asked | uses |
|---|---|---|---|---|
| `fcn_03623a38` | `fcn_03627f98` | 489 | - | random |
| `fcn_0362636e` | `fcn_03627f98` | 583 | - | random |
| `fcn_0362e2bd` | `fcn_0362eb70` | 359 | - | rating |
| `fcn_03634e91` | `fcn_036365e6` | 270 | - | random, staff report |
| `fcn_03635675` | `fcn_036365e6` | 548 | - | - |
| `fcn_03638a08` | `fcn_0363beba` | 657 | - | - |
| `fcn_036435a7` | `fcn_0364418c` | 374 | - | wage bill |
| `fcn_0364692a` | `fcn_0364b81c` | 1202 | - | random |
| `fcn_03651767` | `fcn_03652198` | 416 | - | - |
| `fcn_0364f2ca` | `fcn_03652198` | 1381 | - | random, rating, fee, team strength, squad needs, staff report |
| `fcn_03653d49` | `fcn_0365692c` | 426 | - | - |
| `fcn_03654736` | `fcn_03656fa5` | 539 | - | random, rating |
| `fcn_03655c6b` | `fcn_03656fa5` | 334 | - | - |
| `fcn_03659b50` | `fcn_0365c89a` | 1621 | - | random, salary, fee, staff report |
| `fcn_03661380` | `fcn_03661f6b` | 304 | - | rating |
| `fcn_036602e5` | `fcn_03661f6b` | 392 | 30 | random, squad needs |
| `fcn_0366365b` | `fcn_03664d29` | 769 | 5, 8 | random, salary, complete transfer, staff report |
| `fcn_03668ee8` | `fcn_036696e1` | 310 | - | random |
| `fcn_0366e79f` | `fcn_0366f4bb` | 455 | - | - |
| `fcn_03672359` | `fcn_03676016` | 261 | - | - |
| `fcn_036dfd95` | `fcn_036e067a` | 366 | - | staff report |
| `fcn_036e1665` | `fcn_036e20d2` | 405 | 12, 14 | random, rating, staff report, news |
| `fcn_036fb5de` | `fcn_036fbe88` | 445 | - | - |
| `fcn_037010dc` | `fcn_03701dd5` | 517 | - | - |
| `fcn_0362c6ad` | `fcn_03705515` | 1125 | - | random |

## Appendix B: classes of the career modes

From the exe's type records (`rtti.py`, `output/classes.tsv.xz`). "Functions of its
own" = entries of the class's function table that no other class has; the first is
usually the destructor.

| class | table | functions of its own |
|---|---|---|
| `menu::AccountingPayment` | `0x01fb3fcc` | `0x03199488` `0x0319ac5b` `0x031985fd` `0x03197cdc` |
| `menu::MainMenuML` | `0x01fb604c` | `0x031a25cc` `0x031a4b83` `0x031a2204` `0x031a502c` `0x031a4ee7` `0x031a269b` … (7 in all) |
| `menu::MatchFromSchedule` | `0x020370ac` | `0x0335e134` `0x0335dde7` `0x0335e164` `0x0335f1e8` `0x0335e249` |
| `menu::MenuModeGrowthReport` | `0x01fb1d94` | `0x03183faa` `0x0318c016` `0x031827a6` `0x03182557` |
| `menu::MenuModeMLCoachEdit` | `0x01fb5424` | `0x0319fba9` `0x0319fbd9` `0x0319fe1d` `0x031a0876` `0x031a0916` `0x0319fd15` … (8 in all) |
| `menu::MenuModeMLCoachHallOfFame` | `0x01faf924` | `0x03176a83` `0x03179283` `0x03171d39` `0x03179018` `0x03177b0d` `0x03175a97` … (9 in all) |
| `menu::MenuModeMLCoachMenu` | `0x01fb01ec` | `0x0317c519` `0x0317c5d5` `0x0317c12a` `0x0317bec1` `0x0317bd68` |
| `menu::MenuModeMLCoachSeasonResult` | `0x01fafd6c` | `0x0317a692` `0x0317bcb2` `0x0317adb2` `0x0317bc06` `0x0317bc5c` |
| `menu::MenuModeMLCoachTitleCollection` | `0x01fae9e4` | `0x0316d746` `0x0316e695` `0x0316c99e` `0x0316d38b` `0x0316f3a5` `0x0316db23` … (8 in all) |
| `menu::MenuModeMLMoneyReport` | `0x01fb4fc4` | `0x0319eb57` `0x0319ec13` |
| `menu::MenuModeMLNegociationAdjust` | `0x01fab85c` | `0x03158ce5` `0x031592fc` `0x03154b6f` `0x03155957` `0x03154799` `0x031591cc` |
| `menu::MenuModeMLNegociationCountDown` | `0x01fae024` | `0x0316a843` `0x0316aeaf` `0x0316a206` `0x03169e47` `0x03169e17` |
| `menu::MenuModeMLNegociationDetail` | `0x01fac2dc` | `0x0315d3fe` `0x0315ce0a` `0x031597df` `0x0315c98a` `0x0315cb2f` `0x0315d65a` … (9 in all) |
| `menu::MenuModeMLNegociationDialog` | `0x02004264` | `0x032ab2d7` `0x032ab39c` `0x032ad02a` `0x032abdee` |
| `menu::MenuModeMLNegociationList` | `0x01fad60c` | `0x031646b0` `0x03167916` `0x0315e4c2` `0x031667be` `0x0316714e` `0x0315ef13` … (14 in all) |
| `menu::MenuModeMLNegociationMenu` | `0x01fadacc` | `0x031694f8` `0x03169528` `0x03168ce0` `0x031685c7` `0x031684bc` |
| `menu::MenuModeMLNickName` | `0x01fb0a3c` | `0x0317e805` `0x0317e95c` `0x0317e626` `0x0317e686` |
| `menu::MenuModeMLPlayerManagement` | `0x01fab21c` | `0x03153dcd` `0x03153f17` `0x03154371` `0x03153b5c` `0x031539af` `0x03153c22` |
| `menu::MenuModeMLPlayerSearchConcept` | `0x01faa0cc` | `0x0315099d` `0x031506d9` `0x031507ad` `0x0315089d` `0x031508fd` |
| `menu::MenuModeMLPlayerSearchRole` | `0x01fa9bc4` | `0x0315051e` `0x031502b8` `0x03150398` `0x0315048e` `0x031504de` |
| `menu::MenuModeMLTrainingSelect` | `0x01fb3c24` | `0x03196da1` `0x03197786` `0x03197a86` `0x031975c8` `0x031973ec` `0x03197558` |
| `menu::MenuModeMLTrainingSkill` | `0x01fb3474` | `0x031949e6` `0x03194b5b` `0x03196b65` `0x03195773` `0x031955d0` `0x03196cb5` … (7 in all) |
| `menu::MenuModeMonthlySchedule` | `0x01fe08b4` | `0x03223e65` `0x032251f3` `0x032238a1` `0x032235be` |
| `menu::MenuModeNationalSchedule` | `0x01fb061c` | `0x0317e447` `0x0317e52a` `0x0317d296` `0x0317cd9d` |
| `menu::MenuModeOfferList` | `0x01fb287c` | `0x0318f369` `0x0318f129` `0x0318e40a` `0x0318f0f9` |
| `menu::MenuModeTeamRoleDialog` | `0x020025bc` | `0x032a78d4` `0x032a7db2` `0x032a762a` |
| `menu::ModeMLAccountingClubBS` | `0x01fb44ec` | `0x0319af7e` `0x0319b259` `0x0319b106` |
| `menu::ModeMLDivisionExchange` | `0x01fb0ecc` | `0x0317f12e` `0x0317fac0` `0x0317f05e` |
| `menu::ModeMLGeneralSettings` | `0x01fb58dc` | `0x031a15e0` `0x031a1768` `0x031a13d4` `0x031a15c0` |
| `menu::ModeMLInputMoney` | `0x0203e524` | `0x03379553` `0x03379e4a` `0x03379e9a` `0x03379eca` `0x033793d6` `0x03379396` |
| `menu::ModeMLPhilosophy` | `0x01fae454` | `0x0316bac2` `0x0316b851` `0x0316bb77` `0x0316b227` |
| `menu::ModeMLPlayerGameData` | `0x01fa9264` | `0x0314bf0a` `0x0314d0ae` `0x0314c688` `0x0314d27f` `0x0314d2bf` |
| `menu::ModeMLRangeSetDialogMoney` | `0x02004a34` | `0x032aec5a` `0x032af58a` `0x032af7f9` `0x032aece9` `0x032aeb93` |
| `menu::ModeMLScoutMenu` | `0x01faadd4` | `0x03152e83` `0x031526cf` `0x0315259f` `0x03153690` `0x03152f12` `0x0315264f` |
| `menu::ModeMLScoutingSettings` | `0x01faa824` | `0x0315164c` `0x031522cf` `0x03150a6c` `0x0315137d` `0x03151f32` |
| `menu::ModeMLSeasonRecord` | `0x01fa6a2c` | `0x031387b8` `0x0313b17e` |
| `menu::ModeMLTeamRoleList` | `0x01fb2dfc` | `0x0318fb2a` `0x03194621` `0x03192c2d` `0x03191045` `0x031945f1` `0x0318fa08` … (8 in all) |
| `menu::ModeOfferAccept` | `0x01fa84c4` | `0x03149286` `0x031488da` `0x03146838` `0x03148fff` `0x03148a2a` `0x03148aec` … (7 in all) |
| `menu::Schedule` | `0x01fe367c` | `0x0322fc09` `0x03231f09` `0x03231b45` `0x03231bf6` `0x0322ff8a` `0x03231a59` … (7 in all) |
| `menu::ScheduleBase` | `0x0203931c` | `0x03367fa2` |
| `menu::ScheduleProgress` | `0x01fe3bcc` | `0x032321fb` `0x03231f19` `0x03234067` `0x03233c6b` |
| `menu::SquadNumberSet_ML` | `0x01f9f014` | `0x031191c1` `0x03117e08` |
| `menu::SquadNumberSet_ML_National` | `0x01f9f154` | `0x031191f1` `0x03117e4e` |
| `menu::SquadNumberSettingSel_ML` | `0x01f9f754` | `0x03119e3a` `0x03119e6a` |
| `menu::TeamSelectDefaultTeamML` | `0x020036c4` | `0x032aa340` `0x032aa28b` |
| `menu::TeamSelectRequestML` | `0x02003de4` | `0x032aaa96` `0x032aaac6` `0x032aadc0` |
| `process::CmnAchievementCheck` | `0x020e0524` | `0x035e5e39` `0x035e5f1e` `0x035e6107` |
| `process::CmnAutoSaveCheck` | `0x020e5f84` | `0x036083b1` `0x03608480` |
| `process::CmnAutoSaveCheckFlow` | `0x020e4cdc` | `0x035ff620` `0x035ff6ef` |
| `process::CmnAutoSaveIdleFlow` | `0x020e4b34` | `0x035ff089` `0x035fefd4` `0x035ff2d8` `0x035fef05` |
| `process::CmnAutoSaveSettingIdle` | `0x020e1134` | `0x035e7417` |
| `process::CmnAutoSystemSaveIdleFlow` | `0x020e161c` | `0x035e7a7a` `0x035e78ed` `0x035e78ad` |
| `process::CmnCheckCompeIndex` | `0x020e8934` | `0x03611ae8` `0x03611c86` |
| `process::CmnCheckCompeRegulation` | `0x020e8c1c` | `0x03611f05` `0x03611fd4` |
| `process::CmnCheckJoinCompe` | `0x020e89ac` | `0x03611b18` `0x03611dc6` |
| `process::CmnCoopSettingsCheck` | `0x020dffd4` | `0x035e5670` `0x035e580e` |
| `process::CmnEyeCatchCheck` | `0x020e657c` | `0x036092d3` `0x03609303` |
| `process::CmnGrowthCheck` | `0x020e7e94` | `0x0360f02d` `0x0360f0fc` |
| `process::CmnHallPlayerCheck` | `0x020e7cec` | `0x0360edda` `0x0360eea9` |
| `process::CmnInfoAccumulation` | `0x020e1d04` | `0x035f5515` `0x035f55e4` |
| `process::CmnLeagueRankingSel` | `0x020e0384` | `0x035e5bea` `0x035e5cb9` |
| `process::CmnLoadIdle` | `0x020e219c` | `0x035f88ed` `0x035f9aa2` `0x035fa42c` `0x035f9b22` `0x035fa45c` |
| `process::CmnLoadTeamDataIdle` | `0x020deb24` | `0x035e24af` `0x035e26c3` `0x035e2693` `0x035e2733` `0x035e2b9d` |
| `process::CmnMatchInit` | `0x020e40ec` | `0x035fe2cf` `0x035fe39e` |
| `process::CmnMatchOnlyDataCopy` | `0x020e34b4` | `0x035fd5af` `0x035fd67e` |
| `process::CmnMatchReportMenuReturn` | `0x020e6734` | `0x03609529` `0x036095f8` |
| `process::CmnMatchResultCheck` | `0x020e746c` | `0x0360dc3c` `0x0360dd0b` |
| `process::CmnModeClubGamePlanCreation` | `0x020e371c` | `0x035fd7fe` `0x035fd8cd` |
| `process::CmnModeInit` | `0x020e91b4` | `0x0361251d` `0x036125ec` |
| `process::CmnModeLiveDataAttach` | `0x020dfe14` | `0x035e536d` `0x035e4598` `0x035e5492` |
| `process::CmnModeMainMenuGamePlanCreation` | `0x020e3bfc` | `0x035fdd83` `0x035fde52` |
| `process::CmnModeMainMenuGamePlanRelease` | `0x020e3e6c` | `0x035fe113` `0x035fe1e2` |
| `process::CmnModeNationalGamePlanCreation` | `0x020e398c` | `0x035fda7e` `0x035fdb4d` |
| `process::CmnMonthlyBestElevenCheck` | `0x020e79a4` | `0x0360e645` `0x0360e714` |
| `process::CmnMonthlyCheck` | `0x020e7b54` | `0x0360ea9e` `0x0360eb6d` |
| `process::CmnMonthlyScheduleCheck` | `0x020e77cc` | `0x0360e261` `0x0360e330` |
| `process::CmnMyDataCheck` | `0x020e4e8c` | `0x035ff85e` `0x03606652` |
| `process::CmnOffModeGate` | `0x020df9bc` | `0x035e411b` `0x035e430f` |
| `process::CmnOfferListGamePlanCreation` | `0x020e30ac` | `0x035fd211` `0x035fd2e0` |
| `process::CmnOfferListGamePlanRelease` | `0x020e331c` | `0x035fd3f3` `0x035fd4c2` |
| `process::CmnOfferTeamInfoReturn` | `0x020e27c4` | `0x035fc8d8` `0x035fc9a7` |
| `process::CmnOpCheck` | `0x020e8ebc` | `0x0361234e` `0x0361241d` |
| `process::CmnPostCompeMenuReturn` | `0x020e46f4` | `0x035fe8d9` `0x035fe9a8` |
| `process::CmnPostCompeSelReturn` | `0x020e4534` | `0x035fe696` `0x035fe765` |
| `process::CmnPostLoadModeCheck` | `0x020e6c7c` | `0x03609b23` `0x03609bf2` |
| `process::CmnPostMatchUserCheck` | `0x020e81f4` | `0x0360f859` `0x0360f928` |
| `process::CmnPostMenuReturn` | `0x020e68ec` | `0x03609728` `0x036097f7` |
| `process::CmnPostSaveModeCheck` | `0x020e6ab4` | `0x03609927` `0x036099f6` |
| `process::CmnPromoDemoCheck` | `0x020e62bc` | `0x03608719` `0x036087e8` |
| `process::CmnReportEventCheck` | `0x020e579c` | `0x0360732e` `0x036073da` |
| `process::CmnReportEventFadeWaiting` | `0x020e5514` | `0x03606ef9` `0x03606fde` `0x0360702e` |
| `process::CmnRequestTeamInfoReturn` | `0x020e2954` | `0x035fcae9` `0x035fcbb8` |
| `process::CmnResetInit` | `0x020dda4c` | `0x035e1811` `0x035e1841` `0x035e1a7b` |
| `process::CmnReturnCoopSettingsCheck` | `0x020e004c` | `0x035e56a0` `0x035e592b` |
| `process::CmnReturnMemberList` | `0x020e06b4` | `0x035e61d4` `0x035e62a3` |
| `process::CmnRoleReportCheck` | `0x020e529c` | `0x03606c2e` `0x03606cfd` |
| `process::CmnSaveDataSaveCancel` | `0x020e5964` | `0x03607bae` `0x03607c7d` |
| `process::CmnSaveIdle` | `0x020e10bc` | `0x035fc2e9` |
| `process::CmnScheduleProcessCheck` | `0x020e5c64` | `0x03607db9` `0x03607e8c` |
| `process::CmnSeasonGrowthCheck` | `0x020e7614` | `0x0360df60` `0x0360e02f` |
| `process::CmnSetBGSave` | `0x020ea91c` | `0x036149ca` `0x03614a99` |
| `process::CmnStaffReportCheck` | `0x020e5104` | `0x036068f8` `0x03606ae2` |
| `process::CmnStandingsCheck` | `0x020e8054` | `0x0360f475` `0x0360f544` |
| `process::CmnStorageCheckOP` | `0x020e5df4` | `0x03608215` `0x036082e4` |
| `process::CmnSystemSaveIdle` | `0x020e13a4` | `0x035e781d` `0x035e76a0` `0x035e7680` |
| `process::CmnTeamDataSaveIdle` | `0x020e2624` | `0x035fc838` `0x035fc6bb` `0x035fc5f3` `0x035fc69b` |
| `process::CmnTeamInfoGamePlanCreation` | `0x020e2bbc` | `0x035fcca5` `0x035fcd74` |
| `process::CmnTeamInfoGamePlanRelease` | `0x020e2e44` | `0x035fcf1e` `0x035fd00d` |
| `process::CmnTeamSelCancel` | `0x020e0f2c` | `0x035e722b` `0x035e72fa` |
| `process::CmnUpdateAutoSaveSetting` | `0x020e6114` | `0x0360856d` `0x0360863c` |
| `process::CmnUpdateDayBegin` | `0x020e6f24` | `0x03609e57` `0x03609d22` `0x03609ec7` |
| `process::CmnUpdateDayEnd` | `0x020e71bc` | `0x0360b7af` `0x0360b08e` `0x0360b8ca` |
| `process::CmnUpdatePostAutoSave` | `0x020e1e94` | `0x035f5a7d` `0x035f5b4c` |
| `process::CmnUpdatePostMatch` | `0x020e847c` | `0x0360feac` `0x0360fa6e` `0x0360ff0c` |
| `process::CmnUpdatePreMatch` | `0x020e872c` | `0x03611182` `0x03611910` |
| `process::CmnUpdateSeasonEnd` | `0x020e48ac` | `0x035feb08` `0x035febd7` |
| `process::CmnUpdateSkipMatch` | `0x020e435c` | `0x035fe49e` `0x035fe56d` |
| `process::CompePDSelCancel` | `0x020ea0cc` | `0x03613f0b` `0x03613fda` |
| `process::CompePostUsersCheck` | `0x020ea3f4` | `0x03614329` `0x036143f8` |
| `process::CompePreUsersCheck` | `0x020ea264` | `0x036140d7` `0x036141a6` |
| `process::CompeTeamSelCancel` | `0x020e9f34` | `0x03613d5f` `0x03613e2e` |
| `process::InfoEvent` | `0x021022dc` | `0x0367bb17` |
| `process::InfoEventBL` | `0x021041c8` | `0x036d9543` `0x036daecb` |
| `process::InfoEventLeague` | `0x021022e8` | `0x0367bb47` `0x0367ba4c` |
| `process::InfoEventML` | `0x021027bc` | `0x036832fd` `0x03685083` |
| `process::InfoNews` | `0x02102a24` | - |
| `process::InfoNewsAfterMatch` | `0x02103588` | `0x036c221d` |
| `process::InfoNewsAfterMatchDetail` | `0x02103384` | `0x036b9f94` `0x036ba046` |
| `process::InfoNewsBeforeMatch` | `0x021039a4` | `0x036cd7f4` |
| `process::InfoNewsCompe` | `0x0210315c` | `0x036b6a3a` |
| `process::InfoNewsGeneral` | `0x02102a30` | `0x0368e696` |
| `process::InfoNewsGrowth` | `0x02102c30` | `0x036933f4` |
| `process::InfoNewsTransfer` | `0x02102e78` | `0x036a7949` |
| `process::InfoStaffReport` | `0x021025a8` | `0x03682b67` |
| `process::InfoStaffReportBL` | `0x02103db0` | `0x036d9061` `0x036d9140` |
| `process::InfoStaffReportML` | `0x021025b4` | `0x03682b97` `0x03682f42` |
| `process::KnockOutCreation` | `0x02138bf0` | `0x0376ee12` |
| `process::LeagueCreation` | `0x02138c00` | `0x0376f475` `0x037741b4` |
| `process::LeaguePreUsersCheck` | `0x020df5bc` | `0x035e3c6c` `0x035e3dad` |
| `process::LeagueTeamInfoUserNumCheck` | `0x020df74c` | `0x035e3f7f` `0x035e404e` |
| `process::MLProcessCoachEdit` | `0x020dee0c` | `0x035e3129` `0x035e31f8` |
| `process::ModeDataCreation` | `0x020e1a94` | `0x035e8ba8` `0x035ef91e` `0x035e90eb` `0x035e95c3` |
| `process::ModeDataCreationThread` | `0x020e191c` | `0x035e8b48` `0x035f4b87` |
| `process::OfflineNegociateReturn` | `0x020df0bc` | `0x035e3350` `0x035e341f` |
| `process::PlayerSearch` | `0x020d99c0` | `0x035d7f9c` |
| `process::PracticeCompeCreation` | `0x02138bf8` | `0x0376efdd` |
| `process::ProcessCmnFinanceReportCheck` | `0x020e0bac` | `0x035e68ff` `0x035e69ce` |
| `process::ProcessCmnLotCheck` | `0x020e0d74` | `0x035e6bcb` `0x035e6c9a` |
| `process::ProcessCmnMainMenuSelector` | `0x020e9454` | `0x036129d3` `0x03612a88` |
| `process::ProcessCmnModeTmpWork` | `0x020d9630` | `0x035d4e01` |
| `process::ProcessCmnModeTmpWork::NewsTexture` | `0x020d9628` | `0x035d3dfb` |
| `process::ProcessCmnNationalResultCheck` | `0x020e085c` | `0x035e6370` `0x035e643f` |
| `process::ProcessCmnPreMainCheck` | `0x020e9754` | `0x03612c40` `0x03612c80` `0x03612d35` |
| `process::ProcessCmnSeasonResultCheck` | `0x020e09fc` | `0x035e66df` `0x035e67ae` |
| `process::SpecialCoachTitleSet` | `0x02101168` | `0x036662b8` |
| `process::SpecialTitle` | `0x02101080` | `0x036661c8` |
| `process::SpecialTitleSetAFC` | `0x021010f8` | `0x0366c735` `0x0366691d` `0x0366a4ed` `0x0366696d` `0x03666999` `0x036668dd` |
| `process::SpecialTitleSetCONMEBOL` | `0x021010c0` | `0x0366a3d8` `0x0366689d` |
| `process::SpecialTitleSetUEFA` | `0x02101088` | `0x036667f1` `0x0366662d` |
| `process::SpecialTitleSetWorld` | `0x02101130` | `0x0366a602` `0x0366bd92` `0x03666b95` `0x03666a99` `0x03666b55` `0x036661f8` … (7 in all) |
| `process::UpdateDayBeginThread` | `0x020e6f90` | `0x03609e27` `0x0360b06e` |
| `process::UpdateDayEndThread` | `0x020e7228` | `0x0360b6e3` `0x0360dbf0` |
| `process::UpdatePostMatchThread` | `0x020e84e8` | `0x0360fe7c` `0x03611162` |

## Appendix C: the year for a league with a January season

| date | event | what |
|---|---|---|
| 1.1. | 1 | first day of the season: the year plan is written |
| 1.1. | 3 | first transfer window opens |
| 8.1. | 41 | title step of fcn_0362eb70, fcn_036696e1 (process::SpecialTitle, not read) |
| 11.1. | 26 | asked by fcn_0366f4bb and news functions (not read) |
| 30.1. | 4 | day before the first window closes (the daily scout step is left out) |
| 31.1. | 5 | first transfer window closes |
| 1.2. | 30 | day after a window closes: computer clubs plan their squads (fcn_036602e5) |
| 15.2. | 48 | report step fcn_0363beba (writes a staff report; not read) |
| 15.3. | 19 | taken to be a national team day (six a year) |
| 16.3. | 20 | the day after event 19 |
| 19.3. | 35 | draw day (process::ProcessCmnLotCheck) |
| 19.3. | 36 | draw day (process::ProcessCmnLotCheck) |
| 16.4. | 37 | draw day (process::ProcessCmnLotCheck) |
| 16.4. | 38 | draw day (process::ProcessCmnLotCheck) |
| 9.5. | 11 | asked by fcn_0364b81c (not read) |
| 25.5. | 19 | taken to be a national team day (six a year) |
| 26.5. | 20 | the day after event 19 |
| 28.5. | 39 | draw day (process::ProcessCmnLotCheck) |
| 13.6. | 11 | asked by fcn_0364b81c (not read) |
| 22.6. | 19 | taken to be a national team day (six a year) |
| 23.6. | 20 | the day after event 19 |
| 28.6. | 11 | asked by fcn_0364b81c (not read) |
| 28.6. | 31 | asked by fcn_03676016 (not read) |
| 30.6. | 14 | half-year step of fcn_036e1665 (not read) |
| 30.6. | 24 | asked by fcn_03649f1f, 616 lines (taken to be the closing of the accounts) |
| 30.6. | 13 | half-year step of fcn_036e067a, fcn_036e1568 (not read) |
| 30.6. | 22 | asked by fcn_0314910f only (not read) |
| 1.7. | 25 | money step fcn_03640d19; asked by process::ProcessCmnFinanceReportCheck |
| 1.7. | 6 | second transfer window opens |
| 26.7. | 45 | asked by fcn_03676016 (not read) |
| 4.8. | 10 | asked by fcn_0364c065 and the staff report (not read) |
| 20.8. | 19 | taken to be a national team day (six a year) |
| 21.8. | 20 | the day after event 19 |
| 26.8. | 42 | title step of fcn_0362eb70 (process::SpecialTitleSetUEFA, not read) |
| 27.8. | 32 | draw day (process::ProcessCmnLotCheck) |
| 27.8. | 27 | asked by fcn_0366f4bb and news functions (not read) |
| 30.8. | 7 | day before the second window closes (the daily scout step is left out) |
| 31.8. | 8 | second transfer window closes |
| 1.9. | 30 | day after a window closes: computer clubs plan their squads (fcn_036602e5) |
| 18.9. | 17 | asked by fcn_036f5728 (not read) |
| 19.9. | 16 | asked by the staff report and a transfer news function (not read) |
| 21.9. | 19 | taken to be a national team day (six a year) |
| 22.9. | 20 | the day after event 19 |
| 26.10. | 19 | taken to be a national team day (six a year) |
| 27.10. | 20 | the day after event 19 |
| 7.11. | 11 | asked by fcn_0364b81c (not read) |
| 10.12. | 33 | draw day (process::ProcessCmnLotCheck) |
| 10.12. | 34 | draw day (process::ProcessCmnLotCheck) |
| 12.12. | 11 | asked by fcn_0364b81c (not read) |
| 20.12. | 49 | money step fcn_03640d19 |
| 24.12. | 48 | report step fcn_0363beba (writes a staff report; not read) |
| 28.12. | 44 | title step of fcn_0362eb70, fcn_036696e1 (not read) |
| 29.12. | 43 | title step of fcn_0362eb70, fcn_036696e1 (not read) |
| 29.12. | 31 | asked by fcn_03676016 (not read) |
| 29.12. | 11 | asked by fcn_0364b81c (not read) |
| 30.12. | 28 | asked by fcn_0366f4bb and news functions (not read) |
| 31.12. | 12 | half-year step of fcn_036e1665 (not read) |
| 31.12. | 24 | asked by fcn_03649f1f, 616 lines (taken to be the closing of the accounts) |
| 31.12. | 15 | half-year step of fcn_036e067a, fcn_036e1568 (not read) |
| 31.12. | 23 | last day of the season: season-end processing |

## Appendix D: season kind by league id

Table `0x021687d0` (92 rows). Kind 0 = season from 1 July; every other kind = season
from 1 January. The ids are the game's league ids (`fcn_0385662c` gives the league of
a competition); their names are not looked up.

| kind | league ids |
|---|---|
| 0 | 17, 20, 18, 21, 19, 22, 50, 79, 80, 81, 82, 99, 2, 3, 4, 5, 6, 7, 23, 26, 24, 27, 25, 28, 53, 36, 41, 42, 83, 84, 85, 86, 87, 88, 89, 90, 91, 95 |
| 1 | 29, 30, 67, 13400, 13401, 51, 10200, 10201, 8, 9, 10, 76, 77, 78, 11, 12, 13, 100, 101, 102, 14, 29, 68, 59, 54, 38, 92 |
| 2 | 52, 15, 16, 55, 39, 44, 45, 97 |
| 3 | 60, 61, 62, 63, 64, 65, 66, 75, 74 |
| 4 | 40, 46 |
| 5 | 37, 43 |
| 6 | 1, 35, 34, 47, 48, 56 |

## Appendix E: role table

Table `0x0216f85c`, one row of `0x14` bytes per role, raw: three effect numbers
(10 = none, shown as "-") and the number at `+0x0c` ("kind") that `role_multiplier`
tests for 6. Effects 3, 4 and 5 are the ones `role_multiplier` uses; the others are
not followed. The role names are not looked up.

| role | effect 1 | effect 2 | effect 3 | kind |
| --- | --- | --- | --- | --- |
| 0 | - | - | - | - |
| 1 | - | - | - | 0 |
| 2 | - | - | - | 0 |
| 3 | - | - | - | - |
| 4 | 8 | 6 | - | - |
| 5 | - | - | - | - |
| 6 | - | - | - | - |
| 7 | 1 | - | - | - |
| 8 | - | - | - | - |
| 9 | 3 | - | - | - |
| 10 | 1 | - | - | - |
| 11 | 8 | 6 | - | - |
| 12 | 3 | - | - | - |
| 13 | 8 | 7 | - | - |
| 14 | 0 | - | - | 7 |
| 15 | 2 | - | - | 8 |
| 16 | 4 | - | - | 6 |
| 17 | 9 | - | - | 9 |
| 18 | 8 | 7 | 2 | 2 |
| 19 | 8 | 7 | 4 | 1 |
| 20 | - | - | - | 3 |
| 21 | - | - | - | 4 |
| 22 | - | - | - | 5 |

## Appendix F: who asks for each event

For each event number, the functions whose C tests it with `event_on_date` or
`event_on_day` (found by script: the number assigned just before the call). A class
name in brackets = the function is in that class's table.

| event | asked by |
|---|---|
| 1 | `fcn_031a502c` (menu::MainMenuML), `fcn_0360a350`, `fcn_03661f6b`, `fcn_03664a3d`, `fcn_036d7d15`, `fcn_036d9140` (process::InfoStaffReportBL), `fcn_036daecb` (process::InfoEventBL), `fcn_036e20d2` |
| 3 | `fcn_0360a350`, `fcn_0362579a`, `fcn_03640d19`, `fcn_0365c89a`, `fcn_03661f6b`, `fcn_036623d3`, `fcn_03664a3d`, `fcn_036800a9`, `fcn_03682f42` (process::InfoStaffReportML) … (15 in all) |
| 4 | `fcn_03652198` |
| 5 | `fcn_03137118` (menu::MainMenuBL), `fcn_031a502c` (menu::MainMenuML), `fcn_0329c6cf` (menu::MainMenuBL), `fcn_03609ec7` (process::CmnUpdateDayBegin), `fcn_0360bf0c`, `fcn_03658eda`, `fcn_0366365b`, `fcn_03682f42` (process::InfoStaffReportML), `fcn_03695b10` … (13 in all) |
| 6 | `fcn_031a502c` (menu::MainMenuML), `fcn_0360a350`, `fcn_0362579a`, `fcn_0365c89a`, `fcn_03661f6b`, `fcn_03664a3d`, `fcn_0366f4bb`, `fcn_036800a9`, `fcn_03682f42` (process::InfoStaffReportML) … (14 in all) |
| 7 | `fcn_03652198` |
| 8 | `fcn_03137118` (menu::MainMenuBL), `fcn_03156db0`, `fcn_0315916c`, `fcn_0315a7b6`, `fcn_0315f11b`, `fcn_031a502c` (menu::MainMenuML), `fcn_0329c6cf` (menu::MainMenuBL), `fcn_03609ec7` (process::CmnUpdateDayBegin), `fcn_0360bf0c` … (17 in all) |
| 9 | `fcn_03658821`, `fcn_0365cbbc`, `fcn_0365df66`, `fcn_03664d29`, `fcn_036e2d84`, `fcn_0388d1c3` |
| 10 | `fcn_0364c065`, `fcn_03682f42` (process::InfoStaffReportML), `fcn_0385477f` |
| 11 | `fcn_0364b81c`, `fcn_036823b8`, `fcn_036a69e1`, `fcn_038aee47` |
| 12 | `fcn_036e1665`, `fcn_036e20d2` |
| 13 | `fcn_0367affd`, `fcn_036e067a`, `fcn_036e1568` |
| 14 | `fcn_036e1665`, `fcn_036e20d2` |
| 15 | `fcn_0367affd`, `fcn_036e067a`, `fcn_036e1568` |
| 16 | `fcn_03682f42` (process::InfoStaffReportML), `fcn_0369655a`, `fcn_036d9140` (process::InfoStaffReportBL) |
| 17 | `fcn_036f34be`, `fcn_036f5728` |
| 19 | `fcn_031a502c` (menu::MainMenuML), `fcn_0360a350`, `fcn_0366f4bb`, `fcn_0367b994`, `fcn_03681aeb`, `fcn_038703cc` |
| 20 | `fcn_035fde52` (process::CmnModeMainMenuGamePlanCreation), `fcn_0367d797`, `fcn_036893b3`, `fcn_0368bc98`, `fcn_036d68df`, `fcn_036d6b8f`, `fcn_036da4d0`, `fcn_038700b7`, `fcn_038703cc` |
| 22 | `fcn_0314910f` |
| 23 | `fcn_0314910f`, `fcn_0329ae56` (menu::MainMenuBL), `fcn_032b5298` (menu::MainMenuChoiceLeague), `fcn_0360bf0c`, `fcn_03612ef7` (process::PreMainCheckThread), `fcn_03640686`, `fcn_03640d19`, `fcn_0366d620`, `fcn_0366f4bb` … (14 in all) |
| 24 | `fcn_031a502c` (menu::MainMenuML), `fcn_03649f1f`, `fcn_0364c065`, `fcn_03682f42` (process::InfoStaffReportML) |
| 25 | `fcn_035e69ce` (process::ProcessCmnFinanceReportCheck), `fcn_03640d19` |
| 26 | `fcn_03606928`, `fcn_03631bb6`, `fcn_0366f4bb`, `fcn_03683d47`, `fcn_036d0c58`, `fcn_036d9b56` |
| 27 | `fcn_03631bb6`, `fcn_0366f4bb`, `fcn_03683d47`, `fcn_036d0c58`, `fcn_036d9b56` |
| 28 | `fcn_03631bb6`, `fcn_0366f4bb`, `fcn_03683d47`, `fcn_036d0c58`, `fcn_036d9b56` |
| 29 | `fcn_03631bb6`, `fcn_0366f4bb`, `fcn_03683d47`, `fcn_036d0c58`, `fcn_036d9b56` |
| 30 | `fcn_036602e5`, `fcn_03661f6b` |
| 31 | `fcn_0360a350`, `fcn_03676016`, `fcn_03682f42` (process::InfoStaffReportML), `fcn_036d0796` |
| 32 | `fcn_035e6c9a` (process::ProcessCmnLotCheck), `fcn_036cdb49` |
| 33 | `fcn_035e6c9a` (process::ProcessCmnLotCheck), `fcn_036cdb49` |
| 34 | `fcn_035e6c9a` (process::ProcessCmnLotCheck), `fcn_036cdb49` |
| 35 | `fcn_035e6c9a` (process::ProcessCmnLotCheck), `fcn_036cdb49` |
| 36 | `fcn_035e6c9a` (process::ProcessCmnLotCheck), `fcn_036cdb49` |
| 37 | `fcn_035e6c9a` (process::ProcessCmnLotCheck), `fcn_036cdb49` |
| 38 | `fcn_035e6c9a` (process::ProcessCmnLotCheck), `fcn_036cdb49` |
| 39 | `fcn_035e6c9a` (process::ProcessCmnLotCheck), `fcn_036cdb49` |
| 41 | `fcn_0362eb70`, `fcn_036696e1` |
| 42 | `fcn_0362eb70`, `fcn_0366638e`, `fcn_036667f1` (process::SpecialTitleSetUEFA) |
| 43 | `fcn_0362eb70`, `fcn_036696e1` |
| 44 | `fcn_0362eb70`, `fcn_036696e1` |
| 45 | `fcn_0360a350`, `fcn_03676016` |
| 47 | `fcn_036523fb` |
| 48 | `fcn_031a269b` (menu::MainMenuML), `fcn_031a502c` (menu::MainMenuML), `fcn_0329ce18` (menu::MainMenuBL), `fcn_0360a350`, `fcn_0363beba`, `fcn_03682f42` (process::InfoStaffReportML) |
| 49 | `fcn_03640d19` |
