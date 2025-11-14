from flask import Blueprint, render_template, session, redirect, url_for, request
from functools import wraps
from datetime import datetime, timedelta

from models import db, User, Category1Listing, SiteVisit, UserLoginLog

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("main.render_template_name", template="login.html"))
        user = User.query.get(session["user_id"])
        if not user or not user.is_admin:
            return "Admin access only", 403
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/")
@admin_required
def dashboard():
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_listings = Category1Listing.query.count()
    approved_listings = Category1Listing.query.filter_by(status="approved").count()
    sold_listings = Category1Listing.query.filter_by(status="sold").count()
    rejected_listings = Category1Listing.query.filter_by(status="rejected").count()

    total_visits = SiteVisit.query.count()
    today = datetime.utcnow().date()
    today_visits = SiteVisit.query.filter(
        SiteVisit.created_at >= datetime(today.year, today.month, today.day)
    ).count()

    days = 7
    cutoff = datetime.utcnow() - timedelta(days=days)
    logins_last_n = UserLoginLog.query.filter(
        UserLoginLog.login_at >= cutoff
    ).count()

    pending = Category1Listing.query.filter_by(status="pending_admin_review").all()
    approved = Category1Listing.query.filter_by(status="approved").all()
    rejected = Category1Listing.query.filter_by(status="rejected").all()
    sold = Category1Listing.query.filter_by(status="sold").all()

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        active_users=active_users,
        total_listings=total_listings,
        approved_listings=approved_listings,
        sold_listings=sold_listings,
        rejected_listings=rejected_listings,
        total_visits=total_visits,
        today_visits=today_visits,
        logins_last_n=logins_last_n,
        pending=pending,
        approved=approved,
        rejected=rejected,
        sold=sold,
        login_days=days
    )


@admin_bp.route("/users")
@admin_required
def users():
    days = 7
    cutoff = datetime.utcnow() - timedelta(days=days)
    users = User.query.order_by(User.created_at.desc()).all()
    user_stats = []
    for u in users:
        login_count = UserLoginLog.query.filter(
            UserLoginLog.user_id == u.id,
            UserLoginLog.login_at >= cutoff
        ).count()
        user_stats.append((u, login_count))
    return render_template("admin_users.html", user_stats=user_stats, login_days=days)


@admin_bp.post("/category1/<listing_uid>/update-status")
@admin_required
def update_category1_status(listing_uid):
    listing = Category1Listing.query.filter_by(listing_uid=listing_uid).first_or_404()
    new_status = request.form.get("status")
    if new_status not in ["approved", "rejected"]:
        return "Invalid status", 400
    listing.status = new_status
    db.session.commit()
    return redirect(url_for("admin.dashboard"))
