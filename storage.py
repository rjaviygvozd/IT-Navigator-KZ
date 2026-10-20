import json
import sqlite3
from pathlib import Path
import os
from contextlib import contextmanager
DB=Path(os.environ.get('BOT_DB_PATH',str(Path(__file__).resolve().parent/'data'/'navigator.sqlite3'))).expanduser()

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con=sqlite3.connect(DB,timeout=10)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('CREATE TABLE IF NOT EXISTS results (user_id INTEGER PRIMARY KEY, track TEXT NOT NULL, scores TEXT NOT NULL)')
    con.execute('CREATE TABLE IF NOT EXISTS feedback (user_id INTEGER PRIMARY KEY, stars INTEGER NOT NULL)')
    return con

@contextmanager
def database():
    con=connect()
    try:
        with con: yield con
    finally: con.close()

def save_result(user_id,track,scores):
    with database() as db:
        db.execute('INSERT INTO results VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET track=excluded.track,scores=excluded.scores',(user_id,track,json.dumps(scores,ensure_ascii=False)))

def latest_result(user_id):
    with database() as db:
        return db.execute('SELECT track,scores FROM results WHERE user_id=?',(user_id,)).fetchone()

def save_feedback(user_id,stars):
    with database() as db:
        db.execute('INSERT INTO feedback VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET stars=excluded.stars',(user_id,stars))

def erase(user_id):
    with database() as db:
        db.execute('DELETE FROM results WHERE user_id=?',(user_id,))
        db.execute('DELETE FROM feedback WHERE user_id=?',(user_id,))

def summary():
    with database() as db:
        counts=dict(db.execute('SELECT track,COUNT(*) FROM results GROUP BY track').fetchall())
        n,stars=db.execute('SELECT COUNT(*),AVG(stars) FROM feedback').fetchone()
        total=db.execute('SELECT COUNT(*) FROM results').fetchone()[0]
        return total,counts,n,stars
