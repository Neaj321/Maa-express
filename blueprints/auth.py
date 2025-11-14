from flask import Blueprint, request, jsonify, session, redirect, url_for
from firebase_admin import auth as firebase_auth
from models import db, User
from functools import wraps

auth_bp = Blueprint("auth", __name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("main.render_template_name", template="login.html"))
        return f(*args, **kwargs)
    return decorated


@auth_bp.route("/register")
def register_page():
    return redirect(url_for("main.render_template_name", template="register.html"))


@auth_bp.route("/login")
def login_page():
    return redirect(url_for("main.render_template_name", template="login.html"))


@auth_bp.post("/api/register")
def api_register():
    data = request.get_json()
    id_token = data.get("idToken")
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    phone_country_code = data.get("phone_country_code")
    phone_number = data.get("phone_number")
    phone_verified = data.get("phone_verified", False)

    if not id_token:
        return jsonify({"error": "Missing idToken"}), 400

    try:
        decoded = firebase_auth.verify_id_token(id_token)
    except Exception as e:
        return jsonify({"error": "Invalid ID token", "details": str(e)}), 401

    firebase_uid = decoded["uid"]
    email = decoded.get("email")
    if not email:
        return jsonify({"error": "Email missing from Firebase token"}), 400

    existing = User.query.filter_by(firebase_uid=firebase_uid).first()
    if existing:
        return jsonify({"error": "User already registered"}), 400

    user = User(
        firebase_uid=firebase_uid,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone_country_code=phone_country_code,
        phone_number=phone_number,
        is_phone_verified=bool(phone_verified),
        is_active=bool(phone_verified),
    )
    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id
    return jsonify({"message": "Registered successfully"}), 201


@auth_bp.post("/api/login")
def api_login():
    data = request.get_json()
    id_token = data.get("idToken")
    if not id_token:
        return jsonify({"error": "Missing idToken"}), 400

    try:
        decoded = firebase_auth.verify_id_token(id_token)
    except Exception as e:
        return jsonify({"error": "Invalid ID token", "details": str(e)}), 401

    firebase_uid = decoded["uid"]
    user = User.query.filter_by(firebase_uid=firebase_uid).first()
    if not user:
        return jsonify({"error": "User not found in Maa Express DB"}), 404
    if not user.is_active:
        return jsonify({"error": "Account inactive"}), 403

    from models import UserLoginLog
    session["user_id"] = user.id
    log = UserLoginLog(user_id=user.id)
    db.session.add(log)
    db.session.commit()

    return jsonify({"message": "Logged in"}), 200


@auth_bp.post("/api/logout")
def api_logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200
