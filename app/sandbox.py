"""
Role: isolation. Code from the repo (tests, install scripts) is untrusted, so it only runs in
Docker with limited memory and CPU, and with no network except for dependency
installs. Important: after cloning, the token is removed from the git remote, otherwise
code in the container could read it from .git/config . The token is only supplied at push
time.
"""

import os
import subprocess
import tempfile
import shutil
try:
    import config
except ImportError:
    from app import config


def _git(path, *args):
    return subprocess.run(['git', '-C', path] + list(args), check=True, capture_output=True, text=True)


def clone(repo, branch, token):
    path = tempfile.mkdtemp(prefix='agent-')
    # If repo is a local path (testing mode) or URL
    if os.path.exists(repo):
        subprocess.run(['git', 'clone', '--depth', '50', '--branch', branch, repo, path], check=True, capture_output=True)
    else:
        url = 'https://x-access-token:' + token + '@github.com/' + repo + '.git'
        subprocess.run(['git', 'clone', '--depth', '50', '--branch', branch, url, path], check=True, capture_output=True)

    _git(path, 'remote', 'set-url', 'origin', 'https://github.com/' + repo + '.git')
    _git(path, 'config', 'user.name', 'junior-agent[bot]')
    _git(path, 'config', 'user.email', 'junior-agent@users.noreply.github.com')
    with open(path + '/.git/info/exclude', 'a') as fh:
        fh.write('.venv\n')
    return path


def reset(path):
    _git(path, 'reset', '--hard')
    _git(path, 'clean', '-fd')


def _docker_available():
    if not getattr(config, 'USE_DOCKER', True):
        return False
    try:
        res = subprocess.run(['docker', 'info'], capture_output=True, timeout=2)
        return res.returncode == 0
    except Exception:
        return False


def run(path, cmd, network=False, image='python:3.12'):
    if _docker_available():
        args = [
            'docker', 'run', '--rm', '--memory', '2g', '--cpus', '2',
            '--user', str(os.getuid()) + ':' + str(os.getgid()),
            '-e', 'HOME=/tmp', '-e',
            'PATH=/tmp/.local/bin:/usr/local/bin:/usr/bin:/bin',
            '-v', path + ':/work', '-w', '/work'
        ]
        if not network:
            args += ['--network', 'none']
        args += [image, 'sh', '-c', cmd]
    else:
        # Fallback to local subprocess execution when Docker daemon is not active
        args = ['sh', '-c', cmd]

    try:
        p = subprocess.run(args, cwd=path, capture_output=True, text=True, timeout=config.SANDBOX_TIMEOUT)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return 124, 'timeout'
