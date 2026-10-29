"""
Role: the brain that wires everything. Read it top to bottom as the story of one job.
"""

try:
    import config, store, sandbox, verifier, guardrails, pr
    from github_client import GH
    from log_parser import parse, Failure
    from signature import signature
    from triage import triage
    from fixers.rule_fixers import RULES
    from fixers.llm_fixer import LLMFixer
except ImportError:
    from app import config, store, sandbox, verifier, guardrails, pr
    from app.github_client import GH
    from app.log_parser import parse, Failure
    from app.signature import signature
    from app.triage import triage
    from app.fixers.rule_fixers import RULES
    from app.fixers.llm_fixer import LLMFixer


def flag(gh, job, failure, rec):
    if job.get('number'):
        return job['number']
    if rec and rec.get('issue'):
        return rec['issue']
    body = (
        'Kind: ' + failure.kind + '\nFile: ' + (failure.file or '') + ':'
        + str(failure.line) + '\n\n' + failure.excerpt[-1500:]
    )
    return gh.create_issue('[agent] ' + failure.message[:80], body, ['agent-flagged'])


def handle_review(gh, job):
    workdir = sandbox.clone(job['repo'], job['branch'], gh.token)
    f = Failure('review', job['comment'], job.get('path', ''), 0, job['comment'])
    LLMFixer().fix(workdir, f, 'A reviewer requested this change.')
    ok, out = verifier.run(workdir)
    allowed, reason = guardrails.check(workdir)
    if ok and allowed:
        pr.push_update(gh, workdir, job['branch'], 'address review: ' + job['comment'])
    else:
        gh.comment(job['number'], 'Could not apply that safely: ' + (reason or out[-300:]))


def run_job(job):
    gh = GH(job['repo'])
    if job.get('kind') == 'review':
        return handle_review(gh, job)

    if job.get('kind') == 'ci':
        failure, base = parse(gh.run_log(job['run_id'])), job['branch']
    else:
        failure, base = Failure('unknown', (job.get('text') or '')[:500], excerpt=job.get('text') or ''), gh.default_branch()

    sig = signature(failure)
    rec = store.get(sig)
    if rec and rec.get('status') in ('pr_open', 'gave_up'):
        gh.comment(rec['issue'], 'Seen again. Status: ' + rec['status'])
        return

    issue = flag(gh, job, failure, rec)
    store.save(sig, repo=job['repo'], issue=issue, status='flagged')

    if triage(failure)['route'] == 'flag_only':
        gh.add_labels(issue, ['needs-human'])
        return

    workdir = sandbox.clone(job['repo'], base, gh.token)
    if job.get('kind') == 'ci' and verifier.run(workdir, failure.kind)[0]:
        store.save(sig, status='cannot_reproduce')
        gh.comment(issue, 'Checks pass on this branch now, so I could not reproduce it (flaky or already fixed).')
        return

    chain = [r for r in RULES if r.can_handle(failure)] + [LLMFixer()]
    feedback = ''

    for attempt in range(config.MAX_ATTEMPTS):
        sandbox.reset(workdir)
        fixer = chain[min(attempt, len(chain) - 1)]
        fixer.fix(workdir, failure, feedback)
        ok, out = verifier.run(workdir, failure.kind)
        if not ok:
            feedback = 'checks failed: ' + out
            continue
        allowed, reason = guardrails.check(workdir)
        if not allowed:
            feedback = 'rejected by guardrails: ' + reason
            continue
        url = pr.open_pr(gh, workdir, base, sig, failure, getattr(fixer, 'summary', ''), issue)
        store.save(sig, status='pr_open', pr_url=url, attempts=attempt + 1)
        return

    store.save(sig, status='gave_up', attempts=config.MAX_ATTEMPTS)
    gh.comment(issue, 'I tried ' + str(config.MAX_ATTEMPTS) + ' times and could not fix this. Last problem: ' + feedback[-500:])
    gh.add_labels(issue, ['needs-human'])
