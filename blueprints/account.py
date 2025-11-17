from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
from datetime import datetime
from models import db, User, Category1Listing, Category2Listing, Category3Product, Category1BuyerInfo

account_bp = Blueprint("account", __name__, url_prefix="/account")


# ============================================
# LOGIN REQUIRED DECORATOR
# ============================================

def login_required(f):
    """Decorator to require login for account routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page", "error")
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# MAIN ACCOUNT PAGE
# ============================================

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
    
    # Get purchase history (Category1BuyerInfo where buyer is current user)
    cat1_purchases = Category1BuyerInfo.query.filter_by(buyer_user_id=user_id).order_by(
        Category1BuyerInfo.created_at.desc()
    ).all()
    
    # ✅ NEW: Enrich purchases with listing data
    enriched_purchases = []
    for purchase in cat1_purchases:
        listing = Category1Listing.query.get(purchase.listing_id)
        enriched_purchases.append({
            'purchase': purchase,
            'listing': listing
        })
    
    return render_template(
        "account/account.html",
        user=user,
        cat1_listings=cat1_listings,
        cat2_listings=cat2_listings,
        cat3_products=cat3_products,
        cat1_purchases=enriched_purchases  # ✅ Pass enriched data
    )


# ============================================
# SALES DASHBOARD (FOR SELLERS)
# ============================================

@account_bp.route("/sales")
@login_required
def sales_dashboard():
    """
    Sales dashboard - shows all orders for seller's listings
    ✅ UPDATED: Pass buyer_contact_visible flag for each sale
    """
    user_id = session["user_id"]
    user = User.query.get(user_id)
    
    if not user:
        flash("User not found", "error")
        return redirect(url_for("main.index"))
    
    # Get all Category1 listings owned by this seller
    seller_listings = Category1Listing.query.filter_by(user_id=user_id).all()
    listing_ids = [listing.id for listing in seller_listings]
    
    # Get all buyer_info records for these listings (orders/sales)
    cat1_sales = Category1BuyerInfo.query.filter(
        Category1BuyerInfo.listing_id.in_(listing_ids)
    ).order_by(Category1BuyerInfo.created_at.desc()).all()
    
    # ✅ NEW: Enrich each sale with buyer contact visibility flag
    enriched_sales = []
    for sale in cat1_sales:
        listing = Category1Listing.query.get(sale.listing_id)
        
        # ✅ BUYER CONTACT VISIBLE ONLY AFTER PAYMENT COMPLETED
        buyer_contact_visible = (sale.payment_status == 'paid')
        
        enriched_sales.append({
            'sale': sale,
            'listing': listing,
            'buyer_contact_visible': buyer_contact_visible  # ✅ NEW FLAG
        })
    
    return render_template(
        "account/sales_dashboard.html",
        user=user,
        cat1_sales=enriched_sales  # ✅ Pass enriched data with visibility flags
    )


# ============================================
# EDIT LISTING ROUTES
# ============================================

@account_bp.route("/category1/<int:listing_id>/edit", methods=["GET"])
@login_required
def edit_category1(listing_id):
    """Show edit form for Category1 listing"""
    user_id = session["user_id"]
    listing = Category1Listing.query.filter_by(id=listing_id, user_id=user_id).first_or_404()
    return render_template("account/edit_category1.html", listing=listing)


@account_bp.route("/category1/<int:listing_id>/edit", methods=["POST"])
@login_required
def update_category1(listing_id):
    """Update Category1 listing (simple form, not wizard)"""
    user_id = session["user_id"]
    listing = Category1Listing.query.filter_by(id=listing_id, user_id=user_id).first_or_404()
    
    form = request.form
    
    try:
        # Update basic info
        listing.title = form.get("title", "")[:255]
        listing.description = form.get("description", "")[:2000]
        
        # Update origin
        listing.origin = form.get("origin", "")[:255]
        listing.origin_airport = form.get("origin_airport", "")[:100]
        listing.origin_delivery_location = form.get("origin_delivery_location", "")[:255]
        listing.origin_delivery_postcode = form.get("origin_delivery_postcode", "")[:20]
        
        # Update destination
        listing.destination = form.get("destination", "")[:255]
        listing.destination_airport = form.get("destination_airport", "")[:100]
        listing.destination_delivery_location = form.get("destination_delivery_location", "")[:255]
        listing.destination_delivery_postcode = form.get("destination_delivery_postcode", "")[:20]
        
        # Update pricing
        listing.price_per_kg = float(form.get("price_per_kg", 0))
        listing.total_weight = float(form.get("total_weight", 0))
        listing.discount_percent = float(form.get("discount_percent", 0))
        
        # Update travel date
        travel_date_str = form.get("travel_date")
        if travel_date_str:
            listing.travel_date = datetime.strptime(travel_date_str, "%Y-%m-%d").date()
        
        # If listing was approved, mark as pending for re-review
        if listing.admin_status == "approved":
            listing.admin_status = "pending"
        
        listing.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash("Listing updated successfully", "success")
        return redirect(url_for("account.account"))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating listing: {str(e)}", "error")
        return redirect(url_for("account.edit_category1", listing_id=listing_id))


@account_bp.route("/category2/<int:listing_id>/edit", methods=["GET"])
@login_required
def edit_category2(listing_id):
    """Show edit form for Category2 listing"""
    user_id = session["user_id"]
    listing = Category2Listing.query.filter_by(id=listing_id, user_id=user_id).first_or_404()
    return render_template("account/edit_category2.html", listing=listing)


@account_bp.route("/category2/<int:listing_id>/edit", methods=["POST"])
@login_required
def update_category2(listing_id):
    """Update Category2 listing"""
    user_id = session["user_id"]
    listing = Category2Listing.query.filter_by(id=listing_id, user_id=user_id).first_or_404()
    
    form = request.form
    
    try:
        listing.title = form.get("title", "")[:255]
        listing.description = form.get("description", "")[:2000]
        listing.gender = form.get("gender", "")[:20]
        listing.age = int(form.get("age", 0)) if form.get("age") else None
        listing.travel_from = form.get("travel_from", "")[:255]
        listing.travel_to = form.get("travel_to", "")[:255]
        listing.budget_min = float(form.get("budget_min", 0))
        listing.budget_max = float(form.get("budget_max", 0))
        listing.travel_dates = form.get("travel_dates", "")[:255]
        listing.image_url = form.get("image_url", "")[:500]
        
        if listing.admin_status == "approved":
            listing.admin_status = "pending"
        
        listing.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash("Listing updated successfully", "success")
        return redirect(url_for("account.account"))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating listing: {str(e)}", "error")
        return redirect(url_for("account.edit_category2", listing_id=listing_id))


@account_bp.route("/category3/<int:product_id>/edit", methods=["GET"])
@login_required
def edit_category3(product_id):
    """Show edit form for Category3 product"""
    user_id = session["user_id"]
    product = Category3Product.query.filter_by(id=product_id, user_id=user_id).first_or_404()
    return render_template("account/edit_category3.html", product=product)


@account_bp.route("/category3/<int:product_id>/edit", methods=["POST"])
@login_required
def update_category3(product_id):
    """Update Category3 product"""
    user_id = session["user_id"]
    product = Category3Product.query.filter_by(id=product_id, user_id=user_id).first_or_404()
    
    form = request.form
    
    try:
        product.product_name = form.get("product_name", "")[:255]
        product.product_origin_country = form.get("product_origin_country", "")[:100]
        product.description = form.get("description", "")[:2000]
        product.base_price = float(form.get("base_price", 0))
        product.discount_percent = float(form.get("discount_percent", 0))
        product.stock_quantity = int(form.get("stock_quantity", 0))
        product.image_url = form.get("image_url", "")[:500]
        
        if product.admin_status == "approved":
            product.admin_status = "pending"
        
        product.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash("Product updated successfully", "success")
        return redirect(url_for("account.account"))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating product: {str(e)}", "error")
        return redirect(url_for("account.edit_category3", product_id=product_id))


# ============================================
# DELETE LISTING ROUTES (SOFT DELETE)
# ============================================

@account_bp.route("/category1/<int:listing_id>/delete", methods=["POST"])
@login_required
def delete_category1(listing_id):
    """Soft-delete Category1 listing"""
    user_id = session["user_id"]
    listing = Category1Listing.query.filter_by(id=listing_id, user_id=user_id).first_or_404()
    
    listing.admin_status = "deleted"
    db.session.commit()
    
    flash("Listing deleted successfully", "success")
    return redirect(url_for("account.account"))


@account_bp.route("/category2/<int:listing_id>/delete", methods=["POST"])
@login_required
def delete_category2(listing_id):
    """Soft-delete Category2 listing"""
    user_id = session["user_id"]
    listing = Category2Listing.query.filter_by(id=listing_id, user_id=user_id).first_or_404()
    
    listing.admin_status = "deleted"
    db.session.commit()
    
    flash("Listing deleted successfully", "success")
    return redirect(url_for("account.account"))


@account_bp.route("/category3/<int:product_id>/delete", methods=["POST"])
@login_required
def delete_category3(product_id):
    """Soft-delete Category3 product"""
    user_id = session["user_id"]
    product = Category3Product.query.filter_by(id=product_id, user_id=user_id).first_or_404()
    
    product.admin_status = "deleted"
    db.session.commit()
    
    flash("Product deleted successfully", "success")
    return redirect(url_for("account.account"))


# ============================================
# PAYOUT DETAILS UPDATE
# ============================================

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
        
        elif payout_method == "card":
            if not all([form.get("card_holder_name"), form.get("card_last4"), form.get("card_brand")]):
                flash("All card fields are required", "error")
                return redirect(url_for("account.account"))
            
            user.card_holder_name = form.get("card_holder_name")
            user.card_last4 = form.get("card_last4")
            user.card_brand = form.get("card_brand")
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
        
        elif payout_method == "none":
            user.bank_account_name = None
            user.bank_name = None
            user.bank_bsb_or_routing = None
            user.bank_account_number = None
            user.mobile_banking_number = None
            user.payid_identifier = None
            user.card_holder_name = None
            user.card_last4 = None
            user.card_brand = None
        
        db.session.commit()
        flash("Payout details updated successfully", "success")
        return redirect(url_for("account.account"))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating payout details: {str(e)}", "error")
        return redirect(url_for("account.account"))


# ============================================
# ✅ NEW: CODE VERIFICATION ROUTES (HANDOVER & DELIVERY)
# ============================================

@account_bp.route("/verify-handover/<int:buyer_info_id>", methods=["GET", "POST"])
@login_required
def verify_handover(buyer_info_id):
    """
    Seller verifies handover code at origin
    GET: Show verification form
    POST: Process code verification
    """
    buyer_info = Category1BuyerInfo.query.get_or_404(buyer_info_id)
    listing = Category1Listing.query.get_or_404(buyer_info.listing_id)
    
    # Verify seller owns this listing
    if listing.user_id != session["user_id"]:
        flash("Unauthorized access", "error")
        return redirect(url_for("account.sales_dashboard"))
    
    # GET - Show verification form
    if request.method == "GET":
        # ✅ BUYER CONTACT VISIBLE ONLY AFTER PAYMENT
        buyer_contact_visible = (buyer_info.payment_status == 'paid')
        
        return render_template(
            "account/verify_handover.html",
            buyer_info=buyer_info,
            listing=listing,
            buyer_contact_visible=buyer_contact_visible  # ✅ NEW
        )
    
    # POST - Verify code
    data = request.get_json()
    entered_code = data.get("handover_code", "").strip().upper()
    
    if not entered_code:
        return jsonify({"error": "Handover code is required"}), 400
    
    # Verify code matches
    if entered_code != buyer_info.handover_code.upper():
        # Increment attempts
        buyer_info.handover_attempts += 1
        db.session.commit()
        
        remaining = 5 - buyer_info.handover_attempts
        
        if remaining <= 0:
            buyer_info.status = 'disputed'
            db.session.commit()
            return jsonify({"error": "Maximum attempts exceeded. Order marked as disputed"}), 400
        
        return jsonify({"error": f"Invalid code. {remaining} attempts remaining"}), 400
    
    # ✅ SUCCESS - Mark handover verified
    buyer_info.handover_verified_at = datetime.utcnow()
    buyer_info.status = 'in_transit'
    
    # Save optional photo
    if data.get("photo_url"):
        buyer_info.handover_photo_url = data["photo_url"][:500]
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Handover verified successfully! Parcel is now in transit."
    })


@account_bp.route("/verify-delivery/<int:buyer_info_id>", methods=["GET", "POST"])
@login_required
def verify_delivery(buyer_info_id):
    """
    Seller verifies delivery code at destination
    GET: Show verification form
    POST: Process code verification
    """
    buyer_info = Category1BuyerInfo.query.get_or_404(buyer_info_id)
    listing = Category1Listing.query.get_or_404(buyer_info.listing_id)
    
    # Verify seller owns this listing
    if listing.user_id != session["user_id"]:
        flash("Unauthorized access", "error")
        return redirect(url_for("account.sales_dashboard"))
    
    # GET - Show verification form
    if request.method == "GET":
        # ✅ BUYER CONTACT VISIBLE ONLY AFTER PAYMENT
        buyer_contact_visible = (buyer_info.payment_status == 'paid')
        
        return render_template(
            "account/verify_delivery.html",
            buyer_info=buyer_info,
            listing=listing,
            buyer_contact_visible=buyer_contact_visible  # ✅ NEW
        )
    
    # POST - Verify code
    data = request.get_json()
    entered_code = data.get("delivery_code", "").strip().upper()
    
    if not entered_code:
        return jsonify({"error": "Delivery code is required"}), 400
    
    # Verify code matches
    if entered_code != buyer_info.delivery_code.upper():
        # Increment attempts
        buyer_info.delivery_attempts += 1
        db.session.commit()
        
        remaining = 5 - buyer_info.delivery_attempts
        
        if remaining <= 0:
            buyer_info.status = 'disputed'
            db.session.commit()
            return jsonify({"error": "Maximum attempts exceeded. Order marked as disputed"}), 400
        
        return jsonify({"error": f"Invalid code. {remaining} attempts remaining"}), 400
    
    # ✅ SUCCESS - Mark delivery verified
    buyer_info.delivery_verified_at = datetime.utcnow()
    buyer_info.status = 'delivered'
    
    # Save optional photo
    if data.get("photo_url"):
        buyer_info.delivery_photo_url = data["photo_url"][:500]
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Delivery verified successfully! Order is now complete."
    })