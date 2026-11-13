"""Look things up in the output files (no set-up needed, Python 3 only).

    python3 find.py show 0x038e77af        the C of one function
    python3 find.py string Player.bin      functions that refer to a string containing the text
    python3 find.py import CreateFileA     functions that use an import
    python3 find.py callers 0x038e77af     functions that call it directly
    python3 find.py callees 0x038e77af     functions it calls directly
    python3 find.py hint ProcessMatchInit  functions whose hint contains the text
    python3 find.py grep '0x1f14c50'       search the C of all functions (a few seconds)"""
import glob
import lzma
import os
import re
import sys

OUT = os.environ.get('PES_EXE_OUTPUT') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'output')


def rows(name):
    with lzma.open(os.path.join(OUT, name), 'rt', encoding='utf-8') as f:
        next(f)
        for l in f:
            yield l.rstrip('\n').split('\t')


def addr(s):
    return '0x%08x' % int(s, 16)


def functions(path):
    """-> (header line, text) for every function of one c/XXX.c.xz"""
    with lzma.open(path, 'rt', encoding='utf-8') as f:
        text = f.read()
    for part in text.split('// ==== ')[1:]:
        head, _, body = part.partition('\n')
        yield head, body


def show(a):
    a = int(a, 16)
    path = os.path.join(OUT, 'c', '%03x.c.xz' % (a >> 20))
    if os.path.exists(path):
        for head, body in functions(path):
            if head.startswith('fcn_%08x ' % a):
                return '// ==== ' + head + '\n' + body
    for r in rows('functions.tsv.xz'):
        if int(r[0], 16) == a:
            return 'no C for %s: shape %s, status %s' % (r[0], r[1], r[8])
    return 'no function starts at %#x' % a


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return
    what, arg = argv[1], argv[2]
    if what == 'show':
        print(show(arg))
    elif what == 'string':
        for f, s, t in rows('string_refs.tsv.xz'):
            if arg.lower() in t.lower():
                print('%s\t%s\t%s' % (f, s, t))
    elif what == 'import':
        for f, dll, name in rows('import_refs.tsv.xz'):
            if arg.lower() in name.lower():
                print('%s\t%s\t%s' % (f, dll, name))
    elif what in ('callers', 'callees'):
        a = addr(arg)
        for c, t in rows('calls.tsv.xz'):
            if what == 'callers' and t == a:
                print(c)
            if what == 'callees' and c == a:
                print(t)
    elif what == 'hint':
        for r in rows('functions.tsv.xz'):
            if arg.lower() in r[9].lower():
                print('%s\tsize %s\t%s' % (r[0], r[2], r[9]))
    elif what == 'grep':
        rx = re.compile(arg)
        for path in sorted(glob.glob(os.path.join(OUT, 'c', '*.c.xz'))):
            for head, body in functions(path):
                hits = [l.strip() for l in body.split('\n') if rx.search(l)]
                if hits:
                    print(head.split()[0].replace('fcn_', '0x'))
                    for h in hits[:5]:
                        print('    ' + h[:160])
    else:
        print(__doc__)


if __name__ == '__main__':
    main(sys.argv)
