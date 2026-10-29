import hmac
import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash


def init_db():
    """Create the user table using the same schema as the Flask application."""
    with sqlite3.connect("database.db") as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                escola TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL
            )
            """
        )


def create_user(name, email, school_name, password):
    """Create a user with a Werkzeug password hash, never storing plaintext."""
    try:
        with sqlite3.connect("database.db") as conn:
            conn.execute(
                """
                INSERT INTO usuarios (nome, escola, email, senha)
                VALUES (?, ?, ?, ?)
                """,
                (name, school_name, email.strip().lower(), generate_password_hash(password)),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def verify_user(email, password):
    """Verify hashed passwords and upgrade legacy plaintext rows on successful login."""
    with sqlite3.connect("database.db") as conn:
        conn.row_factory = sqlite3.Row
        user = conn.execute(
            "SELECT * FROM usuarios WHERE LOWER(email) = ?",
            (email.strip().lower(),),
        ).fetchone()

        if user is None:
            return None

        stored_password = user["senha"] or ""
        is_hash = stored_password.startswith(("pbkdf2:", "scrypt:"))
        if is_hash:
            try:
                return user if check_password_hash(stored_password, password) else None
            except (ValueError, TypeError):
                return None

        # Compatibility for legacy records: compare safely, then immediately hash.
        if not hmac.compare_digest(stored_password, password):
            return None

        conn.execute(
            "UPDATE usuarios SET senha = ? WHERE id = ?",
            (generate_password_hash(password), user["id"]),
        )
        return conn.execute(
            "SELECT * FROM usuarios WHERE id = ?",
            (user["id"],),
        ).fetchone()
