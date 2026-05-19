import os

from flask import Flask

from database.db import init_app
from extensions import mail
from routes.auth import auth_bp
from routes.tasks import tasks_bp


def create_app():
    """Crea y configura la aplicacion Flask."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY",
        "clave-local-de-desarrollo-cambiar-en-produccion",
    )
    app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", "587"))
    app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    app.config["MAIL_USE_SSL"] = os.environ.get("MAIL_USE_SSL", "false").lower() == "true"
    app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
    app.config["MAIL_DEFAULT_SENDER"] = os.environ.get(
        "MAIL_DEFAULT_SENDER",
        os.environ.get("MAIL_USERNAME"),
    )

    mail.init_app(app)
    init_app(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(tasks_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
