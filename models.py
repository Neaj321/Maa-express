from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Computed
from datetime import datetime
from decimal import Decimal

db = SQLAlchemy()


class User(db.Model):
    """User accounts with authentication and payout details"""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(30))
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    phone_verified = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(32), default="user")

    # Payout Details
    payout_method_type = db.Column(db.String(20), default='none')
    bank_account_name = db.Column(db.String(100))
    bank_name = db.Column(db.String(100))
    bank_bsb_or_routing = db.Column(db.String(50))
    bank_account_number = db.Column(db.String(50))
    mobile_banking_number = db.Column(db.String(50))
    payid_identifier = db.Column(db.String(100))
    card_holder_name = db.Column(db.String(100))
    card_brand = db.Column(db.String(50))
    card_last4 = db.Column(db.String(4))
    card_exp_month = db.Column(db.SmallInteger)
    card_exp_year = db.Column(db.SmallInteger)

    def __repr__(self):
        return f"<User {self.email}>"


class Category1Listing(db.Model):
    """
    Category 1 - Luggage Space Listings
    ✅ Updated: Airport names instead of codes, service_type field added
    """
    __tablename__ = "category1_listings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # ✅ Service Type Selection
    service_type = db.Column(db.String(255), nullable=False)
    
    # Two separate phone fields
    origin_phone_number = db.Column(db.String(30))
    destination_phone_number = db.Column(db.String(30))

    # ✅ UPDATED: Airport names instead of codes
    origin = db.Column(db.String(255), nullable=False)
    origin_airport = db.Column(db.String(255), nullable=False)  # ✅ Changed from String(10) to String(255)
    origin_delivery_location = db.Column(db.String(255))
    origin_delivery_postcode = db.Column(db.String(20))

    destination = db.Column(db.String(255), nullable=False)
    destination_airport = db.Column(db.String(255), nullable=False)  # ✅ Changed from String(10) to String(255)
    destination_delivery_location = db.Column(db.String(255))
    destination_delivery_postcode = db.Column(db.String(20))

    travel_date = db.Column(db.Date, nullable=False)

    # Currency field (3-letter ISO code)
    currency = db.Column(db.String(3), nullable=False, default='AUD')
    
    # Pricing fields
    price_per_kg = db.Column(db.Numeric(10, 2))
    total_weight = db.Column(db.Numeric(10, 2))
    
    # ✅ GENERATED COLUMNS - Marked as Computed (read-only)
    base_price = db.Column(
        db.Numeric(10, 2),
        Computed("(price_per_kg * total_weight)"),
        nullable=True
    )
    
    discount_percent = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    
    final_price = db.Column(
        db.Numeric(10, 2),
        Computed("(price_per_kg * total_weight) - ((price_per_kg * total_weight) * discount_percent / 100)"),
        nullable=True
    )

    passport_photo_url = db.Column(db.String(500))
    ticket_copy_url = db.Column(db.String(500))

    admin_status = db.Column(db.String(20), default='pending')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref="category1_listings")
    buyer_infos = db.relationship("Category1BuyerInfo", backref="listing", lazy=True)

    def __repr__(self):
        return f"<Category1Listing {self.title}>"


class Category2Listing(db.Model):
    """Category 2 - Travel Companion Listings"""
    __tablename__ = "category2_listings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    gender = db.Column(db.String(20), nullable=False)

    travel_from = db.Column(db.String(255))
    travel_to = db.Column(db.String(255))
    travel_date = db.Column(db.Date)

    price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_percent = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    final_price = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))

    image_url = db.Column(db.String(500))

    admin_status = db.Column(db.String(20), default='pending')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref="category2_listings")
    buyer_infos = db.relationship("Category2BuyerInfo", backref="listing", lazy=True)


class Category3Product(db.Model):
    """Category 3 - Authentic Products"""
    __tablename__ = "category3_products"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    product_name = db.Column(db.String(255), nullable=False)
    product_origin_country = db.Column(db.String(255))
    description = db.Column(db.Text)

    price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_percent = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    final_price = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))

    authenticity_proof_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))

    admin_status = db.Column(db.String(20), default='pending')

    stock = db.Column(db.Integer, default=1)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref="category3_products")
    orders = db.relationship("Category3Order", backref="product", lazy=True)


class Category1BuyerInfo(db.Model):
    """Stores buyer purchase information for Category 1 listings"""
    __tablename__ = "category1_buyer_info"

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("category1_listings.id"), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    receiver_fullname = db.Column(db.String(255))
    receiver_phone = db.Column(db.String(30))
    receiver_email = db.Column(db.String(255))

    delivery_address = db.Column(db.Text)
    delivery_postcode = db.Column(db.String(20))
    delivery_country = db.Column(db.String(255))
    
    note = db.Column(db.Text)
    
    # ✅ Payment tracking
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, failed, refunded

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    buyer = db.relationship("User", backref="category1_purchases")


class Category2BuyerInfo(db.Model):
    """Stores buyer contact information for Category 2 listings"""
    __tablename__ = "category2_buyer_info"

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("category2_listings.id"), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    full_name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(255), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    buyer = db.relationship("User", backref="category2_purchases")


class Category3Order(db.Model):
    """Stores orders for Category 3 products with buyer delivery details"""
    __tablename__ = "category3_orders"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("category3_products.id"), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    quantity = db.Column(db.Integer, default=1)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)

    buyer_fullname = db.Column(db.String(255))
    buyer_phone = db.Column(db.String(30))
    buyer_email = db.Column(db.String(255))

    delivery_country = db.Column(db.String(255))
    delivery_address = db.Column(db.Text)
    delivery_postcode = db.Column(db.String(255))

    admin_status = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    buyer = db.relationship("User", backref="category3_purchases")


class UserLoginLog(db.Model):
    """Tracks user login events for security and analytics"""
    __tablename__ = "user_login_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))

    user = db.relationship("User", backref="login_logs")


class SiteVisit(db.Model):
    """Tracks page visits for analytics"""
    __tablename__ = "site_visits"

    id = db.Column(db.Integer, primary_key=True)
    page_url = db.Column(db.String(500))
    visited_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))