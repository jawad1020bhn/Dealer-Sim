"""Decompile every start of shape `function` to C, in batches, through REA.

    python3 decompile.py <PES2017.exe> <functions_found.tsv> <work folder> [workers] [batch size]

One batch is one `rea execute-rizin-command <exe> '. batch.rz'`: for every
address Rizin analyses the function (af), prints its facts (afij) and the C of
the Ghidra decompiler (pdg). The raw answers stay in <work folder>/batches
(NNNNN.out, .err, .json = the REA Evidence record); assemble.py builds the
output files from them. Run it again to continue: finished batches are skipped.

One function may take 45 seconds. A watchdog then stops Rizin (so does the
memory ceiling of rizin-limited.sh); REA still returns what was printed, the
function is put on the batch's skipped list and the rest of the batch runs in
a new REA call. A batch can therefore have several Evidence ids."""
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import rea

TIMEOUT_MS = 900000      # REA's own deadline for one call
PER_FUNCTION = 45        # seconds


def script(addrs, cur):
    s = []
    for a in addrs:
        s.append('echo %s > %s\naf @ %s\necho FN_BEGIN %s\nafij @ %s\necho FN_CODE\npdg @ %s\necho FN_END %s\n'
                 % (a, cur, a, a, a, a, a))
    s.append('echo BATCH_END\n')
    return ''.join(s)


def watchdog(base, stop):
    name = os.path.basename(base)
    while not stop.wait(2):
        try:
            if time.time() - os.path.getmtime(base + '.cur') > PER_FUNCTION:
                os.system("pkill -f 'bin/rizin -N -q .*/%s[.]rz'" % name)
                stop.wait(5)
        except OSError:
            pass


def one(exe, work, n, addrs):
    base = os.path.join(work, 'batches', '%05d' % n)
    if os.path.exists(base + '.json'):
        return n, 'done before', 0
    t = time.time()
    outs, errs, ids, skipped, todo = [], [], [], [], list(addrs)
    while todo:
        open(base + '.rz', 'w').write(script(todo, base + '.cur'))
        open(base + '.cur', 'w').write(todo[0])
        stop = threading.Event()
        w = threading.Thread(target=watchdog, args=(base, stop))
        w.start()
        try:
            out, err, rec = rea.run(exe, '. ' + base + '.rz', TIMEOUT_MS)
        except RuntimeError as e:
            return n, 'failed: %s' % str(e)[:200], time.time() - t
        finally:
            stop.set()
            w.join()
        outs.append(out)
        errs.append(err)
        ids.append(rec['evidence_id'])
        if 'BATCH_END' in out:
            break
        bad = open(base + '.cur').read().strip()      # stopped or crashed here
        if bad not in todo:
            return n, 'failed: %s' % rea.status(rec), time.time() - t
        skipped.append(bad)
        todo = todo[todo.index(bad) + 1:]
    open(base + '.out', 'w').write(''.join(outs))
    open(base + '.err', 'w').write(''.join(errs))
    open(base + '.json', 'w').write(json.dumps({'evidence_ids': ids, 'skipped': skipped, 'functions': len(addrs)}))
    for x in ('.rz', '.cur'):
        os.remove(base + x)
    return n, 'ok, %d skipped' % len(skipped), time.time() - t


def main(exe, found, work, workers=2, size=1000):
    work = os.path.abspath(work)
    os.makedirs(os.path.join(work, 'batches'), exist_ok=True)
    addrs = [l.split('\t')[0] for l in open(found).read().split('\n')[1:]
             if l and l.split('\t')[4] == 'function']
    jobs = [(i // size, addrs[i:i + size]) for i in range(0, len(addrs), size)]
    print('%d functions, %d batches' % (len(addrs), len(jobs)), flush=True)
    with ThreadPoolExecutor(workers) as ex:
        for n, st, secs in ex.map(lambda j: one(exe, work, *j), jobs):
            print('batch %05d %s %.0f s' % (n, st, secs), flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], *[int(x) for x in sys.argv[4:]])
