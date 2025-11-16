from flask import Blueprint, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, UserLoginLog
from functools import wraps
import phonenumbers


def normalize_phone_e164(phone_str, default_region="AU"):
    """
    Normalize phone number to E.164 format.
    Assumes default region is AU if no country code prefix.
    Returns normalized phone string or None if invalid.
    """
    try:
        # Try to parse the phone number
        parsed = phonenumbers.parse(phone_str, default_region)
        # Validate the number
        if not phonenumbers.is_valid_number(parsed):
            return None
        # Return E.164 format
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.phonenumberutil.NumberParseException:
        return None


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
    """Redirect to register template"""
    return redirect(url_for("main.render_template_name", template="register.html"))


@auth_bp.route("/login")
def login_page():
    """Redirect to login template"""
    return redirect(url_for("main.render_template_name", template="login.html"))


@auth_bp.post("/api/register")
def api_register():
    """
    Register a new user account.
    Expects JSON with: full_name, email, phone (with country code), password
    """
    data = request.get_json()
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip().lower()
    phone = data.get("phone", "").strip()
    password = data.get("password", "")

    # Validate required fields
    if not all([full_name, email, phone, password]):
        return jsonify({"error": "Missing required fields"}), 400

    # Validate email format
    if "@" not in email or "." not in email:
        return jsonify({"error": "Invalid email format"}), 400

    # Validate password strength
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    # Normalize phone to E.164 format
    normalized_phone = normalize_phone_e164(phone)
    if not normalized_phone:
        return jsonify({"error": "Invalid phone number format. Use format: +61412345678"}), 400

    # Check for duplicate email
    existing_email = User.query.filter_by(email=email).first()
    if existing_email:
        return jsonify({"error": "Email already registered"}), 400

    # Check for duplicate phone
    existing_phone = User.query.filter_by(phone=normalized_phone).first()
    if existing_phone:
        return jsonify({"error": "Phone number already registered"}), 400

    # Create new user
    try:
        user = User(
            full_name=full_name,
            email=email,
            phone=normalized_phone,
            password_hash=generate_password_hash(password),
            is_admin=False,
            is_active=True,
            email_verified=True,  # Set to True after email/SMS verification in production
            phone_verified=True   # Set to True after SMS verification in production
        )
        db.session.add(user)
        db.session.commit()

        # Auto-login after registration
        session["user_id"] = user.id

        # Log the registration as a login event
        log = UserLoginLog(
            user_id=user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent")
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({
            "message": "Registration successful",
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500


@auth_bp.post("/api/login")
def api_login():
    """
    Login with email/phone and password.
    Accepts either email or phone as identifier.
    """
    data = request.get_json()
    identifier = data.get("identifier", "").strip()
    password = data.get("password", "")

    if not identifier or not password:
        return jsonify({"error": "Missing identifier or password"}), 400

    # Determine if identifier is email or phone
    user = None
    if "@" in identifier:
        # Treat as email
        user = User.query.filter_by(email=identifier.lower()).first()
    else:
        # Treat as phone; normalize to E.164 first
        normalized_phone = normalize_phone_e164(identifier)
        if normalized_phone:
            user = User.query.filter_by(phone=normalized_phone).first()

    # Verify credentials
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid credentials"}), 401

    # Check if account is active
    if not user.is_active:
        return jsonify({"error": "Account is inactive. Contact support."}), 403

    # Set session
    session["user_id"] = user.id

    # Log the login
    log = UserLoginLog(
        user_id=user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent")
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "is_admin": user.is_admin
        }
    }), 200


@auth_bp.post("/api/logout")
def api_logout():
    """Logout current user by clearing session"""
    session.pop("user_id", None)
    return jsonify({"message": "Logged out successfully"}), 200


@auth_bp.route("/verify-email")
def verify_email():
    """
    Email verification callback endpoint.
    In production, you would verify the token and update user.email_verified = True
    """
    email = request.args.get("email")
    if not email:
        return "Invalid verification link", 400
    
    user = User.query.filter_by(email=email).first()
    if user:
        user.email_verified = True
        db.session.commit()
        return redirect(url_for("main.render_template_name", template="login.html"))
    
    return "User not found", 404


@auth_bp.post("/api/verify-phone")
def api_verify_phone():
    """
    Phone verification endpoint (called after Firebase SMS OTP verification).
    Frontend verifies OTP with Firebase, then calls this to update backend.
    """
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user = User.query.get(session["user_id"])
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    user.phone_verified = True
    db.session.commit()
    
    return jsonify({"message": "Phone verified successfully"}), 200


@auth_bp.route("/api/check-session")
def check_session():
    """Check if user is logged in"""
    if "user_id" in session:
        user = User.query.get(session["user_id"])
        if user:
            return jsonify({
                "logged_in": True,
                "user": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "is_admin": user.is_admin
                }
            }), 200
    
    return jsonify({"logged_in": False}), 200