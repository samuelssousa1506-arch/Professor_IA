import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                school_name TEXT,
                password TEXT NOT NULL
            )
        ''')
        conn.commit()
    finally:
        conn.close()  # Garante o fechamento automático

def create_user(name, email, school_name, password):
    conn = sqlite3.connect('database.db')
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (name, email, school_name, password) 
            VALUES (?, ?, ?, ?)
        ''', (name, email, school_name, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()  # Nunca mais deixa o banco bloqueado

def verify_user(email, password):
    conn = sqlite3.connect('database.db')
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
        user = cursor.fetchone()
        return user
    finally:
        conn.close()  # Fecha a conexão após a busca