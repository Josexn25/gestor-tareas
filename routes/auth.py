import sqlite3
from functools import wraps

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db
from services.email_service import build_email_html, send_email


auth_bp = Blueprint("auth", __name__)

VERIFY_TOKEN_MAX_AGE = 60 * 60 * 24
RESET_TOKEN_MAX_AGE = 60 * 60


def login_required(view):
    """Redirige al login si no hay usuario autenticado."""
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))

        return view(**kwargs)

    return wrapped_view


def get_serializer():
    """Crea un serializador firmado con SECRET_KEY."""
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generate_token(email, purpose):
    """Genera un token firmado para verificacion o recuperacion."""
    return get_serializer().dumps({"email": email, "purpose": purpose})


def load_token(token, purpose, max_age):
    """Lee un token firmado y valida su proposito y expiracion."""
    try:
        data = get_serializer().loads(token, max_age=max_age)
    except SignatureExpired:
        return None, "expired"
    except BadSignature:
        return None, "invalid"

    if data.get("purpose") != purpose:
        return None, "invalid"

    return data.get("email"), None


def send_verification_email(user):
    """Envia el enlace de verificacion de correo."""
    token = generate_token(user["email"], "verify-email")
    link = url_for("auth.verify_email", token=token, _external=True)
    text_body = (
        f"Hola {user['username']},\n\n"
        "Confirma tu correo para activar tu cuenta del gestor de tareas:\n"
        f"{link}\n\n"
        "Este enlace vence en 24 horas."
    )
    html_body = build_email_html(
        "Confirma tu correo",
        f"Hola {user['username']}, confirma tu correo para activar tu cuenta y comenzar a usar tus tareas privadas.",
        link,
        "Verificar correo",
        "Este enlace vence en 24 horas. Si no creaste esta cuenta, puedes ignorar este mensaje.",
    )
    return send_email(user["email"], "Confirma tu correo", text_body, html_body)


def send_password_reset_email(user):
    """Envia el enlace seguro para restablecer contrasena."""
    current_app.logger.info("Generando token de recuperacion para user_id=%s email=%s", user["id"], user["email"])
    token = generate_token(user["email"], "reset-password")
    link = url_for("auth.reset_password", token=token, _external=True)
    text_body = (
        f"Hola {user['username']},\n\n"
        "Usa este enlace para cambiar tu contrasena:\n"
        f"{link}\n\n"
        "Este enlace vence en 1 hora. Si no lo solicitaste, ignora este correo."
    )
    html_body = build_email_html(
        "Recuperar contrasena",
        f"Hola {user['username']}, recibimos una solicitud para cambiar la contrasena de tu cuenta.",
        link,
        "Cambiar contrasena",
        "Este enlace vence en 1 hora. Si no solicitaste este cambio, ignora este correo.",
    )
    sent = send_email(user["email"], "Recuperar contrasena", text_body, html_body)
    current_app.logger.info(
        "Resultado envio recuperacion user_id=%s email=%s sent=%s",
        user["id"],
        user["email"],
        sent,
    )
    return sent


@auth_bp.before_app_request
def load_logged_in_user():
    """Carga el usuario de la sesion actual en g.user."""
    init_db()
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
        return

    g.user = get_db().execute(
        "SELECT id, username, email, is_verified FROM users WHERE id = ?",
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
    """Crea un usuario nuevo y envia verificacion por correo."""
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    db = get_db()

    if not username or not email or not password:
        flash("Escribe usuario, correo y contrasena.", "error")
        return redirect(url_for("auth.register"))

    if len(password) < 6:
        flash("La contrasena debe tener al menos 6 caracteres.", "error")
        return redirect(url_for("auth.register"))

    try:
        db.execute(
            """
            INSERT INTO users (username, email, password_hash, is_verified)
            VALUES (?, ?, ?, 0)
            """,
            (username, email, generate_password_hash(password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        flash("Ese usuario o correo ya esta registrado.", "error")
        return redirect(url_for("auth.register"))

    user = db.execute(
        "SELECT id, username, email FROM users WHERE email = ?",
        (email,),
    ).fetchone()

    sent = send_verification_email(user)
    if sent:
        flash("Cuenta creada. Revisa tu correo para verificarla.", "success")
    else:
        flash("Cuenta creada, pero falta configurar Resend para enviar el correo.", "error")

    return redirect(url_for("auth.login"))


@auth_bp.get("/verify-email/<token>")
def verify_email(token):
    """Verifica la cuenta desde un enlace firmado."""
    email, error = load_token(token, "verify-email", VERIFY_TOKEN_MAX_AGE)

    if error == "expired":
        flash("El enlace de verificacion expiro. Solicita uno nuevo.", "error")
        return redirect(url_for("auth.resend_verification"))
    if error:
        flash("El enlace de verificacion no es valido.", "error")
        return redirect(url_for("auth.login"))

    db = get_db()
    user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if user is None:
        flash("No existe una cuenta para ese correo.", "error")
        return redirect(url_for("auth.register"))

    db.execute("UPDATE users SET is_verified = 1 WHERE email = ?", (email,))
    db.commit()
    flash("Correo verificado. Ya puedes iniciar sesion.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.get("/resend-verification")
def resend_verification():
    """Muestra formulario para reenviar verificacion."""
    return render_template("resend_verification.html")


@auth_bp.post("/resend-verification")
def resend_verification_post():
    """Reenvia el correo de verificacion si el usuario existe."""
    email = request.form.get("email", "").strip().lower()
    user = get_db().execute(
        "SELECT id, username, email, is_verified FROM users WHERE email = ?",
        (email,),
    ).fetchone()

    if user and not user["is_verified"]:
        send_verification_email(user)

    flash("Si el correo existe y no esta verificado, enviaremos un nuevo enlace.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.get("/login")
def login():
    """Muestra el formulario de inicio de sesion."""
    if g.user is not None:
        return redirect(url_for("tasks.index"))

    return render_template("login.html")


@auth_bp.post("/login")
def login_post():
    """Valida credenciales, verificacion y guarda la sesion."""
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    user = get_db().execute(
        "SELECT * FROM users WHERE username = ?",
        (username,),
    ).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        flash("Usuario o contrasena incorrectos.", "error")
        return redirect(url_for("auth.login"))

    if not user["is_verified"]:
        flash("Debes verificar tu correo antes de iniciar sesion.", "error")
        return redirect(url_for("auth.login"))

    session.clear()
    session["user_id"] = user["id"]
    return redirect(url_for("tasks.index"))


@auth_bp.get("/forgot-password")
def forgot_password():
    """Muestra formulario para solicitar recuperacion."""
    return render_template("forgot_password.html")


@auth_bp.post("/forgot-password")
def forgot_password_post():
    """Envia un enlace de recuperacion si el correo existe."""
    email = request.form.get("email", "").strip().lower()
    current_app.logger.info("Solicitud forgot-password recibida para email=%s", email)
    user = get_db().execute(
        "SELECT id, username, email FROM users WHERE LOWER(email) = ?",
        (email,),
    ).fetchone()

    if user:
        current_app.logger.info("Usuario encontrado para recuperacion user_id=%s email=%s", user["id"], user["email"])
        sent = send_password_reset_email(user)
        if not sent:
            current_app.logger.warning("No se pudo enviar recuperacion para user_id=%s email=%s", user["id"], user["email"])
    else:
        current_app.logger.info("No existe usuario para recuperacion email=%s", email)

    flash("Si el correo existe, enviaremos un enlace para cambiar la contrasena.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.get("/reset-password/<token>")
def reset_password(token):
    """Muestra formulario para cambiar contrasena desde token."""
    email, error = load_token(token, "reset-password", RESET_TOKEN_MAX_AGE)

    if error == "expired":
        flash("El enlace de recuperacion expiro. Solicita uno nuevo.", "error")
        return redirect(url_for("auth.forgot_password"))
    if error:
        flash("El enlace de recuperacion no es valido.", "error")
        return redirect(url_for("auth.forgot_password"))

    return render_template("reset_password.html", token=token, email=email)


@auth_bp.post("/reset-password/<token>")
def reset_password_post(token):
    """Actualiza la contrasena usando un token valido."""
    email, error = load_token(token, "reset-password", RESET_TOKEN_MAX_AGE)
    password = request.form.get("password", "")

    if error:
        flash("El enlace no es valido o ya expiro.", "error")
        return redirect(url_for("auth.forgot_password"))

    if len(password) < 6:
        flash("La contrasena debe tener al menos 6 caracteres.", "error")
        return redirect(url_for("auth.reset_password", token=token))

    db = get_db()
    db.execute(
        "UPDATE users SET password_hash = ? WHERE email = ?",
        (generate_password_hash(password), email),
    )
    db.commit()
    flash("Contrasena actualizada. Ya puedes iniciar sesion.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.post("/logout")
def logout():
    """Cierra la sesion actual."""
    session.clear()
    return redirect(url_for("auth.login"))
