import json
from datetime import date
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for


app = Flask(__name__)

# Archivo local donde se guardan las tareas de forma persistente.
DATA_FILE = Path(__file__).with_name("tasks.json")

PRIORITIES = ("Alta", "Media", "Baja")
CATEGORIES = ("Trabajo", "Estudio", "Personal", "Otras")
DEFAULT_PRIORITY = "Media"
DEFAULT_CATEGORY = "Otras"


def normalize_task(task):
    """Convierte tareas antiguas de tasks.json al formato actual."""
    text = str(task.get("text", "")).strip()
    if not text:
        return None

    priority = task.get("priority", DEFAULT_PRIORITY)
    category = task.get("category", DEFAULT_CATEGORY)
    due_date = str(task.get("due_date", "")).strip()

    if priority not in PRIORITIES:
        priority = DEFAULT_PRIORITY
    if category not in CATEGORIES:
        category = DEFAULT_CATEGORY

    return {
        "text": text,
        "completed": bool(task.get("completed", False)),
        "priority": priority,
        "category": category,
        "due_date": due_date,
    }


def load_tasks():
    """Carga las tareas desde JSON y conserva compatibilidad con versiones previas."""
    if not DATA_FILE.exists():
        return []

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            saved_tasks = json.load(file)
    except (json.JSONDecodeError, OSError):
        return []

    if not isinstance(saved_tasks, list):
        return []

    tasks = []
    for task in saved_tasks:
        if isinstance(task, dict):
            normalized = normalize_task(task)
            if normalized:
                tasks.append(normalized)

    return tasks


def save_tasks(tasks):
    """Guarda la lista actual de tareas en el archivo JSON."""
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(tasks, file, ensure_ascii=False, indent=2)


def is_overdue(task, today):
    """Indica si una tarea pendiente ya paso su fecha limite."""
    due_date = task.get("due_date", "")
    return bool(due_date and not task["completed"] and due_date < today)


@app.get("/")
def index():
    """Muestra la interfaz principal del gestor de tareas."""
    tasks = load_tasks()
    today = date.today().isoformat()

    for task in tasks:
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
        today=today,
        pending_count=pending_count,
        completed_count=completed_count,
        total_count=total_count,
        progress=progress,
    )


@app.post("/add")
def add_task():
    """Agrega una nueva tarea con prioridad, categoria y fecha limite."""
    task_text = request.form.get("task", "").strip()
    priority = request.form.get("priority", DEFAULT_PRIORITY)
    category = request.form.get("category", DEFAULT_CATEGORY)
    due_date = request.form.get("due_date", "").strip()

    if priority not in PRIORITIES:
        priority = DEFAULT_PRIORITY
    if category not in CATEGORIES:
        category = DEFAULT_CATEGORY

    if task_text:
        tasks = load_tasks()
        tasks.append(
            {
                "text": task_text,
                "completed": False,
                "priority": priority,
                "category": category,
                "due_date": due_date,
            }
        )
        save_tasks(tasks)

    return redirect(url_for("index"))


@app.post("/toggle/<int:task_id>")
def toggle_task(task_id):
    """Marca una tarea como completada o pendiente."""
    tasks = load_tasks()

    if 0 <= task_id < len(tasks):
        tasks[task_id]["completed"] = not tasks[task_id]["completed"]
        save_tasks(tasks)

    return redirect(url_for("index"))


@app.post("/delete/<int:task_id>")
def delete_task(task_id):
    """Elimina una tarea por su posicion en la lista."""
    tasks = load_tasks()

    if 0 <= task_id < len(tasks):
        del tasks[task_id]
        save_tasks(tasks)

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
