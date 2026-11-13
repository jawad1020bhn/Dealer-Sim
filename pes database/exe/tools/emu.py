"""Run single functions of PES2017.exe on chosen inputs (CPU emulator, no Windows).

    from emu import Game
    g = Game('/path/PES2017.exe')
    p = g.alloc(b'bytes ...')                 # scratch memory, returns its address
    eax = g.call(0x04067af3, [p, 0])          # cdecl / stdcall: arguments on the stack
    eax = g.call(0x0378933e, [], ecx=p)       # thiscall / register arguments
    data = g.read(p, 64)

Needs `pip install unicorn`. The whole image is mapped at its own addresses.
Four C-library imports (memset, memcpy, memmove, strcpy_s) are answered in
Python; any other import stops the run with an error. `g.replace(address, fn)`
puts a Python function in the place of a game function (fn(game, stack
arguments reader) -> eax), so that a formula can be run without the data it
would fetch: the callers of the look-up functions get chosen values. A page is mapped at
address 0, so a function that sets up an exception frame (fs:[0]) runs;
functions that call Windows are out of reach.
"""
import struct

from unicorn import Uc, UcError, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESI,
                               UC_X86_REG_EDI, UC_X86_REG_EBX, UC_X86_REG_ESP, UC_X86_REG_EBP,
                               UC_X86_REG_EIP)

from layout import SECTIONS, load

STACK, STACK_SIZE = 0x00100000, 0x00100000
HEAP, HEAP_SIZE = 0x70000000, 0x04000000
STUBS = 0x00300000            # fake import addresses
RETURN = 0x00301000           # a call returns here; the run stops
IMPORTS = {0x047d7584: 'memset', 0x047d7798: 'memcpy', 0x047d7624: 'memmove', 0x047d7534: 'strcpy_s'}
REG = {'eax': UC_X86_REG_EAX, 'ecx': UC_X86_REG_ECX, 'edx': UC_X86_REG_EDX, 'esi': UC_X86_REG_ESI,
       'edi': UC_X86_REG_EDI, 'ebx': UC_X86_REG_EBX}


def _page(a):
    return a & ~0xfff


class Game:
    def __init__(self, exe):
        d = load(exe)
        self.mu = mu = Uc(UC_ARCH_X86, UC_MODE_32)
        lo = _page(min(v for _, v, _, _ in SECTIONS))
        hi = _page(max(v + s for _, v, _, s in SECTIONS) + 0xfff)
        mu.mem_map(lo, hi - lo)
        for _, v, f, s in SECTIONS:
            mu.mem_write(v, d[f:f + s])
        mu.mem_map(STACK, STACK_SIZE)
        mu.mem_map(HEAP, HEAP_SIZE)
        mu.mem_map(STUBS, 0x2000)
        mu.mem_map(0, 0x1000)                          # fs:[0], the exception frame list
        self.stub = {}
        for i, (slot, name) in enumerate(sorted(IMPORTS.items())):
            mu.mem_write(slot, struct.pack('<I', STUBS + 16 * i))
            self.stub[STUBS + 16 * i] = name
        mu.hook_add(UC_HOOK_CODE, self._import, begin=STUBS, end=STUBS + 0xfff)
        self.top = HEAP
        self.replaced = {}
        self.exe = d

    def _import(self, mu, address, size, user):
        esp = mu.reg_read(UC_X86_REG_ESP)
        ret, a, b, c = struct.unpack('<4I', mu.mem_read(esp, 16))
        name = self.stub.get(address)
        if name == 'memset':
            mu.mem_write(a, bytes([b & 0xff]) * c)
        elif name in ('memcpy', 'memmove'):
            mu.mem_write(a, bytes(mu.mem_read(b, c)))
        elif name == 'strcpy_s':                       # (destination, size, source)
            text = bytes(mu.mem_read(c, b)).split(b'\0')[0]
            assert len(text) < b, 'strcpy_s: text longer than the buffer'
            mu.mem_write(a, text + b'\0')
            a = 0
        else:
            raise RuntimeError('import not emulated at 0x%x' % address)
        mu.reg_write(UC_X86_REG_EAX, a)
        mu.reg_write(UC_X86_REG_ESP, esp + 4)          # cdecl: the caller removes the arguments
        mu.reg_write(UC_X86_REG_EIP, ret)

    def replace(self, address, fn):
        """Answer calls to the game function at `address` with fn(game, arg) -> eax, where
        arg(i) is stack argument i. The stack is cleaned as the real function does it
        (its `ret n` is read from its code)."""
        import capstone
        from layout import off
        md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        n = None
        o = off(address)
        for ins in md.disasm(self.exe[o:o + 0x4000], address):
            if ins.mnemonic == 'ret':
                n = int(ins.op_str, 0) if ins.op_str else 0
                break
        assert n is not None, 'no ret found in 0x%x' % address
        if not self.replaced:
            self.mu.hook_add(UC_HOOK_CODE, self._replaced)
        self.replaced[address] = (fn, n)

    def _replaced(self, mu, address, size, user):
        if address not in self.replaced:
            return
        fn, n = self.replaced[address]
        esp = mu.reg_read(UC_X86_REG_ESP)
        ret = struct.unpack('<I', mu.mem_read(esp, 4))[0]
        arg = lambda i: struct.unpack('<I', mu.mem_read(esp + 4 + 4 * i, 4))[0]
        mu.reg_write(UC_X86_REG_EAX, fn(self, arg) & 0xffffffff)
        mu.reg_write(UC_X86_REG_ESP, esp + 4 + n)
        mu.reg_write(UC_X86_REG_EIP, ret)

    def alloc(self, data=b'', size=None):
        size = max(len(data), size or 0, 1)
        a = self.top
        self.top = (a + size + 15) & ~15
        assert self.top <= HEAP + HEAP_SIZE, 'scratch memory full'
        self.mu.mem_write(a, bytes(data) + b'\0' * (size - len(data)))
        return a

    def free_all(self):
        self.top = HEAP

    def read(self, a, n):
        return bytes(self.mu.mem_read(a, n))

    def write(self, a, data):
        self.mu.mem_write(a, bytes(data))

    def call(self, address, args=(), limit=0, **regs):
        """Call `address`; return eax. Stops at the function's return."""
        mu = self.mu
        esp = STACK + STACK_SIZE - 0x1000
        frame = struct.pack('<%dI' % (len(args) + 1), RETURN, *[a & 0xffffffff for a in args])
        esp -= len(frame)
        mu.mem_write(esp, frame)
        mu.reg_write(UC_X86_REG_ESP, esp)
        mu.reg_write(UC_X86_REG_EBP, 0)
        for k in REG:
            mu.reg_write(REG[k], regs.get(k, 0) & 0xffffffff)
        try:
            mu.emu_start(address, RETURN, count=limit)
        except UcError as e:
            raise RuntimeError('emulation of 0x%08x stopped at 0x%08x: %s' % (
                address, mu.reg_read(UC_X86_REG_EIP), e))
        assert mu.reg_read(UC_X86_REG_EIP) == RETURN, 'instruction limit reached'
        return mu.reg_read(UC_X86_REG_EAX)

    def reg(self, name):
        return self.mu.reg_read(REG[name])
