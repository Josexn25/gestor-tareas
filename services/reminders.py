from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import current_app

from database.db import get_db, init_db
from services.email_service import build_email_html, send_email


def get_today():
    """Devuelve la fecha local segun la zona horaria configurada."""
    timezone_name = current_app.config.get("APP_TIMEZONE", "America/Bogota")
    return datetime.now(ZoneInfo(timezone_name)).date()


def timestamp_now():
    """Devuelve timestamp local ISO para marcar recordatorios enviados."""
    timezone_name = current_app.config.get("APP_TIMEZONE", "America/Bogota")
    return datetime.now(ZoneInfo(timezone_name)).isoformat(timespec="seconds")


def reminder_query(db, due_date, reminder_column, overdue=False):
    """Obtiene tareas pendientes que aun no recibieron el recordatorio indicado."""
    operator = "<" if overdue else "="
    return db.execute(
        f"""
        SELECT
            tasks.id,
            tasks.text,
            tasks.priority,
            tasks.category,
            tasks.due_date,
            users.username,
            users.email
        FROM tasks
        JOIN users ON users.id = tasks.user_id
        WHERE tasks.completed = 0
          AND tasks.due_date != ''
          AND tasks.due_date {operator} ?
          AND (tasks.{reminder_column} IS NULL OR tasks.{reminder_column} = '')
          AND users.is_verified = 1
          AND users.email IS NOT NULL
          AND users.email != ''
        """,
        (due_date,),
    ).fetchall()


def build_task_reminder(task, kind):
    """Construye asunto, texto y HTML para un recordatorio de tarea."""
    dashboard_url = current_app.config.get("PUBLIC_BASE_URL", "http://127.0.0.1:5000").rstrip("/") + "/"
    is_overdue = kind == "overdue"
    title = "Tarea vencida" if is_overdue else "Tu tarea vence manana"
    subject = f"{title}: {task['text']}"
    status_line = "ya vencio" if is_overdue else "vence manana"
    intro = (
        f"Hola {task['username']}, la tarea \"{task['text']}\" {status_line}. "
        f"Prioridad: {task['priority']}. Categoria: {task['category']}. "
        f"Fecha limite: {task['due_date']}."
    )
    text_body = (
        f"{intro}\n\n"
        f"Abre tu tablero para revisarla:\n{dashboard_url}"
    )
    html_body = build_email_html(
        title,
        intro,
        dashboard_url,
        "Abrir tareas",
        "Este recordatorio se envia una sola vez para evitar duplicados.",
    )
    return subject, text_body, html_body


def send_task_reminder(db, task, kind, reminder_column):
    """Envia un recordatorio y marca la tarea si el envio fue exitoso."""
    subject, text_body, html_body = build_task_reminder(task, kind)
    sent = send_email(task["email"], subject, text_body, html_body)

    if sent:
        db.execute(
            f"UPDATE tasks SET {reminder_column} = ? WHERE id = ?",
            (timestamp_now(), task["id"]),
        )
        db.commit()

    return sent


def run_reminder_check():
    """Ejecuta el chequeo de tareas por vencer y vencidas."""
    init_db()
    db = get_db()
    today = get_today()
    tomorrow = today + timedelta(days=1)

    tomorrow_tasks = reminder_query(
        db,
        tomorrow.isoformat(),
        "reminder_tomorrow_sent_at",
        overdue=False,
    )
    overdue_tasks = reminder_query(
        db,
        today.isoformat(),
        "reminder_overdue_sent_at",
        overdue=True,
    )

    sent_count = 0

    for task in tomorrow_tasks:
        sent_count += int(send_task_reminder(db, task, "tomorrow", "reminder_tomorrow_sent_at"))

    for task in overdue_tasks:
        sent_count += int(send_task_reminder(db, task, "overdue", "reminder_overdue_sent_at"))

    current_app.logger.info("Chequeo de recordatorios completado. Enviados: %s", sent_count)
    return sent_count
