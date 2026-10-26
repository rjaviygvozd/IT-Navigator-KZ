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
            con.execute('CREATE TABLE IF NOT EXISTS favorites (user_id BIGINT NOT NULL, university_name TEXT NOT NULL, PRIMARY KEY (user_id,university_name))')
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

def favorite_toggle(user_id,name):
    # One transaction, serializing toggles across PostgreSQL connections.
    with database() as con:
        pg=use_postgres()
        mark='%s' if pg else '?'
        if pg:
            con.execute('SELECT pg_advisory_xact_lock(%s)', (user_id,))
        else:
            con.execute('BEGIN IMMEDIATE')
        values=(user_id,name)
        existing=con.execute(f'SELECT 1 FROM favorites WHERE user_id={mark} AND university_name={mark}',values).fetchone()
        if existing:
            con.execute(f'DELETE FROM favorites WHERE user_id={mark} AND university_name={mark}',values)
            return False
        con.execute(f'INSERT INTO favorites (user_id,university_name) VALUES ({mark},{mark})',values)
        return True

def favorites(user_id):
    return [row[0] for row in query('SELECT university_name FROM favorites WHERE user_id=? ORDER BY university_name','SELECT university_name FROM favorites WHERE user_id=%s ORDER BY university_name',(user_id,),fetch='all')]

def erase(user_id):
    # All personal records are removed together or rolled back together.
    with database() as con:
        mark='%s' if use_postgres() else '?'
        for table in ('favorites','results','feedback'):
            con.execute(f'DELETE FROM {table} WHERE user_id={mark}',(user_id,))


def check_connection():
    with database() as con:
        return con.execute('SELECT 1').fetchone()[0] == 1

def summary():
    counts=dict(query('SELECT track,COUNT(*) FROM results GROUP BY track',
                     'SELECT track,COUNT(*) FROM results GROUP BY track',fetch='all'))
    n, stars=query('SELECT COUNT(*),AVG(stars) FROM feedback',
                   'SELECT COUNT(*),AVG(stars) FROM feedback',fetch='one')
    total=query('SELECT COUNT(*) FROM results','SELECT COUNT(*) FROM results',fetch='one')[0]
    return total,counts,n,stars
