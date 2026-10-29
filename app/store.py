"""
Role: memory. Remembers which errors were already handled (so one bug does not
create 20 issues) and which webhook deliveries were already processed (GitHub retries
deliveries).
"""

import sqlite3
try:
    import config
except ImportError:
    from app import config

db = sqlite3.connect(config.DB_PATH, check_same_thread=False)
db.execute(
    'create table if not exists errors (sig text primary key, repo text, issue int, status text, attempts int default 0, pr_url text)'
)
db.execute('create table if not exists deliveries (id text primary key)')
db.commit()


def seen_delivery(delivery_id):
    if not delivery_id:
        return False
    try:
        db.execute('insert into deliveries values (?)', (delivery_id,))
        db.commit()
        return False
    except sqlite3.IntegrityError:
        return True


def get(sig):
    row = db.execute(
        'select sig, repo, issue, status, attempts, pr_url from errors where sig=?', (sig,)
    ).fetchone()
    if not row:
        return None
    return dict(zip(['sig', 'repo', 'issue', 'status', 'attempts', 'pr_url'], row))


def save(sig, **fields):
    if not get(sig):
        db.execute('insert into errors (sig) values (?)', (sig,))
        db.commit()
    if fields:
        set_clause = ', '.join(f"{key}=?" for key in fields.keys())
        values = list(fields.values()) + [sig]
        db.execute(f'update errors set {set_clause} where sig=?', values)
        db.commit()
