"""
Flask Surveillance System — Main Entry Point
Run: python app.py
"""
from datetime import timedelta
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from models import db, User
import config

login_manager = LoginManager()


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # ── Config ────────────────────────────────────────────────
    app.config["SECRET_KEY"]                    = config.SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"]       = config.DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]= False
    # ★ Permanent sessions — user stays logged in after browser refresh
    app.config["SESSION_PERMANENT"]             = True
    app.config["PERMANENT_SESSION_LIFETIME"]    = timedelta(hours=24)
    app.config["REMEMBER_COOKIE_DURATION"]      = timedelta(days=7)
    app.config["REMEMBER_COOKIE_SECURE"]        = False   # set True in HTTPS prod
    app.config["REMEMBER_COOKIE_HTTPONLY"]      = True

    # ── Init extensions ───────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view          = "auth.login"
    login_manager.login_message       = "Please log in."
    login_manager.login_message_category = "warning"

    # ── Blueprints ────────────────────────────────────────────
    from routes.auth      import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.camera    import camera_bp
    from routes.alerts    import alerts_bp
    from routes.detection  import detection_bp
    from routes.moderation import moderation_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(camera_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(detection_bp)
    app.register_blueprint(moderation_bp)

    @app.route("/")
    def index():
        return redirect(url_for("dashboard.index"))

    with app.app_context():
        db.create_all()
        _create_default_admin()

    return app


@login_manager.user_loader
def load_user(uid):
    return User.query.get(int(uid))


def _create_default_admin():
    if User.query.count() == 0:
        u = User(username="admin", email="admin@eyeq.com", role="admin")
        u.set_password("Admin@1234")
        db.session.add(u)
        db.session.commit()
        print("\n[INIT] Default admin created")
        print("       Username : admin")
        print("       Password : Admin@1234\n")


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=config.DEBUG)
