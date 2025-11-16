from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from functools import wraps
from datetime import datetime
from decimal import Decimal

from models import db, Category1Listing, User, Category1BuyerInfo
from utils.phone_utils import can_view_full_phone

category1_bp = Blueprint("category1", __name__, url_prefix="/category1")


# ============================================================================
# AUTHENTICATION DECORATOR
# ============================================================================
def login_required(f):
    """Require user to be logged in"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue", "error")
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)
    return decorated


# ============================================================================
# PUBLIC ROUTES (NO AUTH REQUIRED)
# ============================================================================

@category1_bp.route("/")
def marketplace():
    """Public marketplace - show only approved listings"""
    # Get filter parameters
    origin = request.args.get('origin', '').strip()
    destination = request.args.get('destination', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    max_price = request.args.get('max_price', '').strip()
    sort_by = request.args.get('sort', 'newest')
    
    # Base query - only approved listings
    query = Category1Listing.query.filter_by(admin_status="approved")
    
    # Apply filters
    if origin:
        query = query.filter(Category1Listing.origin.ilike(f'%{origin}%'))
    if destination:
        query = query.filter(Category1Listing.destination.ilike(f'%{destination}%'))
    if date_from:
        query = query.filter(Category1Listing.travel_date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    if date_to:
        query = query.filter(Category1Listing.travel_date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    if max_price:
        query = query.filter(Category1Listing.final_price <= float(max_price))
    
    # Apply sorting
    if sort_by == 'price_low':
        query = query.order_by(Category1Listing.final_price.asc())
    elif sort_by == 'price_high':
        query = query.order_by(Category1Listing.final_price.desc())
    elif sort_by == 'discount':
        query = query.order_by(Category1Listing.discount_percent.desc())
    else:  # newest
        query = query.order_by(Category1Listing.created_at.desc())
    
    listings = query.all()
    
    return render_template(
        "category1_marketplace.html", 
        listings=listings,
        filters={
            'origin': origin,
            'destination': destination,
            'date_from': date_from,
            'date_to': date_to,
            'max_price': max_price,
            'sort': sort_by
        }
    )


@category1_bp.route("/<int:listing_id>")
def detail(listing_id):
    """View single listing details (public)"""
    listing = Category1Listing.query.filter_by(
        id=listing_id, 
        admin_status="approved"
    ).first_or_404()
    
    # ✅ Check if current user can view full phone numbers
    user_can_view_phone = False
    if 'user_id' in session:
        user_can_view_phone = can_view_full_phone(session['user_id'], listing_id)
    
    return render_template(
        "category1_detail.html", 
        listing=listing,
        can_view_full_phone=user_can_view_phone
    )


# ============================================================================
# CREATE LISTING FLOW (3-STEP WIZARD) - REQUIRES AUTH
# ============================================================================

@category1_bp.route("/listings/new", methods=["GET"])
@login_required
def create_listing():
    """Show 3-step wizard for creating new listing"""
    return render_template("category1/listing_wizard.html", mode="create")


@category1_bp.route("/listings/new", methods=["POST"])
@login_required
def create_listing_submit():
    """Handle final submission after step 3 (phone verification)"""
    try:
        data = request.get_json()
        
        # ========================================
        # VALIDATION
        # ========================================
        
        # Required fields
        required_fields = [
            "origin", "origin_airport", "destination", "destination_airport",
            "travel_date", "service_type", "currency", "price_per_kg", 
            "total_weight", "origin_phone_number", "phone_verified"
        ]
        
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Ensure phone is verified
        if str(data.get("phone_verified")).lower() != "true":
            return jsonify({"error": "Phone number must be verified"}), 400
        
        # Validate currency (3-letter ISO code)
        currency = data.get("currency", "AUD").upper()
        if len(currency) != 3 or not currency.isalpha():
            return jsonify({"error": "Invalid currency code"}), 400
        
        # Parse date
        try:
            travel_date = datetime.strptime(data["travel_date"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400
        
        if travel_date <= datetime.now().date():
            return jsonify({"error": "Travel date must be in the future"}), 400
        
        # Parse numeric values
        try:
            price_per_kg = Decimal(str(data["price_per_kg"]))
            total_weight = Decimal(str(data["total_weight"]))
            discount_percent = Decimal(str(data.get("discount_percent", "0")))
        except (ValueError, TypeError, ArithmeticError):
            return jsonify({"error": "Invalid numeric values"}), 400
        
        # Validate ranges
        if price_per_kg <= 0 or price_per_kg > 10000:
            return jsonify({"error": "Price per kg must be between 0 and 10000"}), 400
        
        if total_weight <= 0 or total_weight > 100:
            return jsonify({"error": "Total weight must be between 0 and 100 kg"}), 400
        
        if discount_percent < 0 or discount_percent > 100:
            return jsonify({"error": "Discount must be between 0 and 100"}), 400
        
        # ========================================
        # AUTO-GENERATE TITLE
        # ========================================
        
        title = data.get("title", "").strip()
        if not title:
            title = f"{data['origin']} → {data['destination']} | {currency} {price_per_kg}/kg | {total_weight}kg"
        
        # Truncate title if too long
        if len(title) > 255:
            title = title[:252] + "..."
        
        # ========================================
        # CREATE LISTING (EXCLUDE GENERATED COLUMNS)
        # ========================================
        
        listing = Category1Listing(
            user_id=session["user_id"],
            title=title,
            description=data.get("description", "").strip()[:2000],
            
            # ✅ Service Type
            service_type=data["service_type"][:255],
            
            # Phone numbers (E.164 format)
            origin_phone_number=data["origin_phone_number"],
            destination_phone_number=data.get("destination_phone_number", ""),
            
            # Origin details
            origin=data["origin"][:255],
            origin_airport=data["origin_airport"][:255],  # ✅ Now stores full airport name
            origin_delivery_location=data.get("origin_delivery_location", "")[:255],
            origin_delivery_postcode=data.get("origin_delivery_postcode", "")[:20],
            
            # Destination details
            destination=data["destination"][:255],
            destination_airport=data["destination_airport"][:255],  # ✅ Now stores full airport name
            destination_delivery_location=data.get("destination_delivery_location", "")[:255],
            destination_delivery_postcode=data.get("destination_delivery_postcode", "")[:20],
            
            # Travel date
            travel_date=travel_date,
            
            # Currency
            currency=currency,
            
            # Pricing (DO NOT SET base_price or final_price - they're GENERATED by MySQL)
            price_per_kg=price_per_kg,
            total_weight=total_weight,
            discount_percent=discount_percent,
            
            # Document URLs (from Firebase Storage)
            passport_photo_url=data.get("passport_photo_url", "")[:500],
            ticket_copy_url=data.get("ticket_copy_url", "")[:500],
            
            # Admin approval status
            admin_status="pending"
        )
        
        db.session.add(listing)
        db.session.commit()
        
        # ========================================
        # SUCCESS RESPONSE
        # ========================================
        
        return jsonify({
            "success": True,
            "message": "Thank you for choosing Maa Express. Your listing has been submitted and is pending admin approval.",
            "listing_id": listing.id,
            "redirect_url": url_for("account.account")
        }), 201
        
    except ValueError as e:
        return jsonify({"error": f"Invalid data format: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error creating listing: {str(e)}")
        return jsonify({"error": f"Failed to create listing: {str(e)}"}), 500


# ============================================================================
# EDIT LISTING FLOW (3-STEP WIZARD) - REQUIRES AUTH & OWNERSHIP
# ============================================================================

@category1_bp.route("/listings/<int:listing_id>/edit", methods=["GET"])
@login_required
def edit_listing(listing_id):
    """Show 3-step wizard for editing existing listing"""
    listing = Category1Listing.query.get_or_404(listing_id)
    
    # Only allow owner to edit
    if listing.user_id != session["user_id"]:
        flash("You don't have permission to edit this listing", "error")
        return redirect(url_for("account.account"))
    
    return render_template("category1/listing_wizard.html", mode="edit", listing=listing)


@category1_bp.route("/listings/<int:listing_id>/edit", methods=["POST"])
@login_required
def update_listing(listing_id):
    """Handle final submission after step 3 (phone verification) in edit mode"""
    try:
        listing = Category1Listing.query.get_or_404(listing_id)
        
        # Only allow owner to update
        if listing.user_id != session["user_id"]:
            return jsonify({"error": "Unauthorized"}), 403
        
        data = request.get_json()
        
        # ========================================
        # VALIDATION (same as create)
        # ========================================
        
        required_fields = [
            "origin", "origin_airport", "destination", "destination_airport",
            "travel_date", "service_type", "currency", "price_per_kg", 
            "total_weight", "origin_phone_number"
        ]
        
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Parse date
        try:
            travel_date = datetime.strptime(data["travel_date"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400
        
        if travel_date <= datetime.now().date():
            return jsonify({"error": "Travel date must be in the future"}), 400
        
        try:
            price_per_kg = Decimal(str(data["price_per_kg"]))
            total_weight = Decimal(str(data["total_weight"]))
            discount_percent = Decimal(str(data.get("discount_percent", "0")))
        except (ValueError, TypeError, ArithmeticError):
            return jsonify({"error": "Invalid numeric values"}), 400
        
        # Validate currency
        currency = data.get("currency", listing.currency).upper()
        if len(currency) != 3 or not currency.isalpha():
            return jsonify({"error": "Invalid currency code"}), 400
        
        # ========================================
        # UPDATE LISTING (EXCLUDE GENERATED COLUMNS)
        # ========================================
        
        # Auto-generate title if not provided
        title = data.get("title", "").strip()
        if not title:
            title = f"{data['origin']} → {data['destination']} | {currency} {price_per_kg}/kg | {total_weight}kg"
        
        if len(title) > 255:
            title = title[:252] + "..."
        
        listing.title = title
        listing.description = data.get("description", "")[:2000]
        
        # Update service type
        listing.service_type = data["service_type"][:255]
        
        # Update phone numbers
        listing.origin_phone_number = data["origin_phone_number"]
        listing.destination_phone_number = data.get("destination_phone_number", "")
        
        # Update origin details
        listing.origin = data["origin"][:255]
        listing.origin_airport = data["origin_airport"][:255]  # ✅ Full airport name
        listing.origin_delivery_location = data.get("origin_delivery_location", "")[:255]
        listing.origin_delivery_postcode = data.get("origin_delivery_postcode", "")[:20]
        
        # Update destination details
        listing.destination = data["destination"][:255]
        listing.destination_airport = data["destination_airport"][:255]  # ✅ Full airport name
        listing.destination_delivery_location = data.get("destination_delivery_location", "")[:255]
        listing.destination_delivery_postcode = data.get("destination_delivery_postcode", "")[:20]
        
        # Update travel date
        listing.travel_date = travel_date
        
        # Update currency
        listing.currency = currency
        
        # Update pricing (DO NOT UPDATE base_price or final_price - they're GENERATED)
        listing.price_per_kg = price_per_kg
        listing.total_weight = total_weight
        listing.discount_percent = discount_percent
        
        # Update document URLs if provided (from Firebase Storage)
        if data.get("passport_photo_url"):
            listing.passport_photo_url = data["passport_photo_url"][:500]
        if data.get("ticket_copy_url"):
            listing.ticket_copy_url = data["ticket_copy_url"][:500]
        
        # If listing was approved, set back to pending for re-review
        if listing.admin_status == "approved":
            listing.admin_status = "pending"
        
        # Update timestamp
        listing.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Listing updated successfully. Changes will be reviewed by admin." if listing.admin_status == "pending" else "Listing updated successfully.",
            "listing_id": listing.id,
            "redirect_url": url_for("account.account")
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating listing: {str(e)}")
        return jsonify({"error": f"Failed to update listing: {str(e)}"}), 500


# ============================================================================
# DELETE LISTING - REQUIRES AUTH & OWNERSHIP
# ============================================================================

@category1_bp.route("/listings/<int:listing_id>/delete", methods=["POST"])
@login_required
def delete_listing(listing_id):
    """User soft-deletes their own listing"""
    listing = Category1Listing.query.get_or_404(listing_id)
    
    # Only allow owner to delete
    if listing.user_id != session["user_id"]:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # Soft delete - change status instead of removing from DB
        listing.admin_status = "deleted"
        listing.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash("Listing deleted successfully", "success")
        return jsonify({"success": True, "redirect_url": url_for("account.account")}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete listing: {str(e)}"}), 500


# ============================================================================
# API ROUTES (AJAX/JSON)
# ============================================================================

@category1_bp.route("/api/listings/search", methods=["GET"])
def api_search():
    """Search listings via AJAX (public)"""
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify({"results": []}), 200
    
    listings = Category1Listing.query.filter(
        Category1Listing.admin_status == "approved"
    ).filter(
        db.or_(
            Category1Listing.title.ilike(f'%{query}%'),
            Category1Listing.origin.ilike(f'%{query}%'),
            Category1Listing.destination.ilike(f'%{query}%'),
            Category1Listing.origin_airport.ilike(f'%{query}%'),
            Category1Listing.destination_airport.ilike(f'%{query}%')
        )
    ).limit(10).all()
    
    results = [{
        "id": l.id,
        "title": l.title,
        "origin": l.origin,
        "destination": l.destination,
        "price": float(l.final_price) if l.final_price else 0,
        "currency": l.currency,
        "url": url_for('category1.detail', listing_id=l.id)
    } for l in listings]
    
    return jsonify({"results": results}), 200


@category1_bp.route("/api/listings/<int:listing_id>/status", methods=["GET"])
@login_required
def api_listing_status(listing_id):
    """Get listing status (for polling during admin review)"""
    listing = Category1Listing.query.get_or_404(listing_id)
    
    # Only allow owner to check status
    if listing.user_id != session["user_id"]:
        return jsonify({"error": "Unauthorized"}), 403
    
    return jsonify({
        "id": listing.id,
        "admin_status": listing.admin_status,
        "updated_at": listing.updated_at.isoformat()
    }), 200


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@category1_bp.errorhandler(404)
def not_found(e):
    """Custom 404 for category1 routes"""
    if request.path.startswith('/category1/api/'):
        return jsonify({"error": "Resource not found"}), 404
    return render_template("errors/404.html", message="Listing not found"), 404


@category1_bp.errorhandler(500)
def internal_error(e):
    """Custom 500 for category1 routes"""
    db.session.rollback()
    if request.path.startswith('/category1/api/'):
        return jsonify({"error": "Internal server error"}), 500
    return render_template("errors/500.html", message="Something went wrong"), 500