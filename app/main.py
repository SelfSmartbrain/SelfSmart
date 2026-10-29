"""
Role: the front door. Three checks before any work: the HMAC signature proves the
request came from GitHub, the delivery id blocks duplicates, and the job is run in the
background so GitHub gets a fast 200 response (it times out after about 10 seconds).
"""

import hashlib
import hmac
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
try:
    import config, events, store, orchestrator
except ImportError:
    from app import config, events, store, orchestrator

app = FastAPI(title="Junior Engineering Agent")


@app.post('/webhook')
async def webhook(request: Request, tasks: BackgroundTasks):
    body = await request.body()
    got = request.headers.get('X-Hub-Signature-256', '')
    want = 'sha256=' + hmac.new(config.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(got, want):
        raise HTTPException(401, 'bad signature')

    delivery_id = request.headers.get('X-GitHub-Delivery', '')
    if store.seen_delivery(delivery_id):
        return {'status': 'duplicate'}

    payload = await request.json() if body else {}
    job = events.to_job(request.headers.get('X-GitHub-Event', ''), payload)
    if job:
        tasks.add_task(orchestrator.run_job, job)

    return {'status': 'queued' if job else 'ignored'}
