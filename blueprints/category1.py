from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from functools import wraps
from datetime import datetime, date, timedelta
from decimal import Decimal
import os
from werkzeug.utils import secure_filename
from config import Config

from models import db, Category1Listing, User, Category1BuyerInfo
from utils.phone_utils import can_view_full_phone
from utils.payment_utils import (
    generate_handover_code,
    generate_delivery_code,
    create_stripe_payment_intent,
    verify_stripe_payment,
    create_paypal_order,
    verify_paypal_payment
)

# ✅ NEW: Firebase Admin SDK import for backend uploads
import firebase_admin
from firebase_admin import credentials, storage

category1_bp = Blueprint("category1", __name__, url_prefix="/category1")

# Maximum file upload size (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024

# Allowed file extensions for proof photos
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}  # ✅ Added PDF for ID documents


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


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================================
# PUBLIC ROUTES (NO AUTH REQUIRED)
# ============================================================================

@category1_bp.route("/")
def marketplace():
    """Public marketplace - show only approved listings"""
    filters = {
        'origin': request.args.get('origin', ''),
        'destination': request.args.get('destination', ''),
        'date_from': request.args.get('date_from', ''),
        'date_to': request.args.get('date_to', '')
    }
    
    query = Category1Listing.query.filter_by(admin_status="approved")
    
    if filters['origin']:
        query = query.filter(Category1Listing.origin.ilike(f"%{filters['origin']}%"))
    if filters['destination']:
        query = query.filter(Category1Listing.destination.ilike(f"%{filters['destination']}%"))
    if filters['date_from']:
        query = query.filter(Category1Listing.travel_date >= datetime.strptime(filters['date_from'], '%Y-%m-%d').date())
    if filters['date_to']:
        query = query.filter(Category1Listing.travel_date <= datetime.strptime(filters['date_to'], '%Y-%m-%d').date())
    
    listings = query.order_by(Category1Listing.travel_date.asc()).all()
    
    return render_template("category1/marketplace.html", listings=listings, filters=filters)


@category1_bp.route("/<int:listing_id>")
def detail(listing_id):
    """View single listing details (public)"""
    listing = Category1Listing.query.filter_by(
        id=listing_id, 
        admin_status="approved"
    ).first_or_404()
    
    # ✅ UPDATED: Contact masking logic (only show if payment_status = 'paid')
    seller_contact_visible = False
    if 'user_id' in session:
        # Check if current user has PAID purchase for this listing
        paid_purchase = Category1BuyerInfo.query.filter_by(
            listing_id=listing_id,
            buyer_id=session['user_id'],
            payment_status='paid'
        ).first()
        
        seller_contact_visible = paid_purchase is not None
    
    return render_template(
        "category1_detail.html", 
        listing=listing,
        seller_contact_visible=seller_contact_visible  # ✅ UPDATED variable name
    )


# ============================================================================
# CREATE LISTING FLOW (3-STEP WIZARD) - REQUIRES AUTH
# ============================================================================

@category1_bp.route("/listings/new", methods=["GET"])
@login_required
def create_listing():
    """Show 3-step wizard for creating new listing"""
    return render_template(
        "category1/listing_wizard.html", 
        mode="create",
        datetime=datetime,
        timedelta=timedelta
    )


@category1_bp.route("/api/validate-step", methods=["POST"])
@login_required
def validate_step():
    """Validate wizard step data before moving to next step"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"valid": False, "error": "No data provided"}), 400
        
        step = data.get("step")
        
        if step == 1:
            # Validate travel details
            required = ["travel_date", "service_type", "origin", "origin_airport", 
                       "destination", "destination_airport"]
            missing = [f for f in required if not data.get(f)]
            
            if missing:
                return jsonify({
                    "valid": False, 
                    "error": f"Missing: {', '.join(missing)}"
                }), 400
            
            # Validate travel date
            try:
                travel_date = datetime.strptime(data["travel_date"], "%Y-%m-%d").date()
                if travel_date <= datetime.now().date():
                    return jsonify({
                        "valid": False,
                        "error": "Travel date must be tomorrow or later"
                    }), 400
            except ValueError:
                return jsonify({
                    "valid": False,
                    "error": "Invalid date format"
                }), 400
            
            return jsonify({"valid": True})
        
        elif step == 2:
            # Validate pricing and documents
            required = ["currency", "price_per_kg", "total_weight"]
            missing = [f for f in required if not data.get(f)]
            
            if missing:
                return jsonify({
                    "valid": False,
                    "error": f"Missing: {', '.join(missing)}"
                }), 400
            
            # Validate numeric fields
            try:
                price_per_kg = Decimal(str(data["price_per_kg"]))
                total_weight = Decimal(str(data["total_weight"]))
                discount = Decimal(str(data.get("discount_percent", "0")))
                
                if price_per_kg <= 0 or price_per_kg > 10000:
                    return jsonify({
                        "valid": False,
                        "error": "Price per kg must be between 0.01 and 10000"
                    }), 400
                
                if total_weight <= 0 or total_weight > 1000:
                    return jsonify({
                        "valid": False,
                        "error": "Total weight must be between 0.01 and 1000 kg"
                    }), 400
                
                if discount < 0 or discount > 100:
                    return jsonify({
                        "valid": False,
                        "error": "Discount must be between 0 and 100%"
                    }), 400
                
            except (ValueError, TypeError):
                return jsonify({
                    "valid": False,
                    "error": "Invalid numeric values"
                }), 400
            
            return jsonify({"valid": True})
        
        elif step == 3:
            # Validate phone numbers
            required = ["origin_phone_number"]
            missing = [f for f in required if not data.get(f)]
            
            if missing:
                return jsonify({
                    "valid": False,
                    "error": f"Missing: {', '.join(missing)}"
                }), 400
            
            return jsonify({"valid": True})
        
        else:
            return jsonify({"valid": False, "error": "Invalid step"}), 400
            
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)}), 500


@category1_bp.route("/listings/new", methods=["POST"])
@login_required
def create_listing_submit():
    """Handle final submission after step 3 (phone verification)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate travel date
        try:
            travel_date = datetime.strptime(data["travel_date"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            return jsonify({"error": "Invalid travel date"}), 400
        
        if travel_date <= datetime.now().date():
            return jsonify({"error": "Travel date must be tomorrow or later (no past or today dates allowed)"}), 400
        
        # Validate currency
        currency = data["currency"].upper()
        if currency not in ['AUD', 'USD', 'EUR', 'GBP', 'BDT', 'INR']:
            return jsonify({"error": "Invalid currency"}), 400
        
        # Validate numeric fields
        try:
            price_per_kg = Decimal(str(data["price_per_kg"]))
            total_weight = Decimal(str(data["total_weight"]))
            discount_percent = Decimal(str(data.get("discount_percent", "0")))
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid numeric values"}), 400
        
        if price_per_kg <= 0 or price_per_kg > 10000:
            return jsonify({"error": "Price per kg must be between 0.01 and 10000"}), 400
        
        if total_weight <= 0 or total_weight > 1000:
            return jsonify({"error": "Total weight must be between 0.01 and 1000 kg"}), 400
        
        if discount_percent < 0 or discount_percent > 100:
            return jsonify({"error": "Discount must be between 0 and 100%"}), 400
        
        # Auto-generate title if not provided
        title = data.get("title", "").strip()
        if not title:
            title = f"{data['origin']} → {data['destination']} | {currency} {price_per_kg}/kg | {total_weight}kg"
        
        # Create listing
        listing = Category1Listing(
            seller_id=session["user_id"],
            title=title[:255],
            description=data.get("description", "")[:5000],
            service_type=data["service_type"][:255],
            
            # Origin details
            origin=data["origin"][:255],
            origin_airport=data["origin_airport"][:255],
            origin_delivery_location=data.get("origin_delivery_location", "")[:255],
            origin_delivery_postcode=data.get("origin_delivery_postcode", "")[:20],
            origin_phone_number=data["origin_phone_number"][:30],
            
            # Destination details
            destination=data["destination"][:255],
            destination_airport=data["destination_airport"][:255],
            destination_delivery_location=data.get("destination_delivery_location", "")[:255],
            destination_delivery_postcode=data.get("destination_delivery_postcode", "")[:20],
            destination_phone_number=data.get("destination_phone_number", "")[:30],
            
            # Travel date
            travel_date=travel_date,
            
            # Currency
            currency=currency,
            
            # Pricing
            price_per_kg=price_per_kg,
            total_weight=total_weight,
            discount_percent=discount_percent,
            
            # Document URLs
            passport_photo_url=data.get("passport_photo_url", "")[:500],
            ticket_copy_url=data.get("ticket_copy_url", "")[:500],
            
            # Admin status
            admin_status="pending"
        )
        
        db.session.add(listing)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Thank you for choosing Maa Express. Your listing has been submitted and is pending admin approval.",
            "listing_id": listing.id,
            "redirect_url": url_for("account.account")
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating listing: {str(e)}")
        return jsonify({"error": f"Failed to create listing: {str(e)}"}), 500


# ============================================================================
# EDIT LISTING FLOW - REQUIRES AUTH & OWNERSHIP
# ============================================================================

@category1_bp.route("/listings/<int:listing_id>/edit", methods=["GET"])
@login_required
def edit_listing(listing_id):
    """Show edit wizard"""
    listing = Category1Listing.query.get_or_404(listing_id)
    
    if listing.seller_id != session["user_id"]:
        flash("Unauthorized access", "error")
        return redirect(url_for("account.account"))
    
    return render_template(
        "category1/listing_wizard.html",
        mode="edit",
        listing=listing,
        datetime=datetime,
        timedelta=timedelta
    )


@category1_bp.route("/listings/<int:listing_id>/edit", methods=["POST"])
@login_required
def update_listing(listing_id):
    """Update listing"""
    listing = Category1Listing.query.get_or_404(listing_id)
    
    if listing.seller_id != session["user_id"]:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        data = request.get_json()
        
        # Update fields (similar validation as create)
        listing.title = data.get("title", listing.title)[:255]
        listing.description = data.get("description", listing.description)[:5000]
        listing.service_type = data.get("service_type", listing.service_type)[:255]
        
        listing.origin = data.get("origin", listing.origin)[:255]
        listing.origin_airport = data.get("origin_airport", listing.origin_airport)[:255]
        listing.destination = data.get("destination", listing.destination)[:255]
        listing.destination_airport = data.get("destination_airport", listing.destination_airport)[:255]
        
        if "travel_date" in data:
            listing.travel_date = datetime.strptime(data["travel_date"], "%Y-%m-%d").date()
        
        if "price_per_kg" in data:
            listing.price_per_kg = Decimal(str(data["price_per_kg"]))
        if "total_weight" in data:
            listing.total_weight = Decimal(str(data["total_weight"]))
        if "discount_percent" in data:
            listing.discount_percent = Decimal(str(data["discount_percent"]))
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Listing updated successfully",
            "redirect_url": url_for("account.account")
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@category1_bp.route("/listings/<int:listing_id>/delete", methods=["POST"])
@login_required
def delete_listing(listing_id):
    """Soft delete listing"""
    listing = Category1Listing.query.get_or_404(listing_id)
    
    if listing.seller_id != session["user_id"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    
    listing.admin_status = "deleted"
    db.session.commit()
    
    return jsonify({"success": True, "message": "Listing deleted"})


# ============================================================================
# BUY NOW FLOW - REQUIRES AUTH
# ============================================================================

@category1_bp.route("/listings/<int:listing_id>/buy", methods=["GET"])
@login_required
def buy_form(listing_id):
    """Show purchase form"""
    listing = Category1Listing.query.filter_by(
        id=listing_id,
        admin_status="approved"
    ).first_or_404()
    
    # Prevent self-purchase
    if listing.seller_id == session["user_id"]:
        flash("You cannot buy your own listing", "error")
        return redirect(url_for("category1.detail", listing_id=listing_id))
    
    return render_template(
        "category1/buy_form.html",
        listing=listing
    )


@category1_bp.route("/listings/<int:listing_id>/buy", methods=["POST"])
@login_required
def process_purchase(listing_id):
    """
    Process purchase and create buyer info record.
    
    Requirements:
    1. Creates category1_buyer_info row with all required fields
    2. Sets status='pending_payment', payment_status='pending'
    3. Does NOT generate handover/delivery codes yet (codes generated after payment)
    4. Uses exact MySQL schema field names
    """
    try:
        listing = Category1Listing.query.filter_by(
            id=listing_id,
            admin_status="approved"
        ).first_or_404()
        
        # Prevent self-purchase
        if listing.seller_id == session["user_id"]:
            return jsonify({
                "success": False, 
                "error": "Cannot buy your own listing"
            }), 403
        
        data = request.get_json()
        
        # ✅ VALIDATE ALL REQUIRED FIELDS (as per requirements)
        required_fields = [
            "receiver_fullname", 
            "receiver_phone", 
            "receiver_email",
            "delivery_address",
            "delivery_postcode",
            "delivery_country",
            "purchased_weight",
            "payment_method"
        ]
        
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {', '.join(missing)}"
            }), 400
        
        # ✅ VALIDATE PAYMENT METHOD (exact MySQL enum values)
        payment_method = data["payment_method"].upper()
        valid_payment_methods = [
            'PAYPAL', 'STRIPE', 'WISE', 
            'BANK_ACCOUNT', 'MOBILE_BANKING_BKASH_NAGAD', 
            'PAYID', 'BKASH_TO_BANK'
        ]
        
        if payment_method not in valid_payment_methods:
            return jsonify({
                "success": False,
                "error": f"Invalid payment method. Must be one of: {', '.join(valid_payment_methods)}"
            }), 400
        
        # Validate purchased weight
        try:
            purchased_weight = Decimal(str(data["purchased_weight"]))
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "error": "Invalid weight value"
            }), 400
        
        if purchased_weight <= 0 or purchased_weight > float(listing.total_weight):
            return jsonify({
                "success": False,
                "error": f"Weight must be between 0.01 and {listing.total_weight} kg"
            }), 400
        
        # Calculate price
        base_price = float(listing.price_per_kg) * float(purchased_weight)
        discount_amount = base_price * (float(listing.discount_percent or 0) / 100)
        total_price = base_price - discount_amount
        
        # Ensure minimum price
        if total_price <= 0:
            total_price = 0.01
        
        # ✅ CREATE BUYER INFO RECORD (as per requirements)
        buyer_info = Category1BuyerInfo(
            listing_id=listing.id,
            buyer_id=session["user_id"],
            
            # Receiver details (exact field names from schema)
            receiver_fullname=data["receiver_fullname"][:255],
            receiver_phone=data["receiver_phone"][:30],
            receiver_email=data["receiver_email"][:255],
            
            # Delivery details (exact field names from schema)
            delivery_address=data["delivery_address"],  # TEXT field
            delivery_postcode=data["delivery_postcode"][:20],
            delivery_country=data["delivery_country"][:255],
            
            # Optional note
            note=data.get("note", "")[:1000] if data.get("note") else None,
            
            # Purchase details (exact field names from schema)
            purchased_weight=Decimal(str(purchased_weight)),
            purchase_price=Decimal(str(total_price)),
            
            # ✅ PAYMENT DETAILS (as per requirements)
            payment_method=payment_method,  # ENUM value
            payment_status="pending",  # ✅ Set to 'pending' (requirement #2)
            payment_transaction_id=None,  # Will be set after payment
            payment_receipt_url=None,  # For manual payments
            payment_reference=None,  # For manual payments
            
            # ✅ ORDER STATUS (as per requirements)
            status="pending_payment",  # ✅ Set to 'pending_payment' (requirement #2)
            
            # ✅ DO NOT GENERATE CODES YET (requirement #2)
            # Codes will be generated in process_payment() after successful payment
            handover_code="PENDING",  # Placeholder (MySQL requires NOT NULL)
            delivery_code="PENDING",   # Placeholder (MySQL requires NOT NULL)
            
            # Verification fields (null initially)
            handover_verified_at=None,
            delivery_verified_at=None,
            handover_attempts=0,
            delivery_attempts=0,
            handover_photo_url=None,
            delivery_photo_url=None,
            
            # ✅ NEW FIELDS (will be populated after payment)
            luggage_photo_url=None,  # Will be uploaded after payment
            sender_id_url=None  # Will be uploaded after payment
        )
        
        db.session.add(buyer_info)
        db.session.commit()
        
        # ✅ REDIRECT TO PAYMENT PAGE (codes will be generated after payment)
        return jsonify({
            "success": True,
            "message": "Purchase initiated successfully. Please complete payment.",
            "redirect_url": url_for(
                "category1.payment_page",
                buyer_info_id=buyer_info.id
            )
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Purchase error: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Purchase failed: {str(e)}"
        }), 500


# ============================================================================
# PAYMENT FLOW
# ============================================================================

@category1_bp.route("/purchase/<int:buyer_info_id>/payment", methods=["GET"])
@login_required
def payment_page(buyer_info_id):
    """Show payment page"""
    buyer_info = Category1BuyerInfo.query.get_or_404(buyer_info_id)
    
    if buyer_info.buyer_id != session["user_id"]:
        flash("Unauthorized access", "error")
        return redirect(url_for("main.index"))
    
    listing = buyer_info.listing
    total_amount = float(buyer_info.purchase_price)
    
    stripe_client_secret = None
    
    if listing.currency.upper() in ['AUD', 'USD', 'EUR', 'GBP']:
        amount_cents = int(total_amount * 100)
        
        from config import Config

        if Config.STRIPE_SECRET_KEY:
            buyer = User.query.get(buyer_info.buyer_id)
            intent = create_stripe_payment_intent(
                amount_cents=amount_cents,
                currency=listing.currency,
                buyer_info_id=buyer_info.id,
                buyer_email=buyer.email
            )
            
            if intent:
                stripe_client_secret = intent.get("client_secret")
    
    return render_template(
        "category1/payment.html",
        buyer_info=buyer_info,
        listing=listing,
        total_amount=total_amount,
        stripe_client_secret=stripe_client_secret
    )


@category1_bp.route("/purchase/<int:buyer_info_id>/payment/process", methods=["POST"])
@login_required
def process_payment(buyer_info_id):
    """Process payment and generate handover/delivery codes"""
    try:
        buyer_info = Category1BuyerInfo.query.get_or_404(buyer_info_id)
        
        if buyer_info.buyer_id != session["user_id"]:
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        
        data = request.get_json()
        payment_method = data.get("payment_method", "").upper()
        
        # ✅ FIXED: Include WISE in valid methods
        valid_methods = [
            'STRIPE', 'PAYPAL', 'WISE',
            'BANK_ACCOUNT', 'BKASH_TO_BANK',
            'PAYID', 'MOBILE_BANKING_BKASH_NAGAD'
        ]
        
        if payment_method not in valid_methods:
            return jsonify({
                "success": False,
                "error": "Invalid payment method"
            }), 400
        
        payment_success = False
        transaction_id = None
        
        # ============================================
        # INSTANT PAYMENT METHODS (STRIPE/PAYPAL)
        # ============================================
        
        if payment_method == 'STRIPE':
            payment_intent_id = data.get("payment_intent_id")
            if payment_intent_id:
                payment_success, transaction_id = verify_stripe_payment(payment_intent_id)
        
        elif payment_method == 'PAYPAL':
            paypal_order_id = data.get("paypal_order_id")
            if paypal_order_id:
                payment_success, transaction_id = verify_paypal_payment(paypal_order_id)
        
        # ============================================
        # MANUAL PAYMENT METHODS (BANK/WISE/BKASH/PAYID)
        # ============================================
        
        elif payment_method in ['BANK_ACCOUNT', 'WISE', 'BKASH_TO_BANK', 'PAYID', 'MOBILE_BANKING_BKASH_NAGAD']:
            # Save receipt and reference
            buyer_info.payment_receipt_url = data.get("receipt_url", "")[:500]
            buyer_info.payment_reference = data.get("payment_reference", "")[:255]
            buyer_info.payment_method = payment_method
            buyer_info.payment_status = "manual_pay"  # ✅ Set to manual_pay (admin will approve)
            
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Payment submitted successfully. We will verify your payment within 24 hours.",
                "redirect_url": url_for("account.account")
            })
        
        # ============================================
        # FINALIZE INSTANT PAYMENTS
        # ============================================
        
        if payment_success:
            # ✅ REDIRECT TO UPLOAD PAGE (NEW STEP) - Don't generate codes yet
            buyer_info.payment_status = "paid"
            buyer_info.payment_method = payment_method
            buyer_info.payment_transaction_id = transaction_id
            buyer_info.status = "pending_handover"
            
            db.session.commit()
            
            # ✅ NEW: Redirect to upload page (luggage photo + sender ID)
            return jsonify({
                "success": True,
                "message": "Payment successful! Please upload required documents.",
                "redirect_url": url_for(
                    "category1.upload_documents",
                    buyer_info_id=buyer_info.id
                )
            })
            
        else:
            return jsonify({
                "success": False,
                "error": "Payment processing failed"
            }), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": f"Payment failed: {str(e)}"
        }), 500


# ✅ NEW ROUTE: Upload documents after payment success
@category1_bp.route("/purchase/<int:buyer_info_id>/upload-documents", methods=["GET", "POST"])
@login_required
def upload_documents(buyer_info_id):
    """
    Upload luggage photo and sender ID after payment success.
    Only accessible if payment_status = 'paid'.
    """
    buyer_info = Category1BuyerInfo.query.get_or_404(buyer_info_id)
    
    # Security check
    if buyer_info.buyer_id != session["user_id"]:
        flash("Unauthorized access", "error")
        return redirect(url_for("main.index"))
    
    # Must have paid
    if buyer_info.payment_status != "paid":
        flash("Payment not completed. Please complete payment first.", "warning")
        return redirect(url_for("category1.payment_page", buyer_info_id=buyer_info.id))
    
    # GET - Show upload form
    if request.method == "GET":
        return render_template(
            "category1/upload_documents.html",
            buyer_info=buyer_info,
            listing=buyer_info.listing
        )
    
    # POST - Process uploads
    try:
        # Get URLs from request (frontend uploads to Firebase)
        data = request.get_json()
        
        luggage_photo_url = data.get("luggage_photo_url", "")
        sender_id_url = data.get("sender_id_url", "")
        
        # Validate sender ID (mandatory)
        if not sender_id_url or len(sender_id_url) < 10:
            return jsonify({
                "success": False,
                "error": "Sender identity document is required"
            }), 400
        
        # Save URLs
        buyer_info.luggage_photo_url = luggage_photo_url[:500] if luggage_photo_url else None
        buyer_info.sender_id_url = sender_id_url[:500]
        
        # ✅ NOW GENERATE CODES (after documents uploaded)
        if buyer_info.handover_code == "PENDING":
            buyer_info.handover_code = generate_handover_code()
        if buyer_info.delivery_code == "PENDING":
            buyer_info.delivery_code = generate_delivery_code()
        
        # ✅ UPDATE USER.user_ID (only if NULL)
        buyer = User.query.get(buyer_info.buyer_id)
        if buyer and (not buyer.user_ID or buyer.user_ID.strip() == ""):
            buyer.user_ID = sender_id_url[:500]
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Documents uploaded successfully!",
            "redirect_url": url_for("category1.purchase_success", buyer_info_id=buyer_info.id)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": f"Upload failed: {str(e)}"
        }), 500


@category1_bp.route("/upload-receipt", methods=["POST"])
@login_required
def upload_receipt():
    """Upload payment receipt via backend"""
    try:
        if 'receipt_file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['receipt_file']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type"}), 400
        
        # Upload to Firebase Storage
        bucket = storage.bucket()
        filename = secure_filename(file.filename)
        blob_name = f"receipts/{session['user_id']}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        blob = bucket.blob(blob_name)
        
        blob.upload_from_file(file, content_type=file.content_type)
        blob.make_public()
        
        return jsonify({
            "success": True,
            "url": blob.public_url
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@category1_bp.route("/purchase/<int:buyer_info_id>/payment/stripe-return", methods=["GET"])
@login_required
def stripe_return(buyer_info_id):
    """Handle Stripe payment return after 3D Secure or redirect"""
    buyer_info = Category1BuyerInfo.query.get_or_404(buyer_info_id)
    
    if buyer_info.buyer_id != session["user_id"]:
        flash("Unauthorized access", "error")
        return redirect(url_for("main.index"))
    
    # Get payment intent ID from query params
    payment_intent_id = request.args.get('payment_intent')
    
    if not payment_intent_id:
        flash("Missing payment information", "error")
        return redirect(url_for("category1.payment_page", buyer_info_id=buyer_info.id))
    
    # Verify payment
    payment_success, transaction_id = verify_stripe_payment(payment_intent_id)
    
    if payment_success:
        # Update payment
        buyer_info.payment_status = "paid"
        buyer_info.payment_method = "STRIPE"
        buyer_info.payment_transaction_id = transaction_id
        buyer_info.status = "pending_handover"
        
        db.session.commit()
        
        # ✅ REDIRECT TO UPLOAD PAGE
        flash("Payment successful!", "success")
        return redirect(url_for("category1.upload_documents", buyer_info_id=buyer_info.id))
    else:
        flash("Payment verification failed. Please try again.", "error")
        return redirect(url_for("category1.payment_page", buyer_info_id=buyer_info.id))


@category1_bp.route("/purchase/<int:buyer_info_id>/success", methods=["GET"])
@login_required
def purchase_success(buyer_info_id):
    """Show purchase success page with handover/delivery codes"""
    buyer_info = Category1BuyerInfo.query.get_or_404(buyer_info_id)
    
    if buyer_info.buyer_id != session["user_id"]:
        flash("Unauthorized access", "error")
        return redirect(url_for("main.index"))
    
    if buyer_info.payment_status != "paid":
        flash("Payment not completed", "warning")
        return redirect(url_for("category1.payment_page", buyer_info_id=buyer_info.id))
    
    # ✅ CHECK: If documents not uploaded, redirect to upload page
    if not buyer_info.sender_id_url or buyer_info.handover_code == "PENDING":
        flash("Please upload required documents", "warning")
        return redirect(url_for("category1.upload_documents", buyer_info_id=buyer_info.id))
    
    # ✅ SHOW SELLER CONTACT (payment verified)
    seller = buyer_info.listing.seller
    
    return render_template(
        "category1/purchase_success.html",
        buyer_info=buyer_info,
        listing=buyer_info.listing,
        seller=seller,
        seller_contact_visible=True  # ✅ Always True on success page
    )


@category1_bp.route("/purchase/<int:buyer_info_id>/payment/paypal-return", methods=["GET"])
@login_required
def paypal_return(buyer_info_id):
    """Handle PayPal payment return after user approves payment"""
    buyer_info = Category1BuyerInfo.query.get_or_404(buyer_info_id)
    
    if buyer_info.buyer_id != session["user_id"]:
        flash("Unauthorized access", "error")
        return redirect(url_for("main.index"))
    
    # Get PayPal order ID from query params
    paypal_order_id = request.args.get('token')
    
    if not paypal_order_id:
        flash("Missing PayPal order information", "error")
        return redirect(url_for("category1.payment_page", buyer_info_id=buyer_info.id))
    
    # Verify payment
    payment_success, transaction_id = verify_paypal_payment(paypal_order_id)
    
    if payment_success:
        # Update payment
        buyer_info.payment_status = "paid"
        buyer_info.payment_method = "PAYPAL"
        buyer_info.payment_transaction_id = transaction_id
        buyer_info.status = "pending_handover"
        
        db.session.commit()
        
        # ✅ REDIRECT TO UPLOAD PAGE
        flash("Payment successful!", "success")
        return redirect(url_for("category1.upload_documents", buyer_info_id=buyer_info.id))
    else:
        flash("PayPal payment verification failed. Please try again.", "error")
        return redirect(url_for("category1.payment_page", buyer_info_id=buyer_info.id))


# ============================================================================
# SELLER VERIFICATION ROUTES (HANDOVER & DELIVERY)
# ============================================================================

@category1_bp.route("/sales/<int:buyer_info_id>/verify-handover", methods=["GET", "POST"])
@login_required
def verify_handover(buyer_info_id):
    """Seller verifies handover at origin"""
    buyer_info = Category1BuyerInfo.query.get_or_404(buyer_info_id)
    listing = buyer_info.listing
    
    # Check if current user is the seller
    if listing.seller_id != session["user_id"]:
        if request.method == "POST":
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        flash("Unauthorized access", "error")
        return redirect(url_for("account.account"))
    
    if request.method == "GET":
        # ✅ SHOW BUYER CONTACT (seller can see after payment_status='paid')
        buyer_contact_visible = buyer_info.payment_status == 'paid'
        
        return render_template(
            "category1/verify_handover.html",
            buyer_info=buyer_info,
            listing=listing,
            buyer_contact_visible=buyer_contact_visible
        )
    
    # POST request - process verification
    try:
        # Check if already verified
        if buyer_info.handover_verified_at:
            return jsonify({
                "success": False,
                "error": "Handover already verified"
            }), 400
        
        # Check if order is in correct status
        if buyer_info.status != "pending_handover":
            return jsonify({
                "success": False,
                "error": f"Cannot verify handover. Current status: {buyer_info.status}"
            }), 400
        
        # Check if too many failed attempts
        if buyer_info.handover_attempts >= 5:
            buyer_info.status = "disputed"
            db.session.commit()
            return jsonify({
                "success": False,
                "error": "Too many failed attempts. Order marked as disputed."
            }), 400
        
        data = request.get_json() if request.is_json else request.form
        entered_code = data.get("handover_code", "").strip().upper()
        
        if not entered_code:
            return jsonify({
                "success": False,
                "error": "Handover code is required"
            }), 400
        
        # Verify code
        if entered_code == buyer_info.handover_code.upper():
            # Success
            buyer_info.handover_verified_at = datetime.utcnow()
            buyer_info.status = "in_transit"
            db.session.commit()
            
            if request.is_json:
                return jsonify({
                    "success": True,
                    "message": "Handover verified successfully!"
                })
            else:
                flash("Handover verified successfully!", "success")
                return redirect(url_for("account.sales_dashboard"))
        else:
            buyer_info.handover_attempts += 1
            db.session.commit()
            
            return jsonify({
                "success": False,
                "error": f"Invalid handover code. Attempts: {buyer_info.handover_attempts}/5"
            }), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": f"Verification failed: {str(e)}"
        }), 500


@category1_bp.route("/sales/<int:buyer_info_id>/verify-delivery", methods=["GET", "POST"])
@login_required
def verify_delivery(buyer_info_id):
    """Seller verifies delivery at destination"""
    buyer_info = Category1BuyerInfo.query.get_or_404(buyer_info_id)
    listing = buyer_info.listing
    
    # Check if current user is the seller
    if listing.seller_id != session["user_id"]:
        if request.method == "POST":
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        flash("Unauthorized access", "error")
        return redirect(url_for("account.account"))
    
    if request.method == "GET":
        # ✅ SHOW BUYER CONTACT (seller can see after payment_status='paid')
        buyer_contact_visible = buyer_info.payment_status == 'paid'
        
        return render_template(
            "category1/verify_delivery.html",
            buyer_info=buyer_info,
            listing=listing,
            buyer_contact_visible=buyer_contact_visible
        )
    
    # POST request - process verification
    try:
        # Check if already verified
        if buyer_info.delivery_verified_at:
            return jsonify({
                "success": False,
                "error": "Delivery already verified"
            }), 400
        
        # Check if order is in correct status
        if buyer_info.status != "in_transit":
            return jsonify({
                "success": False,
                "error": f"Cannot verify delivery. Current status: {buyer_info.status}"
            }), 400
        
        # Check if too many failed attempts
        if buyer_info.delivery_attempts >= 5:
            buyer_info.status = "disputed"
            db.session.commit()
            return jsonify({
                "success": False,
                "error": "Too many failed attempts. Order marked as disputed."
            }), 400
        
        data = request.get_json() if request.is_json else request.form
        entered_code = data.get("delivery_code", "").strip().upper()
        
        if not entered_code:
            return jsonify({
                "success": False,
                "error": "Delivery code is required"
            }), 400
        
        # Verify code
        if entered_code == buyer_info.delivery_code.upper():
            # Success
            buyer_info.delivery_verified_at = datetime.utcnow()
            buyer_info.status = "delivered"
            db.session.commit()
            
            if request.is_json:
                return jsonify({
                    "success": True,
                    "message": "Delivery verified successfully!"
                })
            else:
                flash("Delivery verified successfully!", "success")
                return redirect(url_for("account.sales_dashboard"))
        else:
            buyer_info.delivery_attempts += 1
            db.session.commit()
            
            return jsonify({
                "success": False,
                "error": f"Invalid delivery code. Attempts: {buyer_info.delivery_attempts}/5"
            }), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": f"Verification failed: {str(e)}"
        }), 500


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