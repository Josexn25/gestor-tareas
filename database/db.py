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
            password_hash TEXT NOT NULL,
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )

    db.commit()


def init_app(app):
    """Registra helpers de base de datos en Flask."""
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        """Inicializa la base de datos desde la terminal."""
        init_db()
        current_app.logger.info("Base de datos inicializada en %s", DATABASE_PATH)
        print(f"Base de datos inicializada en: {DATABASE_PATH}")
