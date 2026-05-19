import os

from flask import Flask

from database.db import init_app
from routes.auth import auth_bp
from routes.tasks import tasks_bp


def create_app():
    """Crea y configura la aplicacion Flask."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY",
        "clave-local-de-desarrollo-cambiar-en-produccion",
    )
    app.config["RESEND_API_KEY"] = os.environ.get("RESEND_API_KEY")
    app.config["MAIL_DEFAULT_SENDER"] = os.environ.get(
        "MAIL_DEFAULT_SENDER",
        "onboarding@resend.dev",
    )

    init_app(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(tasks_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
