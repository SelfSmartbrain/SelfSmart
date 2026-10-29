"""
Role: pick the route. Rule route is cheap and predictable. LLM route is for logic bugs. Flag-only
means a human must look.
"""


def triage(f):
    if f.kind in ('lint', 'import'):
        return {'route': 'rule', 'severity': 'low'}
    if f.kind == 'unknown' and not f.message:
        return {'route': 'flag_only', 'severity': 'unknown'}
    return {'route': 'llm', 'severity': 'medium'}
