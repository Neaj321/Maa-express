from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from functools import wraps
from datetime import datetime
from decimal import Decimal

from models import (
    db, User, Category1Listing, Category2Listing, Category3Product,
    Category1BuyerInfo, Category2BuyerInfo, Category3Order
)

account_bp = Blueprint("account", __name__, url_prefix="/account")


def login_required(f):
    """Require login for user account routes"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access your account", "error")
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)
    return decorated


# ============================================================================
# USER ACCOUNT PAGE (My Account)
# ============================================================================

@account_bp.route("/")
@login_required
def account():
    """User account page - My Account"""
    user_id = session["user_id"]
    user = User.query.get(user_id)
    
    if not user:
        flash("User not found", "error")
        return redirect(url_for("main.index"))
    
    # Get user's listings (exclude deleted)
    cat1_listings = Category1Listing.query.filter(
        Category1Listing.user_id == user_id,
        Category1Listing.admin_status != 'deleted'
    ).order_by(Category1Listing.created_at.desc()).all()
    
    cat2_listings = Category2Listing.query.filter(
        Category2Listing.user_id == user_id,
        Category2Listing.admin_status != 'deleted'
    ).order_by(Category2Listing.created_at.desc()).all()
    
    cat3_products = Category3Product.query.filter(
        Category3Product.user_id == user_id,
        Category3Product.admin_status != 'deleted'
    ).order_by(Category3Product.created_at.desc()).all()
    
    # Get purchase history
    cat1_purchases = Category1BuyerInfo.query.filter_by(buyer_id=user_id).order_by(
        Category1BuyerInfo.created_at.desc()
    ).all()
    
    cat2_purchases = Category2BuyerInfo.query.filter_by(buyer_id=user_id).order_by(
        Category2BuyerInfo.created_at.desc()
    ).all()
    
    cat3_purchases = Category3Order.query.filter_by(buyer_id=user_id).order_by(
        Category3Order.created_at.desc()
    ).all()
    
    return render_template(
        "account/account.html",
        user=user,
        cat1_listings=cat1_listings,
        cat2_listings=cat2_listings,
        cat3_products=cat3_products,
        cat1_purchases=cat1_purchases,
        cat2_purchases=cat2_purchases,
        cat3_purchases=cat3_purchases
    )


# ============================================================================
# CATEGORY 1 - USER EDIT & SOFT DELETE
# ============================================================================

@account_bp.route("/listing/category1/<int:listing_id>/edit", methods=["GET", "POST"])
@login_required
def edit_category1(listing_id):
    """Edit user's own Category 1 listing"""
    user_id = session["user_id"]
    listing = Category1Listing.query.get_or_404(listing_id)
    
    # Verify ownership
    if listing.user_id != user_id:
        flash("You can only edit your own listings", "error")
        return redirect(url_for("account.account"))
    
    # Prevent editing if deleted
    if listing.admin_status == 'deleted':
        flash("Cannot edit deleted listings", "error")
        return redirect(url_for("account.account"))
    
    if request.method == "GET":
        return render_template("account/edit_category1.html", listing=listing)
    
    # POST - update listing
    form = request.form
    
    try:
        listing.title = form.get("title") or listing.title
        listing.description = form.get("description", "")
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
        
        if form.get("price"):
            listing.price = Decimal(form.get("price"))
        
        if form.get("discount_percent"):
            listing.discount_percent = Decimal(form.get("discount_percent"))
        
        listing.image_url = form.get("image_url")
        listing.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash(f"Listing '{listing.title}' updated successfully", "success")
        return redirect(url_for("account.account"))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating listing: {str(e)}", "error")
        return redirect(url_for("account.edit_category1", listing_id=listing_id))


@account_bp.post("/listing/category1/<int:listing_id>/delete")
@login_required
def delete_category1(listing_id):
    """Soft delete user's own Category 1 listing"""
    user_id = session["user_id"]
    listing = Category1Listing.query.get_or_404(listing_id)
    
    # Verify ownership
    if listing.user_id != user_id:
        flash("You can only delete your own listings", "error")
        return redirect(url_for("account.account"))
    
    # Soft delete (set admin_status to 'deleted')
    listing.admin_status = 'deleted'
    listing.updated_at = datetime.utcnow()
    db.session.commit()
    
    flash(f"Listing '{listing.title}' deleted successfully", "success")
    return redirect(url_for("account.account"))


# ============================================================================
# CATEGORY 2 - USER EDIT & SOFT DELETE
# ============================================================================

@account_bp.route("/listing/category2/<int:listing_id>/edit", methods=["GET", "POST"])
@login_required
def edit_category2(listing_id):
    """Edit user's own Category 2 listing"""
    user_id = session["user_id"]
    listing = Category2Listing.query.get_or_404(listing_id)
    
    if listing.user_id != user_id:
        flash("You can only edit your own listings", "error")
        return redirect(url_for("account.account"))
    
    if listing.admin_status == 'deleted':
        flash("Cannot edit deleted listings", "error")
        return redirect(url_for("account.account"))
    
    if request.method == "GET":
        return render_template("account/edit_category2.html", listing=listing)
    
    form = request.form
    
    try:
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
        listing.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash(f"Listing '{listing.name}' updated successfully", "success")
        return redirect(url_for("account.account"))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating listing: {str(e)}", "error")
        return redirect(url_for("account.edit_category2", listing_id=listing_id))


@account_bp.post("/listing/category2/<int:listing_id>/delete")
@login_required
def delete_category2(listing_id):
    """Soft delete user's own Category 2 listing"""
    user_id = session["user_id"]
    listing = Category2Listing.query.get_or_404(listing_id)
    
    if listing.user_id != user_id:
        flash("You can only delete your own listings", "error")
        return redirect(url_for("account.account"))
    
    listing.admin_status = 'deleted'
    listing.updated_at = datetime.utcnow()
    db.session.commit()
    
    flash(f"Listing '{listing.name}' deleted successfully", "success")
    return redirect(url_for("account.account"))


# ============================================================================
# CATEGORY 3 - USER EDIT & SOFT DELETE
# ============================================================================

@account_bp.route("/product/category3/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_category3(product_id):
    """Edit user's own Category 3 product"""
    user_id = session["user_id"]
    product = Category3Product.query.get_or_404(product_id)
    
    if product.user_id != user_id:
        flash("You can only edit your own products", "error")
        return redirect(url_for("account.account"))
    
    if product.admin_status == 'deleted':
        flash("Cannot edit deleted products", "error")
        return redirect(url_for("account.account"))
    
    if request.method == "GET":
        return render_template("account/edit_category3.html", product=product)
    
    form = request.form
    
    try:
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
        product.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash(f"Product '{product.product_name}' updated successfully", "success")
        return redirect(url_for("account.account"))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating product: {str(e)}", "error")
        return redirect(url_for("account.edit_category3", product_id=product_id))


@account_bp.post("/product/category3/<int:product_id>/delete")
@login_required
def delete_category3(product_id):
    """Soft delete user's own Category 3 product"""
    user_id = session["user_id"]
    product = Category3Product.query.get_or_404(product_id)
    
    if product.user_id != user_id:
        flash("You can only delete your own products", "error")
        return redirect(url_for("account.account"))
    
    product.admin_status = 'deleted'
    product.updated_at = datetime.utcnow()
    db.session.commit()
    
    flash(f"Product '{product.product_name}' deleted successfully", "success")
    return redirect(url_for("account.account"))


# ============================================================================
# PAYOUT DETAILS MANAGEMENT
# ============================================================================

@account_bp.route("/payout", methods=["POST"])
@login_required
def update_payout():
    """Update user payout details"""
    user_id = session["user_id"]
    user = User.query.get(user_id)
    
    form = request.form
    payout_method = form.get("payout_method_type", "none")
    
    try:
        user.payout_method_type = payout_method
        
        if payout_method == "bank":
            if not all([form.get("bank_account_name"), form.get("bank_name"),
                       form.get("bank_bsb_or_routing"), form.get("bank_account_number")]):
                flash("All bank account fields are required", "error")
                return redirect(url_for("account.account"))
            
            user.bank_account_name = form.get("bank_account_name")
            user.bank_name = form.get("bank_name")
            user.bank_bsb_or_routing = form.get("bank_bsb_or_routing")
            user.bank_account_number = form.get("bank_account_number")
            user.mobile_banking_number = None
            user.payid_identifier = None
            user.card_holder_name = None
            user.card_last4 = None
            user.card_brand = None
            user.card_exp_month = None
            user.card_exp_year = None
        
        elif payout_method == "card":
            if not all([form.get("card_holder_name"), form.get("card_last4"),
                       form.get("card_brand"), form.get("card_exp_month"), form.get("card_exp_year")]):
                flash("All card fields are required", "error")
                return redirect(url_for("account.account"))
            
            last4 = form.get("card_last4")
            if not last4.isdigit() or len(last4) != 4:
                flash("Card last 4 digits must be exactly 4 numbers", "error")
                return redirect(url_for("account.account"))
            
            user.card_holder_name = form.get("card_holder_name")
            user.card_last4 = last4
            user.card_brand = form.get("card_brand")
            user.card_exp_month = int(form.get("card_exp_month"))
            user.card_exp_year = int(form.get("card_exp_year"))
            user.bank_account_name = None
            user.bank_name = None
            user.bank_bsb_or_routing = None
            user.bank_account_number = None
            user.mobile_banking_number = None
            user.payid_identifier = None
        
        elif payout_method == "mobile_banking":
            if not form.get("mobile_banking_number"):
                flash("Mobile banking number is required", "error")
                return redirect(url_for("account.account"))
            
            user.mobile_banking_number = form.get("mobile_banking_number")
            user.bank_account_name = None
            user.bank_name = None
            user.bank_bsb_or_routing = None
            user.bank_account_number = None
            user.payid_identifier = None
            user.card_holder_name = None
            user.card_last4 = None
            user.card_brand = None
            user.card_exp_month = None
            user.card_exp_year = None
        
        elif payout_method == "payid":
            if not form.get("payid_identifier"):
                flash("PayID identifier is required", "error")
                return redirect(url_for("account.account"))
            
            user.payid_identifier = form.get("payid_identifier")
            user.bank_account_name = None
            user.bank_name = None
            user.bank_bsb_or_routing = None
            user.bank_account_number = None
            user.mobile_banking_number = None
            user.card_holder_name = None
            user.card_last4 = None
            user.card_brand = None
            user.card_exp_month = None
            user.card_exp_year = None
        
        else:  # none
            user.bank_account_name = None
            user.bank_name = None
            user.bank_bsb_or_routing = None
            user.bank_account_number = None
            user.mobile_banking_number = None
            user.payid_identifier = None
            user.card_holder_name = None
            user.card_last4 = None
            user.card_brand = None
            user.card_exp_month = None
            user.card_exp_year = None
        
        db.session.commit()
        flash("Payout details updated successfully", "success")
        return redirect(url_for("account.account"))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating payout details: {str(e)}", "error")
        return redirect(url_for("account.account"))