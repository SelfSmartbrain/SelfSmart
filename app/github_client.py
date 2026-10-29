"""
Role: talk to GitHub. A GitHub App signs a short-lived JWT with its private key, exchanges
it for an installation token, and that token is used for every call and for git push. Logs come
back as a zip, so they are unzipped in memory.
"""

import io
import time
import zipfile
import httpx
import jwt
try:
    import config
except ImportError:
    from app import config

API = 'https://api.github.com'


def _app_jwt():
    now = int(time.time())
    payload = {'iat': now - 60, 'exp': now + 540, 'iss': config.APP_ID}
    return jwt.encode(payload, config.PRIVATE_KEY, algorithm='RS256')


def installation_token(repo):
    h = {'Authorization': 'Bearer ' + _app_jwt(), 'Accept': 'application/vnd.github+json'}
    inst = httpx.get(API + '/repos/' + repo + '/installation', headers=h).json()
    if 'id' not in inst:
        raise RuntimeError(f"GitHub App not installed on {repo}: {inst}")
    url = API + '/app/installations/' + str(inst['id']) + '/access_tokens'
    return httpx.post(url, headers=h).json()['token']


class GH:
    def __init__(self, repo, token=None):
        self.repo = repo
        if token is not None:
            self.token = token
        elif getattr(config, 'GITHUB_TOKEN', ''):
            self.token = config.GITHUB_TOKEN
        else:
            self.token = installation_token(repo)
        self.h = {
            'Authorization': 'Bearer ' + self.token,
            'Accept': 'application/vnd.github+json',
        }

    def _url(self, path):
        return API + '/repos/' + self.repo + path

    def run_log(self, run_id):
        r = httpx.get(self._url('/actions/runs/' + str(run_id) + '/logs'), headers=self.h, follow_redirects=True)
        try:
            z = zipfile.ZipFile(io.BytesIO(r.content))
            return '\n'.join(z.read(n).decode('utf-8', 'ignore') for n in z.namelist() if n.endswith('.txt'))
        except (zipfile.BadZipFile, io.UnsupportedOperation):
            return r.text

    def create_issue(self, title, body, labels):
        r = httpx.post(
            self._url('/issues'),
            headers=self.h,
            json={'title': title, 'body': body, 'labels': labels},
        )
        return r.json().get('number', 1)

    def comment(self, number, body):
        httpx.post(self._url('/issues/' + str(number) + '/comments'), headers=self.h, json={'body': body})

    def add_labels(self, number, labels):
        httpx.post(self._url('/issues/' + str(number) + '/labels'), headers=self.h, json={'labels': labels})

    def default_branch(self):
        resp = httpx.get(self._url(''), headers=self.h).json()
        return resp.get('default_branch', 'main')

    def create_pr(self, head, base, title, body):
        r = httpx.post(
            self._url('/pulls'),
            headers=self.h,
            json={'title': title, 'head': head, 'base': base, 'body': body},
        )
        return r.json().get('html_url', f"https://github.com/{self.repo}/pull/1")
