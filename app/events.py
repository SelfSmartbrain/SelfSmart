"""
Role: decide which events matter. Loop prevention is critical: ignore Bot senders and CI
failures on branches that start with agent/ , otherwise the agent can fix its own failing
fixes forever. Only trusted users can trigger it by comment.
"""

try:
    import config
except ImportError:
    from app import config

TRUSTED = ('OWNER', 'MEMBER', 'COLLABORATOR')


def issue_job(repo, issue):
    return {
        'kind': 'issue',
        'repo': repo,
        'number': issue.get('number', 0),
        'text': (issue.get('title') or '') + ' ' + (issue.get('body') or ''),
    }


def to_job(event, p):
    repo = p.get('repository', {}).get('full_name')
    if p.get('sender', {}).get('type') == 'Bot':
        return None

    if event == 'workflow_run' and p.get('action') == 'completed':
        run = p.get('workflow_run', {})
        head_branch = run.get('head_branch') or ''
        if run.get('conclusion') != 'failure' or head_branch.startswith(config.BRANCH_PREFIX):
            return None
        return {'kind': 'ci', 'repo': repo, 'run_id': run.get('id'), 'branch': head_branch}

    if event == 'issues' and p.get('action') == 'labeled' and p.get('label', {}).get('name') == 'agent-fix':
        return issue_job(repo, p.get('issue', {}))

    if event == 'issue_comment':
        comment = p.get('comment', {})
        body = comment.get('body') or ''
        if '@agent fix' in body:
            if comment.get('author_association') in TRUSTED:
                return issue_job(repo, p.get('issue', {}))

    if event == 'pull_request_review_comment' and p.get('action') == 'created':
        pr = p.get('pull_request', {})
        head_ref = pr.get('head', {}).get('ref') or ''
        comment = p.get('comment', {})
        if head_ref.startswith(config.BRANCH_PREFIX) and comment.get('author_association') in TRUSTED:
            return {
                'kind': 'review',
                'repo': repo,
                'branch': head_ref,
                'number': pr.get('number', 0),
                'path': comment.get('path', ''),
                'comment': comment.get('body', ''),
            }

    return None
