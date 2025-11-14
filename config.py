import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this")

    # Database
    DB_USER = os.getenv("DB_USER")
    RAW_DB_PASS = os.getenv("DB_PASSWORD", "")
    DB_PASS = quote_plus(RAW_DB_PASS)  # URL-encode special characters
    DB_NAME = os.getenv("DB_NAME")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "3306")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+mysqlconnector://{DB_USER}:{DB_PASS}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Firebase Front-end
    FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
    FIREBASE_APP_ID = os.getenv("FIREBASE_APP_ID")
    FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")
    FIREBASE_AUTH_DOMAIN = os.getenv("FIREBASE_AUTH_DOMAIN")
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
    FIREBASE_MESSAGING_SENDER_ID = os.getenv("FIREBASE_MESSAGING_SENDER_ID")
    FIREBASE_MEASUREMENT_ID = os.getenv("FIREBASE_MEASUREMENT_ID")

    # Firebase Admin SDK
    FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")

    # SMTP EMAIL
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = os.getenv("SMTP_PORT")
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")
    MAIL_FROM = os.getenv("MAIL_FROM")

    # PayPal
    PAYPAL_MODE = os.getenv("PAYPAL_MODE")
    PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
    PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")

    # Stripe
    STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

    # App
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000/")
