"""
Role: prove the fix works by running the same checks CI runs. The first call builds a .venv
(network on), later calls run tests with the network off. For a lint failure it re-runs the
linter. For Node repos, add a branch that uses the node:20 image and npm ci && npm
test .
"""

import os
try:
    import sandbox
except ImportError:
    from app import sandbox


def run(workdir, kind=''):
    if os.path.exists(workdir + '/requirements.txt') and not os.path.exists(workdir + '/.venv'):
        sandbox.run(workdir, 'python -m venv .venv && .venv/bin/pip install -q -r requirements.txt', network=True)

    if kind == 'lint':
        code, out = sandbox.run(workdir, 'pip install -q --user ruff && ruff check .', network=True)
        return code == 0, out[-4000:]

    if os.path.exists(workdir + '/tests') or os.path.exists(workdir + '/pytest.ini'):
        cmd = '.venv/bin/python -m pytest -x -q' if os.path.exists(workdir + '/.venv') else 'pytest -x -q'
        code, out = sandbox.run(workdir, cmd)
        return code == 0, out[-6000:]

    return False, 'no test command found'
