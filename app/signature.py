"""
Role: fingerprint the error so the same bug always produces the same id. Numbers and
memory addresses are replaced, because they change on every run.
"""

import hashlib
import re


def signature(f):
    msg = (f.message or '').lower()
    # Normalize memory addresses (e.g. 0x7ffee1b2c)
    msg = re.sub(r'0x[0-9a-f]+', 'ADDR', msg)
    # Normalize numbers (e.g. line numbers, timestamps, process ids)
    msg = re.sub(r'[0-9]+', 'N', msg)
    raw = f.kind + '|' + (f.file or '') + '|' + msg
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]
