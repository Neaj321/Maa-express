import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load environment variables from .env file
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    """Application configuration"""
    
    # ============================================
    # FLASK CORE
    # ============================================
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = os.environ.get("FLASK_DEBUG", "True") == "True"
    
    # ============================================
    # DATABASE (MySQL)
    # ============================================
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_NAME = os.environ.get("DB_NAME", "maa_express")
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    
    # URL-encode password to handle special characters
    encoded_password = quote_plus(DB_PASSWORD)
    
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector://{DB_USER}:{encoded_password}@{DB_HOST}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set to True for SQL debugging
    
    # ============================================
    # FIREBASE ADMIN SDK (Server-side)
    # ============================================
    FIREBASE_CREDENTIALS = os.environ.get(
        "FIREBASE_CREDENTIALS",
        os.path.join(BASE_DIR, "serviceAccountKey.json")
    )
    FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "")
    FIREBASE_STORAGE_BUCKET = os.environ.get("FIREBASE_STORAGE_BUCKET", "")
    
    # ============================================
    # ✅ NEW: FIREBASE CLIENT SDK (Frontend JavaScript)
    # ============================================
    # These are safe to expose in templates (public API keys)
    FIREBASE_API_KEY = os.environ.get("FIREBASE_API_KEY", "")
    FIREBASE_AUTH_DOMAIN = os.environ.get("FIREBASE_AUTH_DOMAIN", "")
    FIREBASE_MESSAGING_SENDER_ID = os.environ.get("FIREBASE_MESSAGING_SENDER_ID", "")
    FIREBASE_APP_ID = os.environ.get("FIREBASE_APP_ID", "")
    
    # ============================================
    # EMAIL (Flask-Mail)
    # ============================================
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True") == "True"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@maaexpress.com")
    
    # ============================================
    # PAYMENT GATEWAYS
    # ============================================
    
    # Stripe
    STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "")
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    
    # PayPal
    PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
    PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
    PAYPAL_MODE = os.environ.get("PAYPAL_MODE", "sandbox")  # 'sandbox' or 'live'
    
    # ============================================
    # FILE UPLOADS
    # ============================================
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max file size
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}
    
    # ============================================
    # SESSION & SECURITY
    # ============================================
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False") == "True"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours in seconds
    
    # ============================================
    # RECAPTCHA (Optional - for bot protection)
    # ============================================
    RECAPTCHA_SITE_KEY = os.environ.get("RECAPTCHA_SITE_KEY", "")
    RECAPTCHA_SECRET_KEY = os.environ.get("RECAPTCHA_SECRET_KEY", "")
    
    # ============================================
    # ADMIN SETTINGS
    # ============================================
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@maaexpress.com")
    
    # ============================================
    # APPLICATION SETTINGS
    # ============================================
    SITE_NAME = "Maa Express"
    SITE_URL = os.environ.get("SITE_URL", "http://localhost:5000")
    
    # Verification code settings
    HANDOVER_CODE_LENGTH = 6
    DELIVERY_CODE_LENGTH = 6
    MAX_VERIFICATION_ATTEMPTS = 5
    
    # Commission rates (if applicable)
    PLATFORM_COMMISSION_PERCENT = float(os.environ.get("PLATFORM_COMMISSION_PERCENT", "5.0"))
    
    @staticmethod
    def init_app(app):
        """Initialize application with this config"""
        pass


class DevelopmentConfig(Config):
    """Development-specific configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True  # Show SQL queries in console


class ProductionConfig(Config):
    """Production-specific configuration"""
    DEBUG = False
    SQLALCHEMY_ECHO = False
    SESSION_COOKIE_SECURE = True  # Force HTTPS cookies


class TestingConfig(Config):
    """Testing-specific configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"  # In-memory SQLite for tests
    WTF_CSRF_ENABLED = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}