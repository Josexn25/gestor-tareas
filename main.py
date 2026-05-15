import json
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for


app = Flask(__name__)

# Archivo local donde se guardan las tareas de forma persistente.
DATA_FILE = Path(__file__).with_name("tasks.json")


def load_tasks():
    """Carga las tareas desde JSON y descarta datos incompletos."""
    if not DATA_FILE.exists():
        return []

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            saved_tasks = json.load(file)
    except (json.JSONDecodeError, OSError):
        return []

    return [
        {
            "text": str(task.get("text", "")).strip(),
            "completed": bool(task.get("completed", False)),
        }
        for task in saved_tasks
        if isinstance(task, dict) and str(task.get("text", "")).strip()
    ]


def save_tasks(tasks):
    """Guarda la lista actual de tareas en el archivo JSON."""
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(tasks, file, ensure_ascii=False, indent=2)


@app.get("/")
def index():
    """Muestra la interfaz principal del gestor de tareas."""
    tasks = load_tasks()
    completed_count = sum(task["completed"] for task in tasks)
    pending_count = len(tasks) - completed_count

    return render_template(
        "index.html",
        tasks=tasks,
        pending_count=pending_count,
        completed_count=completed_count,
    )


@app.post("/add")
def add_task():
    """Agrega una nueva tarea enviada desde el formulario."""
    task_text = request.form.get("task", "").strip()

    if task_text:
        tasks = load_tasks()
        tasks.append({"text": task_text, "completed": False})
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
