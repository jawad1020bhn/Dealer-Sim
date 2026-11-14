# Sider Lua modules for Master League

Modules for the Sider that ships in `pes.7z` (`sider.dll` of 20 February 2022, Lua
enabled in `sider.ini`). They work on the running game; `PES2017.exe` is not edited.

| file | what it does |
|---|---|
| `MLCheck.lua` | **read-only test.** Reads the overall window of computer clubs by level (section 9.4 of `../MASTER_LEAGUE.md`) and four numbers of the transfer fee formula (section 6.2) from the running game and writes them to `sider.log`. It writes nothing to the game |
| `test_module.py <PES2017.exe>` | runs `MLCheck.lua` outside the game against the bytes of the exe file (needs `pip install lupa`) |

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
  them lies in one of the 127 functions named in `../names.tsv`, so the salary, fee,
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
  change code. That is the route for the tuning modules.

## Notes for the next module

- The exe has a fixed load address (no relocation table, no dynamic base), so the
  addresses of `MASTER_LEAGUE.md` are valid in the running game. `MLCheck.lua` tests
  exactly this.
- The level values are single bytes inside `mov eax, value` instructions; 68 and 9,000
  of the fee formula are numbers inside two instructions; 0.00027 is a constant with
  one user. All four can be changed in place.
- **The 2.2 of the fee formula is a shared constant** (`0x01f0f2b8`, 16 references in
  the exe). It must not be changed in place; the fee function has to be pointed to a
  constant of its own.
