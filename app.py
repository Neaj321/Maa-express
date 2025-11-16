import os
from flask import Flask
from config import Config
from models import db
import firebase_admin
from firebase_admin import credentials

from blueprints.auth import auth_bp
from blueprints.main import main_bp
from blueprints.category1 import category1_bp
from blueprints.admin import admin_bp
from blueprints.account import account_bp


def create_app():
    app = Flask(__name__)
    
    app.config.from_object(Config)

    # Initialize database
    db.init_app(app)

    # Initialize Firebase Admin SDK
    cred_path = app.config.get("FIREBASE_CREDENTIALS")
    if cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
    else:
        raise RuntimeError("Firebase Admin credential path is invalid or missing")

    firebase_admin.initialize_app(cred, {
        "projectId": app.config.get("FIREBASE_PROJECT_ID"),
        "storageBucket": app.config.get("FIREBASE_STORAGE_BUCKET"),
    })

    # Inject config into templates
    @app.context_processor
    def inject_config():
        return dict(config=app.config)

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(category1_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(account_bp)

   
    return app


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)