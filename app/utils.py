import sqlite3
from flask import session, redirect, url_for
from functools import wraps

DB_PATH = '/usr/src/fastbi_tenant_db/user.db'

def get_user_status(username):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        return result[0] if result else None

def set_user_status(username, status):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET status = ? WHERE username = ?', (status, username))
        conn.commit()

def login_required(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('app_frontend_bp.login'))
        username = session['username']
        status = get_user_status(username)
        if status != 'active':
            session.clear()
            return redirect(url_for('app_frontend_bp.login'))
        return func(*args, **kwargs)
    return decorator

def set_session(username: str, email: str, remember_me: bool = False) -> None:
    session['username'] = username
    session['email'] = email
    session.permanent = remember_me