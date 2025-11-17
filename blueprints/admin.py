"""
Admin blueprint for Maa Express
Handles admin dashboard, manual payment verification, user management, and listing approvals
"""

from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify, flash
from functools import wraps
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import func, desc

from models import (
    db, User, Category1Listing, Category2Listing, Category3Product,
    SiteVisit, UserLoginLog, Category1BuyerInfo
)

from utils.payment_utils import generate_handover_code, generate_delivery_code

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ============================================
# ADMIN AUTHENTICATION DECORATOR
# ============================================

def admin_required(f):
    """Require admin authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to access admin panel", "error")
            return redirect(url_for("auth.login_page"))
        
        user = User.query.get(session["user_id"])
        if not user or not user.is_admin:
            flash("Admin access required", "error")
            return redirect(url_for("main.index"))
        
        return f(*args, **kwargs)
    return decorated


# ============================================
# ADMIN DASHBOARD
# ============================================

@admin_bp.route("/")
@admin_required
def dashboard():
    """Admin dashboard with pending manual payments"""
    # User statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    admin_users = User.query.filter_by(is_admin=True).count()

    # Category 1 statistics
    cat1_total = Category1Listing.query.count()
    cat1_pending = Category1Listing.query.filter_by(admin_status="pending").count()
    cat1_approved = Category1Listing.query.filter_by(admin_status="approved").count()
    cat1_rejected = Category1Listing.query.filter_by(admin_status="rejected").count()

    # Category 2 statistics
    cat2_total = Category2Listing.query.count()
    cat2_pending = Category2Listing.query.filter_by(admin_status="pending").count()
    cat2_approved = Category2Listing.query.filter_by(admin_status="approved").count()
    cat2_rejected = Category2Listing.query.filter_by(admin_status="rejected").count()

    # Category 3 statistics
    cat3_total = Category3Product.query.count()
    cat3_pending = Category3Product.query.filter_by(admin_status="pending").count()
    cat3_approved = Category3Product.query.filter_by(admin_status="approved").count()
    cat3_rejected = Category3Product.query.filter_by(admin_status="rejected").count()
    
    # ✅ PENDING MANUAL PAYMENTS COUNT
    pending_manual_payments = Category1BuyerInfo.query.filter_by(
        payment_status="manual_pay"
    ).count()

    # Site visit statistics
    total_visits = SiteVisit.query.count()
    today = datetime.utcnow().date()
    today_visits = SiteVisit.query.filter(
        SiteVisit.visited_at >= datetime(today.year, today.month, today.day)
    ).count()

    # Login statistics
    days = 7
    cutoff = datetime.utcnow() - timedelta(days=days)
    logins_last_n = UserLoginLog.query.filter(UserLoginLog.login_time >= cutoff).count()

    # Top pages
    top_pages = db.session.query(
        SiteVisit.page_url,
        func.count(SiteVisit.id).label('visit_count')
    ).group_by(SiteVisit.page_url).order_by(desc('visit_count')).limit(10).all()

    # Recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

    # Pending items for quick access
    pending_cat1 = Category1Listing.query.filter_by(admin_status="pending").limit(20).all()
    pending_cat2 = Category2Listing.query.filter_by(admin_status="pending").limit(20).all()
    pending_cat3 = Category3Product.query.filter_by(admin_status="pending").limit(20).all()

    return render_template(
        "dashboard.html",
        total_users=total_users,
        active_users=active_users,
        admin_users=admin_users,
        cat1_total=cat1_total, 
        cat1_pending=cat1_pending, 
        cat1_approved=cat1_approved, 
        cat1_rejected=cat1_rejected,
        cat2_total=cat2_total, 
        cat2_pending=cat2_pending, 
        cat2_approved=cat2_approved, 
        cat2_rejected=cat2_rejected,
        cat3_total=cat3_total, 
        cat3_pending=cat3_pending, 
        cat3_approved=cat3_approved, 
        cat3_rejected=cat3_rejected,
        pending_manual_payments=pending_manual_payments,
        recent_users=recent_users,
        pending_cat1=pending_cat1,
        pending_cat2=pending_cat2,
        pending_cat3=pending_cat3,
        total_visits=total_visits,
        today_visits=today_visits,
        logins_last_n=logins_last_n,
        top_pages=top_pages,
        login_days=days
    )


# ============================================
# MANUAL PAYMENT VERIFICATION
# ============================================

@admin_bp.route("/pending-payments")
@admin_required
def pending_payments():
    """Show all pending manual payments"""
    pending = Category1BuyerInfo.query.filter_by(
        payment_status="manual_pay"
    ).order_by(Category1BuyerInfo.created_at.desc()).all()
    
    return render_template(
        "admin/pending_payments.html",
        pending_payments=pending
    )


@admin_bp.route("/verify-payment/<int:buyer_info_id>", methods=["GET", "POST"])
@admin_required
def verify_payment(buyer_info_id):
    """Admin verifies manual payment and generates codes"""
    buyer_info = Category1BuyerInfo.query.get_or_404(buyer_info_id)
    
    if request.method == "GET":
        return render_template(
            "admin/verify_payment.html",
            buyer_info=buyer_info,
            listing=buyer_info.listing
        )
    
    # POST - approve or reject
    action = request.form.get("action")
    
    if action == "approve":
        # Generate codes automatically
        buyer_info.handover_code = generate_handover_code()
        buyer_info.delivery_code = generate_delivery_code()
        
        # Update status
        buyer_info.payment_status = "paid"
        buyer_info.status = "pending_handover"
        
        db.session.commit()
        
        flash(f"✅ Payment approved! Codes generated for Order #{buyer_info.id}", "success")
        return redirect(url_for("admin.pending_payments"))
    
    elif action == "reject":
        # ✅ GET REJECTION REASON
        rejection_reason = request.form.get("rejection_reason", "").strip()
        
        # ✅ VALIDATE: Rejection reason is required
        if not rejection_reason:
            flash("❌ Rejection reason is required", "error")
            return redirect(url_for("admin.verify_payment", buyer_info_id=buyer_info.id))
        
        # Update payment status
        buyer_info.payment_status = "failed"
        buyer_info.status = "payment_failed"
        
        # ✅ STORE REJECTION REASON IN NOTE FIELD
        current_note = buyer_info.note or ""
        rejection_note = f"\n\n[ADMIN REJECTION - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}]\n{rejection_reason}"
        buyer_info.note = (current_note + rejection_note)[:65000]  # TEXT field max
        
        db.session.commit()
        
        flash(f"⚠️ Payment rejected for Order #{buyer_info.id}. Reason: {rejection_reason}", "warning")
        return redirect(url_for("admin.pending_payments"))
    
    return redirect(url_for("admin.pending_payments"))


# ============================================
# USER MANAGEMENT
# ============================================

@admin_bp.route("/users")
@admin_required
def users():
    """User management page"""
    days = int(request.args.get("days", 7))
    cutoff = datetime.utcnow() - timedelta(days=days)
    users_list = User.query.order_by(User.created_at.desc()).all()

    user_stats = []
    for u in users_list:
        login_count = UserLoginLog.query.filter(
            UserLoginLog.user_id == u.id,
            UserLoginLog.login_time >= cutoff
        ).count()
        user_stats.append((u, login_count))

    return render_template("admin/users.html", user_stats=user_stats, login_days=days)


@admin_bp.post("/users/<int:user_id>/toggle-admin")
@admin_required
def toggle_admin(user_id):
    """Toggle admin status for a user"""
    user = User.query.get_or_404(user_id)
    
    # Prevent self-modification
    if user.id == session.get("user_id"):
        return jsonify({"error": "Cannot change your own admin status"}), 400
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    return jsonify({"ok": True, "is_admin": user.is_admin})


@admin_bp.post("/users/<int:user_id>/toggle-active")
@admin_required
def toggle_active(user_id):
    """Toggle user active status"""
    user = User.query.get_or_404(user_id)
    
    # Prevent self-modification
    if user.id == session.get("user_id"):
        return jsonify({"error": "Cannot deactivate your own account"}), 400
    
    user.is_active = not user.is_active
    db.session.commit()
    
    return jsonify({"ok": True, "is_active": user.is_active})


# ============================================
# CATEGORY 1 - ADMIN LISTING MANAGEMENT
# ============================================

@admin_bp.route("/category1")
@admin_required
def category1_listings():
    """View all Category 1 listings"""
    status_filter = request.args.get("status", "all")
    q = Category1Listing.query.order_by(Category1Listing.created_at.desc())
    
    if status_filter in {"pending", "approved", "rejected", "deleted", "sold", "refunded"}:
        q = q.filter_by(admin_status=status_filter)
    
    listings = q.all()
    return render_template(
        "admin/category1_listings.html", 
        listings=listings, 
        status_filter=status_filter
    )


@admin_bp.route("/category1/new", methods=["GET", "POST"])
@admin_required
def create_category1_listing():
    """Admin creates a new Category 1 listing on behalf of a user"""
    if request.method == "GET":
        users = User.query.order_by(User.email).all()
        return render_template("admin/category1_new.html", users=users)

    # POST - create listing
    form = request.form
    required_fields = (
        "user_id", "title", "origin", "origin_airport", "destination", 
        "destination_airport", "travel_date", "price_per_kg", "total_weight"
    )
    
    for field in required_fields:
        if not form.get(field):
            flash(f"Missing required field: {field}", "error")
            return redirect(url_for("admin.create_category1_listing"))

    try:
        user_id = int(form.get("user_id"))
        travel_date = datetime.strptime(form.get("travel_date"), "%Y-%m-%d").date()
        price_per_kg = Decimal(form.get("price_per_kg"))
        total_weight = Decimal(form.get("total_weight"))
        discount = Decimal(form.get("discount_percent") or "0")
        admin_status = form.get("admin_status", "pending")
        
        # ✅ VALIDATE admin_status matches MySQL enum
        valid_statuses = {"pending", "approved", "rejected", "deleted", "sold", "refunded"}
        if admin_status not in valid_statuses:
            admin_status = "pending"

        # Validate user exists
        user = User.query.get(user_id)
        if not user:
            flash("Invalid user selected", "error")
            return redirect(url_for("admin.create_category1_listing"))

        listing = Category1Listing(
            user_id=user_id,
            title=form.get("title"),
            description=form.get("description"),
            service_type=form.get("service_type", "Included pick up at Origin and delivery at Destination."),
            origin=form.get("origin"),
            origin_airport=form.get("origin_airport"),
            origin_delivery_location=form.get("origin_delivery_location"),
            origin_delivery_postcode=form.get("origin_delivery_postcode"),
            destination=form.get("destination"),
            destination_airport=form.get("destination_airport"),
            destination_delivery_location=form.get("destination_delivery_location"),
            destination_delivery_postcode=form.get("destination_delivery_postcode"),
            travel_date=travel_date,
            currency=form.get("currency", "AUD"),
            price_per_kg=price_per_kg,
            total_weight=total_weight,
            discount_percent=discount,
            passport_photo_url=form.get("passport_photo_url"),
            ticket_copy_url=form.get("ticket_copy_url"),
            admin_status=admin_status,
            admin_note=form.get("admin_note")
        )
        
        db.session.add(listing)
        db.session.commit()
        
        flash(f"✅ Listing created successfully (ID: {listing.id})", "success")
        return redirect(url_for("admin.category1_listings"))

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error creating listing: {str(e)}", "error")
        return redirect(url_for("admin.create_category1_listing"))


@admin_bp.route("/category1/<int:listing_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_category1_listing(listing_id):
    """Admin edits an existing Category 1 listing"""
    listing = Category1Listing.query.get_or_404(listing_id)

    if request.method == "GET":
        users = User.query.order_by(User.email).all()
        return render_template("admin/category1_edit.html", listing=listing, users=users)

    # POST - update listing
    form = request.form
    
    try:
        # Update user if changed
        if form.get("user_id"):
            new_user_id = int(form.get("user_id"))
            if User.query.get(new_user_id):
                listing.user_id = new_user_id

        # Update all fields
        listing.title = form.get("title") or listing.title
        listing.description = form.get("description", "")
        listing.service_type = form.get("service_type") or listing.service_type
        listing.origin = form.get("origin") or listing.origin
        listing.origin_airport = form.get("origin_airport") or listing.origin_airport
        listing.origin_delivery_location = form.get("origin_delivery_location")
        listing.origin_delivery_postcode = form.get("origin_delivery_postcode")
        listing.destination = form.get("destination") or listing.destination
        listing.destination_airport = form.get("destination_airport") or listing.destination_airport
        listing.destination_delivery_location = form.get("destination_delivery_location")
        listing.destination_delivery_postcode = form.get("destination_delivery_postcode")
        
        if form.get("travel_date"):
            listing.travel_date = datetime.strptime(form.get("travel_date"), "%Y-%m-%d").date()
        
        if form.get("currency"):
            listing.currency = form.get("currency")
        
        if form.get("price_per_kg"):
            listing.price_per_kg = Decimal(form.get("price_per_kg"))
        
        if form.get("total_weight"):
            listing.total_weight = Decimal(form.get("total_weight"))
        
        if form.get("discount_percent"):
            listing.discount_percent = Decimal(form.get("discount_percent"))
        
        listing.passport_photo_url = form.get("passport_photo_url")
        listing.ticket_copy_url = form.get("ticket_copy_url")
        listing.admin_note = form.get("admin_note")
        
        # ✅ VALIDATE admin_status matches MySQL enum
        if form.get("admin_status") in {"pending", "approved", "rejected", "deleted", "sold", "refunded"}:
            listing.admin_status = form.get("admin_status")

        listing.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash(f"✅ Listing {listing_id} updated successfully", "success")
        return redirect(url_for("admin.category1_listings"))

    except ValueError as e:
        flash(f"❌ Invalid input: {str(e)}", "error")
        return redirect(url_for("admin.edit_category1_listing", listing_id=listing_id))
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error updating listing: {str(e)}", "error")
        return redirect(url_for("admin.edit_category1_listing", listing_id=listing_id))


@admin_bp.post("/category1/<int:listing_id>/update-status")
@admin_required
def update_category1_status(listing_id):
    """Update approval status of a Category 1 listing"""
    listing = Category1Listing.query.get_or_404(listing_id)
    new_status = request.form.get("status")
    
    # ✅ VALIDATE against MySQL enum
    if new_status not in {"pending", "approved", "rejected", "deleted", "sold", "refunded"}:
        return "Invalid status", 400
    
    listing.admin_status = new_status
    db.session.commit()
    
    flash(f"✅ Listing {listing_id} status updated to {new_status}", "success")
    return redirect(url_for("admin.category1_listings"))


@admin_bp.post("/category1/<int:listing_id>/delete")
@admin_required
def delete_category1_listing(listing_id):
    """Admin soft-deletes a Category 1 listing"""
    listing = Category1Listing.query.get_or_404(listing_id)
    
    try:
        # Soft delete by setting admin_status to 'deleted'
        listing.admin_status = "deleted"
        db.session.commit()
        flash(f"✅ Listing {listing_id} marked as deleted", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error deleting listing: {str(e)}", "error")
    
    return redirect(url_for("admin.category1_listings"))


# ============================================
# CATEGORY 2 - ADMIN LISTING MANAGEMENT
# ============================================

@admin_bp.route("/category2")
@admin_required
def category2_listings():
    """View all Category 2 listings"""
    status_filter = request.args.get("status", "all")
    q = Category2Listing.query.order_by(Category2Listing.created_at.desc())
    
    if status_filter in {"pending", "approved", "rejected"}:
        q = q.filter_by(admin_status=status_filter)
    
    listings = q.all()
    return render_template(
        "admin/category2_listings.html", 
        listings=listings, 
        status_filter=status_filter
    )


@admin_bp.route("/category2/<int:listing_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_category2_listing(listing_id):
    """Admin edits an existing Category 2 listing"""
    listing = Category2Listing.query.get_or_404(listing_id)

    if request.method == "GET":
        users = User.query.order_by(User.email).all()
        return render_template("admin/category2_edit.html", listing=listing, users=users)

    # POST - update listing
    form = request.form
    
    try:
        if form.get("user_id"):
            new_user_id = int(form.get("user_id"))
            if User.query.get(new_user_id):
                listing.user_id = new_user_id

        listing.name = form.get("name") or listing.name
        listing.description = form.get("description", "")
        
        if form.get("gender") in {"male", "female", "other"}:
            listing.gender = form.get("gender")
        
        listing.travel_from = form.get("travel_from")
        listing.travel_to = form.get("travel_to")
        
        if form.get("travel_date"):
            listing.travel_date = datetime.strptime(form.get("travel_date"), "%Y-%m-%d").date()
        
        if form.get("price"):
            listing.price = Decimal(form.get("price"))
        
        if form.get("discount_percent"):
            listing.discount_percent = Decimal(form.get("discount_percent"))
        
        listing.image_url = form.get("image_url")
        
        if form.get("admin_status") in {"pending", "approved", "rejected"}:
            listing.admin_status = form.get("admin_status")

        listing.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash(f"✅ Category 2 listing {listing_id} updated successfully", "success")
        return redirect(url_for("admin.category2_listings"))

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error updating listing: {str(e)}", "error")
        return redirect(url_for("admin.edit_category2_listing", listing_id=listing_id))


@admin_bp.post("/category2/<int:listing_id>/update-status")
@admin_required
def update_category2_status(listing_id):
    """Update approval status of a Category 2 listing"""
    listing = Category2Listing.query.get_or_404(listing_id)
    new_status = request.form.get("status")
    
    if new_status not in {"pending", "approved", "rejected"}:
        return "Invalid status", 400
    
    listing.admin_status = new_status
    db.session.commit()
    
    flash(f"✅ Category 2 listing {listing_id} status updated to {new_status}", "success")
    return redirect(url_for("admin.category2_listings"))


# ============================================
# CATEGORY 3 - ADMIN PRODUCT MANAGEMENT
# ============================================

@admin_bp.route("/category3")
@admin_required
def category3_products():
    """View all Category 3 products"""
    status_filter = request.args.get("status", "all")
    q = Category3Product.query.order_by(Category3Product.created_at.desc())
    
    if status_filter in {"pending", "approved", "rejected"}:
        q = q.filter_by(admin_status=status_filter)
    
    products = q.all()
    return render_template(
        "admin/category3_products.html", 
        products=products, 
        status_filter=status_filter
    )


@admin_bp.route("/category3/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_category3_product(product_id):
    """Admin edits an existing Category 3 product"""
    product = Category3Product.query.get_or_404(product_id)

    if request.method == "GET":
        users = User.query.order_by(User.email).all()
        return render_template("admin/category3_edit.html", product=product, users=users)

    # POST - update product
    form = request.form
    
    try:
        if form.get("user_id"):
            new_user_id = int(form.get("user_id"))
            if User.query.get(new_user_id):
                product.user_id = new_user_id

        product.product_name = form.get("product_name") or product.product_name
        product.product_origin_country = form.get("product_origin_country")
        product.description = form.get("description", "")
        
        if form.get("price"):
            product.price = Decimal(form.get("price"))
        
        if form.get("discount_percent"):
            product.discount_percent = Decimal(form.get("discount_percent"))
        
        if form.get("stock"):
            product.stock = int(form.get("stock"))
        
        product.authenticity_proof_url = form.get("authenticity_proof_url")
        product.image_url = form.get("image_url")
        
        if form.get("admin_status") in {"pending", "approved", "rejected"}:
            product.admin_status = form.get("admin_status")

        product.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash(f"✅ Category 3 product {product_id} updated successfully", "success")
        return redirect(url_for("admin.category3_products"))

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error updating product: {str(e)}", "error")
        return redirect(url_for("admin.edit_category3_product", product_id=product_id))


@admin_bp.post("/category3/<int:product_id>/update-status")
@admin_required
def update_category3_status(product_id):
    """Update approval status of a Category 3 product"""
    product = Category3Product.query.get_or_404(product_id)
    new_status = request.form.get("status")
    
    if new_status not in {"pending", "approved", "rejected"}:
        return "Invalid status", 400
    
    product.admin_status = new_status
    db.session.commit()
    
    flash(f"✅ Category 3 product {product_id} status updated to {new_status}", "success")
    return redirect(url_for("admin.category3_products"))


# ============================================
# ANALYTICS & SETTINGS
# ============================================

@admin_bp.route("/analytics")
@admin_required
def analytics():
    """Analytics dashboard"""
    days = int(request.args.get("days", 30))
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Daily visits
    daily_visits = db.session.query(
        func.date(SiteVisit.visited_at).label('date'),
        func.count(SiteVisit.id).label('count')
    ).filter(
        SiteVisit.visited_at >= cutoff
    ).group_by('date').order_by('date').all()

    # Daily logins
    daily_logins = db.session.query(
        func.date(UserLoginLog.login_time).label('date'),
        func.count(UserLoginLog.id).label('count')
    ).filter(
        UserLoginLog.login_time >= cutoff
    ).group_by('date').order_by('date').all()

    # Daily registrations
    daily_registrations = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= cutoff
    ).group_by('date').order_by('date').all()

    # Most active users
    active_users = db.session.query(
        User.id,
        User.full_name,
        User.email,
        func.count(UserLoginLog.id).label('login_count')
    ).join(UserLoginLog).filter(
        UserLoginLog.login_time >= cutoff
    ).group_by(User.id, User.full_name, User.email).order_by(desc('login_count')).limit(10).all()

    return render_template(
        "admin/analytics.html",
        days=days,
        daily_visits=daily_visits,
        daily_logins=daily_logins,
        daily_registrations=daily_registrations,
        active_users=active_users
    )


@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    """Admin settings page"""
    if request.method == "POST":
        flash("✅ Settings updated successfully", "success")
        return redirect(url_for("admin.settings"))
    
    return render_template("admin/settings.html")