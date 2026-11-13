# PES2017.exe decompiled

Static decompilation of the `PES2017.exe` in `pes.7z.001`-`.005` (110,179,840 bytes,
sha256 `44b0caaa…954f`, 32-bit Windows, built 2 September 2016). Nothing was run: the
file was read with [REA](https://github.com/morluto/rea) driving Rizin 0.9.1 and its
Ghidra decompiler plugin (`rea execute-rizin-command`, set-up in `../../rea-setup.sh`).

This is a first pass: every function that could be found is decompiled to C with
machine names (`fcn_038e77af`). Nothing is named or explained yet.

## Look something up

Python 3 only, no set-up:

```
cd "pes database/exe/tools"
python3 find.py show 0x038e77af        # the C of one function
python3 find.py string editSaveData    # functions that refer to a string containing the text
python3 find.py import CreateFileW     # functions that use a Windows import
python3 find.py callers 0x038e77af     # who calls it        (callees: what it calls)
python3 find.py grep 'overall_value'   # search all the C (a few seconds)
```

## What is in `output/`

| file | content |
|---|---|
| `c/02a.c.xz` … `c/047.c.xz` | the C: one file per 1 MB of code, functions in address order. 104,462 functions, 4,900,593 lines, 184 MB unpacked |
| `functions.tsv.xz` | 199,860 code starts: address, shape, size, blocks, call sites, data pointers, callees, lines of C, status, hint |
| `calls.tsv.xz` | 324,827 caller → callee pairs (direct calls between functions) |
| `string_refs.tsv.xz` | 42,917 function → string references |
| `import_refs.tsv.xz` | 10,334 function → import references |
| `strings.tsv.xz` | 151,820 strings of the two data sections (address, kind, text) |
| `sections.tsv`, `imports.tsv`, `exports.tsv` | 14 sections, 682 imports, 41 exports |
| `evidence.tsv` | the 129 REA Evidence ids: 3 inventory commands, 110 decompile batches |

`*.xz` opens with 7-Zip, `xz -d`, or Python's `lzma`.

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
ends a function (or it is called from two places).

| shape | starts | what |
|---|---|---|
| `function` | 109,689 | ordinary code: decompiled |
| `atexit` | 48,390 | 12-byte stubs that register a destructor |
| `unwind` | 39,573 | C++ exception clean-up stubs |
| `dtor` | 1,768 | destructor of one global |
| `thunk` | 439 | a jump to another function |
| `ehandler` | 1 | exception handler stub |

Result for the 109,689:

| status | starts | |
|---|---|---|
| `ok` | 104,462 | C in `c/` |
| `inside fcn_X` | 3,886 | not a start: the address lies inside that function |
| `not analysed` | 910 | Rizin found no function there (mostly padding) |
| `not decompiled` | 415 | the decompiler gave an error |
| `skipped` | 16 | over 45 seconds or over the 1.4 GB memory ceiling |

The decompiled functions cover 25.07 MB of the 31.28 MB of code (80.1 %; 85.3 % without
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
`check.py`. The raw answers of Rizin stay in `~/pes-work/out` (not in the repository).

`check.py` is the self-check: every function has a status and every `ok` one its C; the
stack-cookie routine `fcn_038e77af` names its five Windows imports; for 300 functions the
callees are confirmed by a byte scan that does not use Rizin; 300 string references are
read back from the exe; the import slots match the file.

## Not done

- No function is named or understood yet; no structure (player record, team record) is mapped.
- Virtual calls are not resolved, so `calls.tsv.xz` misses every call through a vtable.
- The 16 skipped functions include `0x02e8c729`, which is called from 237 places.
- The encrypted `.data` section and anything the game unpacks at run time.
