from datetime import date

from flask import Blueprint, g, redirect, render_template, request, url_for

from database.db import get_db
from routes.auth import login_required


tasks_bp = Blueprint("tasks", __name__)

PRIORITIES = ("Alta", "Media", "Baja")
CATEGORIES = ("Trabajo", "Estudio", "Personal", "Otras")
DEFAULT_PRIORITY = "Media"
DEFAULT_CATEGORY = "Otras"


def is_overdue(task, today):
    """Indica si una tarea pendiente ya paso su fecha limite."""
    due_date = task["due_date"] or ""
    return bool(due_date and not task["completed"] and due_date < today)


def get_user_tasks():
    """Obtiene solo las tareas del usuario autenticado."""
    rows = get_db().execute(
        """
        SELECT id, text, completed, priority, category, due_date
        FROM tasks
        WHERE user_id = ?
        ORDER BY completed ASC, due_date = '' ASC, due_date ASC, id DESC
        """,
        (g.user["id"],),
    ).fetchall()

    return [dict(row) for row in rows]


@tasks_bp.get("/")
@login_required
def index():
    """Muestra el tablero de tareas del usuario actual."""
    tasks = get_user_tasks()
    today = date.today().isoformat()

    for task in tasks:
        task["completed"] = bool(task["completed"])
        task["overdue"] = is_overdue(task, today)

    completed_count = sum(task["completed"] for task in tasks)
    pending_count = len(tasks) - completed_count
    total_count = len(tasks)
    progress = round((completed_count / total_count) * 100) if total_count else 0

    return render_template(
        "index.html",
        tasks=tasks,
        priorities=PRIORITIES,
        categories=CATEGORIES,
        pending_count=pending_count,
        completed_count=completed_count,
        total_count=total_count,
        progress=progress,
    )


@tasks_bp.post("/add")
@login_required
def add_task():
    """Agrega una tarea asociada al usuario autenticado."""
    task_text = request.form.get("task", "").strip()
    priority = request.form.get("priority", DEFAULT_PRIORITY)
    category = request.form.get("category", DEFAULT_CATEGORY)
    due_date = request.form.get("due_date", "").strip()

    if priority not in PRIORITIES:
        priority = DEFAULT_PRIORITY
    if category not in CATEGORIES:
        category = DEFAULT_CATEGORY

    if task_text:
        get_db().execute(
            """
            INSERT INTO tasks (user_id, text, completed, priority, category, due_date)
            VALUES (?, ?, 0, ?, ?, ?)
            """,
            (g.user["id"], task_text, priority, category, due_date),
        )
        get_db().commit()

    return redirect(url_for("tasks.index"))


@tasks_bp.post("/toggle/<int:task_id>")
@login_required
def toggle_task(task_id):
    """Marca una tarea propia como completada o pendiente."""
    db = get_db()
    task = db.execute(
        "SELECT completed FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, g.user["id"]),
    ).fetchone()

    if task is not None:
        db.execute(
            "UPDATE tasks SET completed = ? WHERE id = ? AND user_id = ?",
            (0 if task["completed"] else 1, task_id, g.user["id"]),
        )
        db.commit()

    return redirect(url_for("tasks.index"))


@tasks_bp.post("/delete/<int:task_id>")
@login_required
def delete_task(task_id):
    """Elimina una tarea propia."""
    db = get_db()
    db.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, g.user["id"]),
    )
    db.commit()

    return redirect(url_for("tasks.index"))
