"""Runs MLCheck.lua outside the game, against the bytes of PES2017.exe.

    python3 test_module.py <PES2017.exe>          needs: pip install lupa

The module gets only the names Sider gives a Lua module (log, memory, string, table,
ipairs, ...; no pcall, no io), and a memory.read that serves bytes from the exe file at
the game's addresses. Three runs: the real exe, an exe with one level value changed, and
an exe whose jump table is rubbish. This tests the module's logic, not Sider and not the
running game.
"""
import os
import struct
import sys

from lupa.luajit21 import LuaRuntime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import clubai                                   # noqa: E402
from layout import load, off, SECTIONS          # noqa: E402

MODULE = os.path.join(HERE, 'MLCheck.lua')
# what the module may read: the two level functions with their jump tables, and the fee numbers
ALLOWED = ((0x0365d08d, 112 + 40), (0x0365d12d, 112 + 40), (0x038ab8db, 3), (0x038ab8e6, 6),
           (0x0216ba48, 8), (0x01f0f2b8, 8))


def run(image):
    """Returns (log lines, list of (address, count) read)."""
    lua = LuaRuntime(encoding=None, unpack_returned_tuples=True)
    lines, reads = [], []

    def read(address, count):
        address, count = int(address), int(count)
        reads.append((address, count))
        o = off(address)
        assert o is not None and off(address + count - 1) == o + count - 1, 'read outside the exe image'
        return bytes(image[o:o + count])

    def log(text):
        lines.append(text.decode())

    make = lua.eval('''function(source, log, read)
        local env = { assert = assert, table = table, pairs = pairs, ipairs = ipairs, string = string,
                      math = math, tonumber = tonumber, tostring = tostring, unpack = unpack,
                      error = error, _VERSION = _VERSION, type = type,
                      os = { time = os.time, clock = os.clock, date = os.date },
                      log = log, memory = { read = read } }
        local chunk = assert(loadstring(source, "MLCheck.lua"))
        setfenv(chunk, env)
        local module = chunk()
        assert(type(module) == "table" and type(module.init) == "function")
        module.init({ sider_dir = ".\\\\", register = function() end })
    end''')
    make(open(MODULE, 'rb').read(), log, read)
    return lines, reads


def inside_allowed(reads):
    return all(any(a <= address and address + count <= a + n for a, n in ALLOWED) for address, count in reads)


def main(exe):
    image = load(exe)

    lines, reads = run(image)
    print('\n'.join(lines))
    row = lambda values: ' '.join('%2d' % v for v in values)
    assert lines[2] == 'lowest overall  %s   as expected' % row(clubai.LEVEL_MIN), lines[2]
    assert lines[3] == 'highest overall %s   as expected' % row(clubai.LEVEL_MAX), lines[3]
    assert lines[-1].startswith('RESULT: 6 of 6 as expected'), lines[-1]
    assert 'DIFFERENT' not in '\n'.join(lines) and inside_allowed(reads)
    print('ok 1: on the real exe the module prints the level windows of clubai.py and all six '
          'checks agree (%d reads, all inside the six places it may read)' % len(reads))

    changed = bytearray(image)                  # level 7, highest overall: 83 -> 84
    target = struct.unpack_from('<I', image, off(0x0365d0fd + 4 * 7))[0]
    assert changed[off(target) + 1] == 83
    changed[off(target) + 1] = 84
    lines, reads = run(changed)
    assert lines[3] == 'highest overall 74 75 76 77 78 79 80 84 86 99   DIFFERENT', lines[3]
    assert lines[-1].startswith('RESULT: only 5 of 6 as expected') and inside_allowed(reads)
    print('ok 2: one changed value is shown and counted as different')

    rubbish = bytearray(image)                  # jump table full of addresses elsewhere
    rubbish[off(0x0365d19d):off(0x0365d19d) + 40] = struct.pack('<10I', *[0x00000010 + 0x1111111 * i for i in range(10)])
    lines, reads = run(rubbish)
    assert lines[2] == 'lowest overall  ' + ' '.join(['??'] * 10) + '   DIFFERENT', lines[2]
    assert lines[-1].startswith('RESULT: only 5 of 6 as expected') and inside_allowed(reads)
    print('ok 3: with a rubbish jump table the module reports it and does not read at those addresses')


if __name__ == '__main__':
    main(sys.argv[1])
