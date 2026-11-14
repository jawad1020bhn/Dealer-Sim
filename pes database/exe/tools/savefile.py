"""The PES 2017 save container (EDIT00000000 and the other files of the save
folder), written from the game's own code. Python 3 only, no other tool.

    python3 savefile.py check <save file>            # the game's checks + the five hashes
    python3 savefile.py unpack <save file> <folder>  # description.dat, logo.png, data.dat, serial.txt, header.dat
    python3 savefile.py fix <save file> <out file>   # same content, the five hashes recomputed
    python3 savefile.py pack <save file> <data.dat> <out file>   # the save with new data, hashes recomputed

Layout (reader fcn_0378d643, writer fcn_0378cd8d, see ../NOTES.md):

    0x000  320  five SHA-512 hashes: description, logo, data, serial, file header.
                The fifth is stored as it is; the first four are encrypted with
                key = fifth hash XOR MASTER.
    0x140  176  file header, encrypted with stream key 0xb0:
                  +0x00 64  MASTER
                  +0x40 4x4 data size, logo size, description size (0x180), serial length in characters
                  +0x50 64  random bytes (CryptGenRandom), a new value on each save
                  +0x90 32  file type text, "EDIT"
    0x1f0       description (stream key 0), logo (1), data (2), serial in UTF-16 (3)

MASTER is SHA-512 of the UTF-16 text "Pro Evolution Soccer 2017", the folder
name of the save (fcn_03791698). A stream key is the XOR of the five hashes
with the key number XORed into each 8 bytes (fcn_0378b203). The stream is
MT19937 seeded with the 64 key bytes, five outputs mixed per word (fcn_0378b253).
"""
import hashlib
import os
import random
import struct
import sys

GAME_NAME = 'Pro Evolution Soccer 2017'
MASTER = hashlib.sha512(GAME_NAME.encode('utf-16-le')).digest()
DESC_SIZE, HEAD_SIZE, HASHES_SIZE = 0x180, 0xb0, 0x140
PARTS = ('description', 'logo', 'data', 'serial')
M32 = 0xffffffff


def _mt(key):
    """random.Random in the state MT19937 init_by_array(key as 16 words) gives."""
    key = struct.unpack('<16I', key)
    mt = [19650218]
    for i in range(1, 624):
        mt.append((1812433253 * (mt[-1] ^ (mt[-1] >> 30)) + i) & M32)
    i, j = 1, 0
    for _ in range(624):
        mt[i] = ((mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >> 30)) * 1664525)) + key[j] + j) & M32
        i += 1
        j = (j + 1) % 16
        if i >= 624:
            mt[0] = mt[623]
            i = 1
    for _ in range(623):
        mt[i] = ((mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >> 30)) * 1566083941)) - i) & M32
        i += 1
        if i >= 624:
            mt[0] = mt[623]
            i = 1
    mt[0] = 0x80000000
    r = random.Random()
    r.setstate((3, tuple(mt) + (624,), None))
    return r


def _ror(x, k):
    return ((x >> k) | (x << (32 - k))) & M32


def _lanes_ror(x, k, n):
    """Rotate each of the n 32-bit lanes of the integer x right by k."""
    lo = int.from_bytes(struct.pack('<I', M32 >> k) * n, 'little')
    return ((x >> k) & lo) | ((x & int.from_bytes(struct.pack('<I', (1 << k) - 1) * n, 'little')) << (32 - k))


def crypt_stream(key, data):
    """fcn_0378b253: the same call encrypts and decrypts."""
    n = (len(data) + 3) // 4
    if n == 0:
        return b''
    r = _mt(key)
    m = r.getrandbits(32 * (n + 4))               # lane j is the j-th generator output
    head = [(m >> (32 * j)) & M32 for j in range(min(n + 4, 8))]
    # from the fifth word on, word i is: m[i+4] ^ ror13(m[i+3]) ^ ror6(m[i+2]) ^ rol5(m[i+1]) ^ ror10(m[i])
    ks = ((m >> 128) ^ _lanes_ror(m >> 96, 13, n) ^ _lanes_ror(m >> 64, 6, n)
          ^ _lanes_ror(m >> 32, 27, n) ^ _lanes_ror(m, 10, n)) & ((1 << (32 * n)) - 1)
    c0, c1, c2, c3 = head[:4]                     # the first four words, step by step as in the game
    for i in range(min(n, 4)):
        c4 = head[4 + i]
        w = c4 ^ c3 ^ c2 ^ c1 ^ c0
        ks = (ks & ~(M32 << (32 * i))) | (w << (32 * i))
        c0, c1, c2, c3 = _ror(c1, 15), _ror(c2, 21), _ror(c3, 25), _ror(c4, 13)
    x = int.from_bytes(data + b'\0' * (4 * n - len(data)), 'little') ^ ks
    return x.to_bytes(4 * n, 'little')[:len(data)]


def _xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def _stream_key(hashes, number):
    rolling = bytes(64)
    for i in range(5):
        rolling = _xor(rolling, hashes[64 * i:64 * i + 64])
    return _xor(rolling, struct.pack('<Q', number) * 8)


def _crypt_hashes(block):
    """fcn_0378b6bd / fcn_0378b789: the first 256 bytes change, the last 64 stay."""
    return crypt_stream(_xor(block[256:], MASTER), block)[:256] + block[256:]


def read(path):
    """Decrypt a save file. Returns a dict: hashes (320 bytes), header (176),
    description, logo, data, serial (bytes), and sizes as the header gives them."""
    f = open(path, 'rb').read()
    assert len(f) >= HASHES_SIZE + HEAD_SIZE, 'file too short'
    s = {'hashes': _crypt_hashes(f[:HASHES_SIZE])}
    o = HASHES_SIZE
    s['header'] = crypt_stream(_stream_key(s['hashes'], HEAD_SIZE), f[o:o + HEAD_SIZE])
    o += HEAD_SIZE
    data, logo, desc, serial = struct.unpack_from('<4I', s['header'], 0x40)
    for number, (name, size) in enumerate((('description', desc), ('logo', logo), ('data', data),
                                           ('serial', serial * 2))):
        assert o + size <= len(f), '%s runs past the end of the file' % name
        s[name] = crypt_stream(_stream_key(s['hashes'], number), f[o:o + size])
        o += size
    s['unused_tail'] = len(f) - o
    return s


def true_hashes(s):
    return b''.join(hashlib.sha512(s[k]).digest() for k in PARTS + ('header',))


def write(s, keep_hashes=False):
    """Encrypt. keep_hashes=True writes s['hashes'] as they are (exact copy of a
    file that was read); otherwise the five hashes are computed from the parts."""
    header = bytearray(s['header'])
    struct.pack_into('<4I', header, 0x40, len(s['data']), len(s['logo']), len(s['description']),
                     len(s['serial']) // 2)
    s = dict(s, header=bytes(header))
    hashes = s['hashes'] if keep_hashes else true_hashes(s)
    out = [_crypt_hashes(hashes), crypt_stream(_stream_key(hashes, HEAD_SIZE), s['header'])]
    for number, name in enumerate(PARTS):
        out.append(crypt_stream(_stream_key(hashes, number), s[name]))
    return b''.join(out)


def check(s, file_type='EDIT'):
    """[(verdict, text)]: first what the game's reader tests, then the hashes.
    verdict is 'ok', 'FAIL' (the game refuses the file) or 'note'."""
    h = s['header']
    res = []

    def add(good, text, bad='FAIL'):
        res.append(('ok' if good else bad, text))
    data, logo, desc, serial = struct.unpack_from('<4I', h, 0x40)
    add(desc == DESC_SIZE, 'description size is 0x180 (it is 0x%x)' % desc)
    kind = h[0x90:0xb0].split(b'\0')[0].decode('latin1')
    add(kind == file_type, 'file type text is "%s" (it is "%s")' % (file_type, kind))
    add(s['unused_tail'] == 0, 'no bytes after the last part (%d)' % s['unused_tail'], 'note')
    add(h[:64] == MASTER, 'header starts with SHA-512 of "%s"' % GAME_NAME, 'note')
    true = true_hashes(s)
    for i, name in enumerate(PARTS + ('header',)):
        add(true[64 * i:64 * i + 64] == s['hashes'][64 * i:64 * i + 64],
            'stored hash of the %s (%d bytes) is its SHA-512' % (name, len(s[name])), 'note')
    return res


def main(argv):
    if len(argv) < 3 or argv[1] not in ('check', 'unpack', 'fix', 'pack') or len(argv) < {'check': 3, 'pack': 5}.get(argv[1], 4):
        print(__doc__)
        return 2
    s = read(argv[2])
    if argv[1] == 'check':
        res = check(s)
        for verdict, text in res:
            print('%-4s %s' % (verdict, text))
        if any(v == 'note' for v, _ in res):
            print('note = differs from a file the game wrote; the reader does not refuse it (NOTES.md, save file)')
        return 1 if any(v == 'FAIL' for v, _ in res) else 0
    if argv[1] == 'unpack':
        os.makedirs(argv[3], exist_ok=True)
        for name, ext in (('description', 'dat'), ('logo', 'png'), ('data', 'dat'), ('serial', 'txt'),
                          ('header', 'dat'), ('hashes', 'dat')):
            open(os.path.join(argv[3], name + '.' + ext), 'wb').write(s[name])
        print('wrote 6 files to', argv[3])
        return 0
    dest, what = argv[3], 'content identical'
    if argv[1] == 'pack':
        new = open(argv[3], 'rb').read()
        assert len(new) == len(s['data']), 'data.dat has another size than the data of the save'
        s, dest, what = dict(s, data=new), argv[4], 'data replaced'
    out = write(s)
    open(dest, 'wb').write(out)
    back = read(dest)
    assert all(back[k] == s[k] for k in PARTS + ('header',)) and back['hashes'] == true_hashes(s)
    print('wrote %s (%d bytes); %s, five hashes recomputed' % (dest, len(out), what))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
