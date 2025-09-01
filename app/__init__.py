import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
bcrypt = Bcrypt()


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=False)

    from .config import Config

    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    # Ensure uploads directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # CLI
    from .cli import register_cli
    register_cli(app)

    from .auth.routes import auth_bp
    from .requirements.routes import requirements_bp
    from .admin.routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(requirements_bp)
    app.register_blueprint(admin_bp)

    @app.shell_context_processor
    def make_shell_context():
        from . import models

        return {
            "db": db,
            "models": models,
        }

    return app


