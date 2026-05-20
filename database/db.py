import sqlite3
from pathlib import Path

from flask import current_app, g


DATABASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = DATABASE_DIR / "tasks.db"


def get_db():
    """Abre una conexion SQLite reutilizable durante la peticion actual."""
    if "db" not in g:
        DATABASE_DIR.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(_error=None):
    """Cierra la conexion SQLite al finalizar la peticion."""
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db():
    """Crea las tablas necesarias para usuarios y tareas."""
    db = get_db()

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            is_verified INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0,
            priority TEXT NOT NULL DEFAULT 'Media',
            category TEXT NOT NULL DEFAULT 'Otras',
            due_date TEXT DEFAULT '',
            reminder_tomorrow_sent_at TEXT DEFAULT '',
            reminder_overdue_sent_at TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )

    migrate_users_table(db)
    migrate_tasks_table(db)
    db.commit()


def column_exists(db, table, column):
    """Comprueba si una columna existe en una tabla SQLite."""
    columns = db.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in columns)


def migrate_users_table(db):
    """Agrega columnas nuevas cuando la base ya existia."""
    if not column_exists(db, "users", "email"):
        db.execute("ALTER TABLE users ADD COLUMN email TEXT")

    if not column_exists(db, "users", "is_verified"):
        db.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER NOT NULL DEFAULT 0")
        db.execute("UPDATE users SET is_verified = 1 WHERE email IS NULL OR email = ''")

    db.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email
        ON users(email)
        WHERE email IS NOT NULL AND email != ''
        """
    )


def migrate_tasks_table(db):
    """Agrega columnas de recordatorios a tareas existentes."""
    if not column_exists(db, "tasks", "reminder_tomorrow_sent_at"):
        db.execute("ALTER TABLE tasks ADD COLUMN reminder_tomorrow_sent_at TEXT DEFAULT ''")

    if not column_exists(db, "tasks", "reminder_overdue_sent_at"):
        db.execute("ALTER TABLE tasks ADD COLUMN reminder_overdue_sent_at TEXT DEFAULT ''")


def init_app(app):
    """Registra helpers de base de datos en Flask."""
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        """Inicializa la base de datos desde la terminal."""
        init_db()
        current_app.logger.info("Base de datos inicializada en %s", DATABASE_PATH)
        print(f"Base de datos inicializada en: {DATABASE_PATH}")
