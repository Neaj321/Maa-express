import os
from flask import Flask
from config import Config, validate_config
from models import db
import firebase_admin
from firebase_admin import credentials

from blueprints.auth import auth_bp
from blueprints.main import main_bp
from blueprints.category1 import category1_bp
from blueprints.admin import admin_bp
from blueprints.account import account_bp


def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # ✅ Validate configuration before starting
    try:
        validate_config()
    except (ValueError, FileNotFoundError) as e:
        print(f"❌ Configuration Error: {e}")
        print("\nPlease check your .env file and ensure all required variables are set.")
        print("See .env.example for reference.")
        raise
    
    # Initialize database
    db.init_app(app)
    
    # Initialize Firebase Admin SDK (server-side)
    try:
        cred = credentials.Certificate(app.config['FIREBASE_CREDENTIALS'])
        firebase_admin.initialize_app(cred, {
            'storageBucket': app.config['FIREBASE_STORAGE_BUCKET']
        })
        print("✅ Firebase Admin SDK initialized")
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
        raise
    
    # Register blueprints
    # ✅ Keep /auth prefix for login/register pages
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(category1_bp, url_prefix='/category1')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(account_bp, url_prefix='/account')
    
    # ✅ Register API routes at root level (for frontend compatibility)
    from blueprints.auth import api_login, api_register, api_logout
    
    @app.route('/api/login', methods=['POST'])
    def root_api_login():
        """Proxy to auth blueprint's api_login"""
        return api_login()
    
    @app.route('/api/register', methods=['POST'])
    def root_api_register():
        """Proxy to auth blueprint's api_register"""
        return api_register()
    
    @app.route('/api/logout', methods=['POST'])
    def root_api_logout():
        """Proxy to auth blueprint's api_logout"""
        return api_logout()
    
    # Make config available to templates
    @app.context_processor
    def inject_config():
        return dict(
            config=app.config,
            # Expose only frontend-safe Firebase config
            firebase_config={
                'apiKey': app.config['FIREBASE_API_KEY'],
                'authDomain': app.config['FIREBASE_AUTH_DOMAIN'],
                'projectId': app.config['FIREBASE_PROJECT_ID'],
                'storageBucket': app.config['FIREBASE_STORAGE_BUCKET'],
                'messagingSenderId': app.config['FIREBASE_MESSAGING_SENDER_ID'],
                'appId': app.config['FIREBASE_APP_ID']
            }
        )
    
    print(f"✅ Flask app created successfully")
    print(f"   Database: {app.config['DB_NAME']}@{app.config['DB_HOST']}")
    print(f"   Firebase Project: {app.config['FIREBASE_PROJECT_ID']}")
    print(f"   Debug Mode: {app.config['DEBUG']}")
    
    return app


if __name__ == "__main__":
    app = create_app()
    
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables created/verified")
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            raise
    
    print("\n" + "="*60)
    print("🚀 MAA EXPRESS - STARTING SERVER")
    print("="*60)
    print(f"   URL: http://127.0.0.1:5000")
    print(f"   Environment: {'Development' if app.config['DEBUG'] else 'Production'}")
    print("="*60 + "\n")
    
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )