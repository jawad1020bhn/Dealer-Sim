"""Run one Rizin command on the exe through REA (rea execute-rizin-command).

REA starts `rizin -N -q -e scr.color=0 -c <command> <exe>`, checks the exe's
sha256 before and after, and returns an Evidence record. Needs the set-up of
../../../rea-setup.sh. Rizin runs through rizin-limited.sh (memory ceiling);
RIZIN names another Rizin than ~/pes-work/rz/bin/rizin."""
import json
import os
import subprocess

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
REA = os.path.join(REPO, 'node_modules', '.bin', 'rea')
EXE_SHA256 = '44b0caaac6703459f1a674ab7defc98d39613008b9254646f2543431fa9d954f'


def run(exe, command, timeout_ms=120000):
    """-> (stdout of Rizin, stderr of Rizin, record without the two copies of the output)"""
    env = dict(os.environ)
    env['REA_RIZIN_COMMAND'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rizin-limited.sh')
    env['PATH'] = os.path.dirname(REA) + os.pathsep + env['PATH']     # the pinned Node 24
    p = subprocess.run(
        [REA, 'execute-rizin-command', os.path.abspath(exe), command, '--format', 'json',
         '--command-timeout-ms', str(timeout_ms), '--max-output-bytes', '44000000'],
        capture_output=True, text=True, env=env, cwd=REPO)
    try:
        rec = json.loads(p.stdout)
        raw = rec['raw_result']
    except (ValueError, KeyError):
        raise RuntimeError('REA gave no Evidence record: %s %s' % (p.stdout[:300], p.stderr[:300]))
    out, err = raw.pop('stdout', '') or '', raw.pop('stderr', '') or ''
    rec.pop('normalized_result', None)
    if rec['subject']['digest']['sha256'] != EXE_SHA256:
        raise RuntimeError('not the PES2017.exe this work is about')
    return out, err, rec


def status(rec):
    r = rec['raw_result']
    return 'ok' if r.get('exit_code') == 0 and r.get('completion_status') == 'complete' \
        and not r.get('output_truncated') else 'exit=%s %s truncated=%s' % (
            r.get('exit_code'), r.get('completion_status'), r.get('output_truncated'))
