from flask import Blueprint, render_template, session
from models import Category1Listing, SiteVisit, User
from datetime import datetime

main_bp = Blueprint("main", __name__)


@main_bp.before_app_request
def track_visit():
    from models import db
    from flask import request
    if request.endpoint != "static":
        v = SiteVisit(path=request.path)
        db.session.add(v)
        db.session.commit()


@main_bp.app_context_processor
def inject_current_user():
    user = None
    if "user_id" in session:
        user = User.query.get(session["user_id"])
    return dict(current_user=user)


@main_bp.route("/")
def index():
    listings = Category1Listing.query.filter_by(status="approved").order_by(
        Category1Listing.created_at.desc()
    ).all()
    return render_template("index.html", listings=listings)


@main_bp.route("/page/<template>")
def render_template_name(template):
    return render_template(template)
