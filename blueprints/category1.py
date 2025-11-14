from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from functools import wraps
from datetime import datetime
import re

from models import db, User, Category1Listing, Category1BuyerInfo

category1_bp = Blueprint("category1", __name__, url_prefix="/category1")


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("main.render_template_name", template="login.html"))
        return f(*args, **kwargs)
    return decorated


def phone_verified_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("main.render_template_name", template="login.html"))
        user = User.query.get(session["user_id"])
        if not user or not user.is_active or not user.is_phone_verified:
            return "Phone verification required before creating listings.", 403
        return f(*args, **kwargs)
    return decorated


@category1_bp.route("/new", methods=["GET", "POST"])
@login_required
@phone_verified_required
def new_listing():
    if request.method == "GET":
        return render_template("category1_new_step1.html")

    form = request.form
    note = form.get("pickup_delivery_note", "").strip()
    if re.search(r"[0-9@]", note):
        return "Note cannot contain numbers or emails.", 400
    if len(note.split()) > 100:
        return "Note cannot exceed 100 words.", 400

    flight_date = datetime.strptime(form.get("flight_date"), "%Y-%m-%d").date()

    listing = Category1Listing(
        seller_id=session["user_id"],
        service_type=form.get("service_type"),
        pickup_delivery_note=note,
        flight_date=flight_date,
        flight_number=form.get("flight_number"),
        airline_name=form.get("airline_name"),
        origin_country=form.get("origin_country"),
        origin_airport=form.get("origin_airport"),
        origin_city=form.get("origin_city"),
        origin_postcode=form.get("origin_postcode"),
        origin_contact_name=form.get("origin_contact_name"),
        origin_phone_country_code=form.get("origin_phone_country_code"),
        origin_phone_number=form.get("origin_phone_number"),
        destination_country=form.get("destination_country"),
        destination_airport=form.get("destination_airport"),
        destination_city=form.get("destination_city"),
        destination_postcode=form.get("destination_postcode"),
        destination_contact_name=form.get("destination_contact_name"),
        destination_phone_country_code=form.get("destination_phone_country_code"),
        destination_phone_number=form.get("destination_phone_number"),
        contact_email=form.get("contact_email"),
        cargo_weight_kg=float(form.get("cargo_weight_kg")),
        currency_code=form.get("currency_code"),
        price_amount=float(form.get("price_amount")),
        description=form.get("description") or "write any special requirements",
        status="pending_documents"
    )
    db.session.add(listing)
    db.session.commit()

    return redirect(url_for("category1.upload_docs", listing_uid=listing.listing_uid))


@category1_bp.route("/<listing_uid>/upload-docs", methods=["GET", "POST"])
@login_required
def upload_docs(listing_uid):
    listing = Category1Listing.query.filter_by(
        listing_uid=listing_uid, seller_id=session["user_id"]
    ).first_or_404()

    if request.method == "GET":
        return render_template("category1_new_step2.html", listing=listing)

    data = request.get_json()
    listing.ticket_copy_url = data.get("ticket_copy_url")
    listing.passport_front_url = data.get("passport_front_url")
    listing.passport_back_url = data.get("passport_back_url")
    listing.status = "pending_phone_verification"
    db.session.commit()

    return jsonify({
        "message": "Documents saved. Proceed to phone verification.",
        "next": url_for("category1.verify_phone", listing_uid=listing_uid)
    })


@category1_bp.route("/<listing_uid>/verify-phone", methods=["GET", "POST"])
@login_required
def verify_phone(listing_uid):
    listing = Category1Listing.query.filter_by(
        listing_uid=listing_uid, seller_id=session["user_id"]
    ).first_or_404()

    if request.method == "GET":
        return render_template("category1_new_step3.html", listing=listing)

    listing.status = "pending_admin_review"
    db.session.commit()

    return jsonify({
        "message": (
            "Thank you for choosing Maa Express. Your identity documents are "
            "securely stored in our database and are accessible only to authorized "
            "administrators for verification purposes. We will review your listing "
            "and will publish ASAP."
        )
    })


@category1_bp.route("/view/<listing_uid>")
def detail(listing_uid):
    listing = Category1Listing.query.filter_by(
        listing_uid=listing_uid, status="approved"
    ).first_or_404()
    return render_template("category1_detail.html", listing=listing)


@category1_bp.post("/api/<listing_uid>/purchase")
@login_required
def purchase(listing_uid):
    listing = Category1Listing.query.filter_by(
        listing_uid=listing_uid, status="approved"
    ).first_or_404()

    data = request.get_json()
    order_id = data.get("order_id")

    listing.buyer_id = session["user_id"]
    listing.status = "sold"

    def gen_code(n):
        import random, string
        return ''.join(random.choices(string.digits, k=n))

    listing.parcel_number = gen_code(8)
    listing.secret_code_handover = gen_code(6)
    listing.secret_code_delivery = gen_code(6)

    db.session.commit()

    return jsonify({
        "message": "Order saved",
        "next_url": url_for("category1.buyer_step1", listing_uid=listing_uid)
    })


@category1_bp.route("/buyer/<listing_uid>/step1", methods=["GET", "POST"])
@login_required
def buyer_step1(listing_uid):
    listing = Category1Listing.query.filter_by(
        listing_uid=listing_uid, buyer_id=session["user_id"]
    ).first_or_404()

    if request.method == "GET":
        return render_template("buyer_step1.html", listing=listing)

    data = request.get_json()
    identity_doc_url = data.get("identity_doc_url")
    identity_doc_type = data.get("identity_doc_type")

    sender_name = data.get("sender_name")
    sender_address = data.get("sender_address")
    sender_phone_country_code = data.get("sender_phone_country_code")
    sender_phone_number = data.get("sender_phone_number")
    sender_email = data.get("sender_email")

    receiver_name = data.get("receiver_name")
    receiver_address = data.get("receiver_address")
    receiver_phone_country_code = data.get("receiver_phone_country_code")
    receiver_phone_number = data.get("receiver_phone_number")
    receiver_email = data.get("receiver_email")

    delivery_address_box = data.get("delivery_address_box")
    delivery_country = listing.destination_country

    existing = Category1BuyerInfo.query.filter_by(
        listing_id=listing.id, buyer_id=session["user_id"]
    ).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()

    buyer_info = Category1BuyerInfo(
        listing_id=listing.id,
        buyer_id=session["user_id"],
        sender_name=sender_name,
        sender_address=sender_address,
        sender_phone_country_code=sender_phone_country_code,
        sender_phone_number=sender_phone_number,
        sender_email=sender_email,
        receiver_name=receiver_name,
        receiver_address=receiver_address,
        receiver_phone_country_code=receiver_phone_country_code,
        receiver_phone_number=receiver_phone_number,
        receiver_email=receiver_email,
        delivery_country=delivery_country,
        delivery_address_box=delivery_address_box,
        identity_doc_type=identity_doc_type,
        identity_doc_url=identity_doc_url,
        buyer_phone_verified=False
    )
    db.session.add(buyer_info)
    db.session.commit()

    return jsonify({
        "message": (
            "Thank you for choosing Maa Express. Your identity documents "
            "are securely stored in our database and are accessible only to "
            "authorized administrators for verification purposes."
        ),
        "next_url": url_for("category1.buyer_codes", listing_uid=listing_uid)
    })


@category1_bp.route("/buyer/<listing_uid>/codes", methods=["GET"])
@login_required
def buyer_codes(listing_uid):
    listing = Category1Listing.query.filter_by(
        listing_uid=listing_uid, buyer_id=session["user_id"]
    ).first_or_404()
    buyer_info = Category1BuyerInfo.query.filter_by(
        listing_id=listing.id, buyer_id=session["user_id"]
    ).first()
    return render_template("buyer_codes.html", listing=listing, buyer_info=buyer_info)


@category1_bp.post("/api/buyer/<listing_uid>/verify-phone")
@login_required
def buyer_verify_phone(listing_uid):
    listing = Category1Listing.query.filter_by(
        listing_uid=listing_uid, buyer_id=session["user_id"]
    ).first_or_404()
    buyer_info = Category1BuyerInfo.query.filter_by(
        listing_id=listing.id, buyer_id=session["user_id"]
    ).first_or_404()

    buyer_info.buyer_phone_verified = True
    db.session.commit()

    seller = listing.seller

    return jsonify({
        "parcel_number": listing.parcel_number,
        "secret_code_handover": listing.secret_code_handover,
        "secret_code_delivery": listing.secret_code_delivery,
        "seller_origin_phone": f"{listing.origin_phone_country_code} {listing.origin_phone_number}",
        "seller_destination_phone": f"{listing.destination_phone_country_code} {listing.destination_phone_number}",
        "seller_email": seller.email
    })
