import os

from flask import Flask

from database.db import init_app
from routes.auth import auth_bp
from routes.tasks import tasks_bp
from services.reminders import run_reminder_check
from services.scheduler import start_reminder_scheduler


def create_app():
    """Crea y configura la aplicacion Flask."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY",
        "clave-local-de-desarrollo-cambiar-en-produccion",
    )
    app.config["RESEND_API_KEY"] = os.environ.get("RESEND_API_KEY")
    app.config["APP_TIMEZONE"] = os.environ.get("APP_TIMEZONE", "America/Bogota")
    app.config["PUBLIC_BASE_URL"] = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:5000")

    init_app(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(tasks_bp)
    register_commands(app)
    start_reminder_scheduler(app)

    return app


def register_commands(app):
    """Registra comandos CLI de mantenimiento."""
    @app.cli.command("run-reminders")
    def run_reminders_command():
        """Ejecuta manualmente el envio de recordatorios."""
        sent_count = run_reminder_check()
        print(f"Recordatorios enviados: {sent_count}")


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
