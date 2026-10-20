"""Persistence layer: PostgreSQL when DATABASE_URL is set, SQLite locally."""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB = Path(os.environ.get('BOT_DB_PATH', str(Path(__file__).resolve().parent / 'data' / 'navigator.sqlite3'))).expanduser()

def use_postgres():
    return bool(os.environ.get('DATABASE_URL', '').strip())

def connect():
    if use_postgres():
        import psycopg
        return psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=10)
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=10)
    con.execute('PRAGMA journal_mode=WAL')
    return con

@contextmanager
def database():
    con=connect()
    try:
        with con:
            if use_postgres():
                con.execute('CREATE TABLE IF NOT EXISTS results (user_id BIGINT PRIMARY KEY, track TEXT NOT NULL, scores TEXT NOT NULL)')
                con.execute('CREATE TABLE IF NOT EXISTS feedback (user_id BIGINT PRIMARY KEY, stars INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5))')
            else:
                con.execute('CREATE TABLE IF NOT EXISTS results (user_id INTEGER PRIMARY KEY, track TEXT NOT NULL, scores TEXT NOT NULL)')
                con.execute('CREATE TABLE IF NOT EXISTS feedback (user_id INTEGER PRIMARY KEY, stars INTEGER NOT NULL)')
            yield con
    finally:
        con.close()

def query(sql_sqlite, sql_pg, values=(), fetch='none'):
    with database() as con:
        cur=con.execute(sql_pg if use_postgres() else sql_sqlite, values)
        if fetch=='one': return cur.fetchone()
        if fetch=='all': return cur.fetchall()

def save_result(user_id,track,scores):
    encoded=json.dumps(scores, ensure_ascii=False)
    sql='INSERT INTO results (user_id,track,scores) VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET track=excluded.track,scores=excluded.scores'
    query(sql, sql.replace('?', '%s'), (user_id,track,encoded))

def latest_result(user_id):
    return query('SELECT track,scores FROM results WHERE user_id=?',
                 'SELECT track,scores FROM results WHERE user_id=%s',(user_id,),fetch='one')

def save_feedback(user_id,stars):
    sql='INSERT INTO feedback (user_id,stars) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET stars=excluded.stars'
    query(sql,sql.replace('?','%s'),(user_id,stars))

def erase(user_id):
    query('DELETE FROM results WHERE user_id=?','DELETE FROM results WHERE user_id=%s',(user_id,))
    query('DELETE FROM feedback WHERE user_id=?','DELETE FROM feedback WHERE user_id=%s',(user_id,))

def summary():
    counts=dict(query('SELECT track,COUNT(*) FROM results GROUP BY track',
                     'SELECT track,COUNT(*) FROM results GROUP BY track',fetch='all'))
    n, stars=query('SELECT COUNT(*),AVG(stars) FROM feedback',
                   'SELECT COUNT(*),AVG(stars) FROM feedback',fetch='one')
    total=query('SELECT COUNT(*) FROM results','SELECT COUNT(*) FROM results',fetch='one')[0]
    return total,counts,n,stars
