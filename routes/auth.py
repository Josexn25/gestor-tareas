import sqlite3
from functools import wraps

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db


auth_bp = Blueprint("auth", __name__)


def login_required(view):
    """Redirige al login si no hay usuario autenticado."""
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view


@auth_bp.before_app_request
def load_logged_in_user():
    """Carga el usuario de la sesion actual en g.user."""
    init_db()
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
        return

    g.user = get_db().execute(
        "SELECT id, username FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()


@auth_bp.get("/register")
def register():
    """Muestra el formulario de registro."""
    if g.user is not None:
        return redirect(url_for("tasks.index"))

    return render_template("register.html")


@auth_bp.post("/register")
def register_post():
    """Crea un usuario nuevo con contrasena protegida por hash."""
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    db = get_db()

    if not username or not password:
        flash("Escribe un usuario y una contrasena.", "error")
        return redirect(url_for("auth.register"))

    if len(password) < 6:
        flash("La contrasena debe tener al menos 6 caracteres.", "error")
        return redirect(url_for("auth.register"))

    try:
        cursor = db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        flash("Ese nombre de usuario ya existe.", "error")
        return redirect(url_for("auth.register"))

    session.clear()
    session["user_id"] = cursor.lastrowid
    flash("Cuenta creada correctamente.", "success")
    return redirect(url_for("tasks.index"))


@auth_bp.get("/login")
def login():
    """Muestra el formulario de inicio de sesion."""
    if g.user is not None:
        return redirect(url_for("tasks.index"))

    return render_template("login.html")


@auth_bp.post("/login")
def login_post():
    """Valida credenciales y guarda el usuario en la sesion."""
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    user = get_db().execute(
        "SELECT * FROM users WHERE username = ?",
        (username,),
    ).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        flash("Usuario o contrasena incorrectos.", "error")
        return redirect(url_for("auth.login"))

    session.clear()
    session["user_id"] = user["id"]
    return redirect(url_for("tasks.index"))


@auth_bp.post("/logout")
def logout():
    """Cierra la sesion actual."""
    session.clear()
    return redirect(url_for("auth.login"))
