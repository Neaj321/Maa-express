from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    firebase_uid = db.Column(db.String(128), unique=True, nullable=False)

    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(255), unique=True, nullable=False)

    phone_country_code = db.Column(db.String(10), nullable=False)
    phone_number = db.Column(db.String(30), nullable=False)

    is_phone_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    listings_category1 = db.relationship(
        "Category1Listing",
        backref="seller",
        lazy=True,
        foreign_keys="Category1Listing.seller_id",
    )

    def __repr__(self):
        return f"<User {self.email}>"


class Category1Listing(db.Model):
    __tablename__ = "category1_listings"

    id = db.Column(db.Integer, primary_key=True)
    listing_uid = db.Column(db.String(36), unique=True, nullable=False,
                            default=lambda: str(uuid.uuid4()))

    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    service_type = db.Column(db.String(50), nullable=False)
    pickup_delivery_note = db.Column(db.String(500))

    flight_date = db.Column(db.Date, nullable=False)
    flight_number = db.Column(db.String(20), nullable=False)
    airline_name = db.Column(db.String(100), nullable=False)

    origin_country = db.Column(db.String(100), nullable=False)
    origin_airport = db.Column(db.String(150), nullable=False)
    origin_city = db.Column(db.String(100), nullable=False)
    origin_postcode = db.Column(db.String(20), nullable=False)
    origin_contact_name = db.Column(db.String(100), nullable=False)
    origin_phone_country_code = db.Column(db.String(10), nullable=False)
    origin_phone_number = db.Column(db.String(30), nullable=False)

    destination_country = db.Column(db.String(100), nullable=False)
    destination_airport = db.Column(db.String(150), nullable=False)
    destination_city = db.Column(db.String(100), nullable=False)
    destination_postcode = db.Column(db.String(20), nullable=False)
    destination_contact_name = db.Column(db.String(100), nullable=False)
    destination_phone_country_code = db.Column(db.String(10), nullable=False)
    destination_phone_number = db.Column(db.String(30), nullable=False)

    contact_email = db.Column(db.String(255), nullable=False)

    cargo_weight_kg = db.Column(db.Float, nullable=False)
    currency_code = db.Column(db.String(3), nullable=False)
    price_amount = db.Column(db.Float, nullable=False)

    description = db.Column(db.Text, nullable=False,
                            default="write any special requirements")

    ticket_copy_url = db.Column(db.String(500))
    passport_front_url = db.Column(db.String(500))
    passport_back_url = db.Column(db.String(500))

    status = db.Column(db.String(50), nullable=False,
                       default="pending_documents")

    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    parcel_number = db.Column(db.String(50))
    secret_code_handover = db.Column(db.String(10))
    secret_code_delivery = db.Column(db.String(10))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    buyer = db.relationship(
        "User",
        foreign_keys=[buyer_id],
        backref="purchased_category1_listings"
    )

    buyer_info = db.relationship(
        "Category1BuyerInfo",
        backref="listing",
        uselist=False,
        lazy=True
    )

    def __repr__(self):
        return f"<Category1Listing {self.listing_uid}>"


class Category1BuyerInfo(db.Model):
    __tablename__ = "category1_buyer_info"

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("category1_listings.id"),
                           nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    sender_name = db.Column(db.String(100), nullable=False)
    sender_address = db.Column(db.Text, nullable=False)
    sender_phone_country_code = db.Column(db.String(10), nullable=False)
    sender_phone_number = db.Column(db.String(30), nullable=False)
    sender_email = db.Column(db.String(255), nullable=False)

    receiver_name = db.Column(db.String(100), nullable=False)
    receiver_address = db.Column(db.Text, nullable=False)
    receiver_phone_country_code = db.Column(db.String(10), nullable=False)
    receiver_phone_number = db.Column(db.String(30), nullable=False)
    receiver_email = db.Column(db.String(255), nullable=False)

    delivery_country = db.Column(db.String(100), nullable=False)
    delivery_address_box = db.Column(db.Text, nullable=False)

    identity_doc_type = db.Column(db.String(50), nullable=False)
    identity_doc_url = db.Column(db.String(500), nullable=False)

    buyer_phone_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    buyer = db.relationship("User", backref="category1_buyer_infos")


class Category2Listing(db.Model):
    __tablename__ = "category2_listings"

    id = db.Column(db.Integer, primary_key=True)
    listing_uid = db.Column(db.String(36), unique=True, nullable=False,
                            default=lambda: str(uuid.uuid4()))

    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    flight_date = db.Column(db.Date, nullable=False)
    airline_name = db.Column(db.String(100), nullable=False)
    flight_number = db.Column(db.String(20), nullable=False)

    gender = db.Column(db.String(20))
    age_range = db.Column(db.String(20), nullable=False)

    origin_country = db.Column(db.String(100), nullable=False)
    origin_airport = db.Column(db.String(150), nullable=False)
    origin_city = db.Column(db.String(100), nullable=False)
    origin_pickup_address = db.Column(db.Text, nullable=False)

    destination_country = db.Column(db.String(100), nullable=False)
    destination_airport = db.Column(db.String(150), nullable=False)
    destination_city = db.Column(db.String(100), nullable=False)
    destination_dropoff_address = db.Column(db.Text, nullable=False)

    fee_amount = db.Column(db.Float, nullable=False)
    currency_code = db.Column(db.String(3), nullable=False)
    note = db.Column(db.String(500))

    origin_phone_country_code = db.Column(db.String(10), nullable=False)
    origin_phone_number = db.Column(db.String(30), nullable=False)
    destination_phone_country_code = db.Column(db.String(10), nullable=False)
    destination_phone_number = db.Column(db.String(30), nullable=False)

    contact_email = db.Column(db.String(255), nullable=False)

    ticket_copy_url = db.Column(db.String(500))
    passport_front_url = db.Column(db.String(500))
    passport_back_url = db.Column(db.String(500))

    status = db.Column(db.String(50), nullable=False,
                       default="pending_documents")
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)


class Category2BuyerInfo(db.Model):
    __tablename__ = "category2_buyer_info"

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("category2_listings.id"),
                           nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    buyer_phone_country_code = db.Column(db.String(10), nullable=False)
    buyer_phone_number = db.Column(db.String(30), nullable=False)
    buyer_email = db.Column(db.String(255), nullable=False)

    identity_doc_type = db.Column(db.String(50), nullable=False)
    identity_doc_url = db.Column(db.String(500), nullable=False)

    buyer_phone_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Category3Product(db.Model):
    __tablename__ = "category3_products"

    id = db.Column(db.Integer, primary_key=True)
    product_uid = db.Column(db.String(36), unique=True, nullable=False,
                            default=lambda: str(uuid.uuid4()))

    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    main_category = db.Column(db.String(50), nullable=False)
    sub_category = db.Column(db.String(50), nullable=False)

    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

    quantity = db.Column(db.Integer, nullable=False)
    currency_code = db.Column(db.String(3), nullable=False)
    price_amount = db.Column(db.Float, nullable=False)

    status = db.Column(db.String(20), nullable=False, default="active")
    highlight = db.Column(db.Boolean, default=False)
    main_image_url = db.Column(db.String(500))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)


class Category3Order(db.Model):
    __tablename__ = "category3_orders"

    id = db.Column(db.Integer, primary_key=True)
    order_uid = db.Column(db.String(36), unique=True, nullable=False,
                          default=lambda: str(uuid.uuid4()))

    product_id = db.Column(db.Integer, db.ForeignKey("category3_products.id"),
                           nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    currency_code = db.Column(db.String(3), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)

    paypal_order_id = db.Column(db.String(100))
    status = db.Column(db.String(20), nullable=False, default="paid")

    parcel_number = db.Column(db.String(50))
    secret_code_delivery = db.Column(db.String(10))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)


class SiteVisit(db.Model):
    __tablename__ = "site_visits"

    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserLoginLog(db.Model):
    __tablename__ = "user_login_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    login_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="login_logs")
