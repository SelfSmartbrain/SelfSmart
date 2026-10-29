"""
Role: turn a huge CI log into one Failure object. GitHub prefixes every log line with a
timestamp, so strip those first or the ^ anchored regexes never match. Order matters:
most specific patterns first. Kinds: lint , type , import , test , runtime , unknown .
"""

import re
from dataclasses import dataclass


@dataclass
class Failure:
    kind: str
    message: str
    file: str = ''
    line: int = 0
    excerpt: str = ''


def parse(text: str) -> Failure:
    # GitHub prefixes every log line with an ISO timestamp like '2024-01-01T12:00:00.0000000Z '
    text = re.sub(r'^[0-9T:.-]+Z ', '', text, flags=re.M)
    lines = text.splitlines()
    tail = '\n'.join(lines[-80:]) if lines else ''

    # 1. Missing import / module
    m = re.search(r'No module named .([A-Za-z0-9_]+)', text)
    if m:
        return Failure('import', m.group(1), excerpt=tail)

    # 2. Linter error (e.g. ruff, flake8: file:line:col: CODE description)
    m = re.search(r'^([^: \n]+):([0-9]+):[0-9]+: ([A-Z]+[0-9]+) (.*)$', text, re.M)
    if m:
        return Failure('lint', m.group(3) + ' ' + m.group(4), m.group(1), int(m.group(2)), tail)

    # 3. Type checker error (e.g. mypy: file:line: error: message)
    m = re.search(r'^([^: \n]+):([0-9]+): error: (.*)$', text, re.M)
    if m:
        return Failure('type', m.group(3), m.group(1), int(m.group(2)), tail)

    # 4. Test failure (e.g. pytest: FAILED file::test_name - assertion message)
    m = re.search(r'FAILED ([^: \n]+)::([^ \n]+)(?: - (.*))?', text)
    if m:
        return Failure('test', m.group(3) or m.group(2), m.group(1), 0, tail)

    # 5. Generic runtime exception
    m = re.search(r'^([A-Za-z]+Error: .*)$', text, re.M)
    if m:
        return Failure('runtime', m.group(1), excerpt=tail)

    return Failure('unknown', lines[-1] if lines else '', excerpt=tail)
