import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "resume_ai.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        job_title TEXT,
        created_at TEXT NOT NULL,
        resume_input TEXT NOT NULL,
        job_description TEXT NOT NULL,
        ats_resume TEXT NOT NULL,
        cover_letter TEXT NOT NULL,
        missing_skills TEXT NOT NULL,
        linkedin_summary TEXT NOT NULL,
        job_match_score REAL NOT NULL,
        model TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()

def create_user(username, email, password_hash):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (username, email, password_hash, created_at)
        VALUES (?, ?, ?, ?)
    """, (username, email, password_hash, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_user_by_username(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cur.fetchone()
    conn.close()
    return user

def save_history(user_id, job_title, resume_input, job_description,
                 ats_resume, cover_letter, missing_skills, linkedin_summary,
                 job_match_score, model):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO history (
            user_id, job_title, created_at,
            resume_input, job_description,
            ats_resume, cover_letter, missing_skills, linkedin_summary,
            job_match_score, model
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, job_title, datetime.utcnow().isoformat(),
        resume_input, job_description,
        ats_resume, cover_letter, missing_skills, linkedin_summary,
        job_match_score, model
    ))
    conn.commit()
    conn.close()

def get_user_history(user_id, limit=30):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, job_title, created_at, job_match_score, model
        FROM history
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (user_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_history_item(history_id, user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM history
        WHERE id = ? AND user_id = ?
    """, (history_id, user_id))
    row = cur.fetchone()
    conn.close()
    return row
