from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ============================================================================
# USER MODEL
# ============================================================================

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

    # ✅ NEW FIELD: Main verified ID document URL for user
    user_ID = db.Column(db.String(500))  # URL of verified identity document

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
    card_exp_month = db.Column(db.Integer)
    card_exp_year = db.Column(db.Integer)

    # Relationships
    category1_listings = db.relationship('Category1Listing', backref='seller', lazy=True)
    category1_purchases = db.relationship('Category1BuyerInfo', backref='buyer', lazy=True, foreign_keys='Category1BuyerInfo.buyer_id')

    def __repr__(self):
        return f"<User {self.id}: {self.email}>"


# ============================================================================
# CATEGORY 1: LUGGAGE SPACE LISTINGS
# ============================================================================

class Category1Listing(db.Model):
    """In-flight luggage space listings"""
    __tablename__ = "category1_listings"

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Basic Info
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    service_type = db.Column(db.String(255))
    
    # Origin Details
    origin = db.Column(db.String(255))
    origin_airport = db.Column(db.String(255))
    origin_delivery_location = db.Column(db.String(255))
    origin_delivery_postcode = db.Column(db.String(20))
    origin_phone_number = db.Column(db.String(30))
    
    # Destination Details
    destination = db.Column(db.String(255))
    destination_airport = db.Column(db.String(255))
    destination_delivery_location = db.Column(db.String(255))
    destination_delivery_postcode = db.Column(db.String(20))
    destination_phone_number = db.Column(db.String(30))
    
    # Travel Date
    travel_date = db.Column(db.Date)
    
    # Pricing
    currency = db.Column(db.String(10), default='AUD')
    price_per_kg = db.Column(db.Numeric(10, 2))
    total_weight = db.Column(db.Numeric(10, 2))
    discount_percent = db.Column(db.Numeric(5, 2), default=0)
    
    # Document URLs (for admin verification)
    passport_photo_url = db.Column(db.String(500))
    ticket_copy_url = db.Column(db.String(500))
    
    # Status
    admin_status = db.Column(
        db.Enum('pending', 'approved', 'rejected', name="cat1_status_enum"),
        default='pending'
    )
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    buyer_infos = db.relationship('Category1BuyerInfo', backref='listing', lazy=True)

    @property
    def final_price(self):
        """Calculate final price after discount"""
        if self.price_per_kg and self.total_weight:
            subtotal = float(self.price_per_kg) * float(self.total_weight)
            if self.discount_percent:
                discount_amount = subtotal * (float(self.discount_percent) / 100)
                return subtotal - discount_amount
            return subtotal
        return 0.0

    def __repr__(self):
        return f"<Category1Listing {self.id}: {self.origin} → {self.destination}>"


# ============================================================================
# CATEGORY 1: BUYER INFO (PURCHASE DETAILS)
# ============================================================================

class Category1BuyerInfo(db.Model):
    """Purchase/booking details for Category 1 listings"""
    __tablename__ = "category1_buyer_info"

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('category1_listings.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Receiver Details
    receiver_fullname = db.Column(db.String(255))
    receiver_phone = db.Column(db.String(30))
    receiver_email = db.Column(db.String(255))
    delivery_address = db.Column(db.Text)
    delivery_postcode = db.Column(db.String(20))
    delivery_country = db.Column(db.String(255))
    
    # ✅ VERIFICATION CODES (Generated after payment approval)
    handover_code = db.Column(db.String(8), nullable=False)
    delivery_code = db.Column(db.String(8), nullable=False)
    
    # Verification Timestamps
    handover_verified_at = db.Column(db.DateTime)
    delivery_verified_at = db.Column(db.DateTime)
    
    # Verification Attempts (max 5)
    handover_attempts = db.Column(db.Integer, default=0)
    delivery_attempts = db.Column(db.Integer, default=0)
    
    # ✅ PROOF PHOTOS (NEW FIELDS ADDED)
    handover_photo_url = db.Column(db.String(500))  # Photo at handover (origin)
    delivery_photo_url = db.Column(db.String(500))  # Photo at delivery (destination)
    luggage_photo_url = db.Column(db.String(500))   # ✅ NEW: Parcel/luggage photo (uploaded at purchase)
    sender_id_url = db.Column(db.String(500))       # ✅ NEW: Sender ID uploaded at purchase time
    
    # Order Status
    status = db.Column(
        db.Enum('pending_payment', 'payment_failed', 'pending_handover', 'in_transit', 'delivered', 'disputed'),
        default='pending_payment'
    )
    
    # Payment Details
    payment_method = db.Column(
        db.Enum('PAYPAL', 'STRIPE', 'WISE', 'BANK_ACCOUNT', 'MOBILE_BANKING_BKASH_NAGAD', 'PAYID', 'BKASH_TO_BANK')
    )
    payment_status = db.Column(
        db.Enum('pending', 'manual_pay', 'paid', 'failed', 'refunded'),
        nullable=False,
        default='pending'
    )
    payment_transaction_id = db.Column(db.String(255))
    payment_receipt_url = db.Column(db.String(500))
    payment_reference = db.Column(db.String(255))
    
    # Additional Notes
    note = db.Column(db.Text)
    
    # Purchase Details
    purchased_weight = db.Column(db.Numeric(10, 2))
    purchase_price = db.Column(db.Numeric(10, 2))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Category1BuyerInfo {self.id}: Buyer {self.buyer_id} → Listing {self.listing_id}>"


# ============================================================================
# CATEGORY 2: DOCUMENT CARRY SERVICE
# ============================================================================

class Category2Listing(db.Model):
    """Document carry service listings"""
    __tablename__ = "category2_listings"

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    origin = db.Column(db.String(255))
    destination = db.Column(db.String(255))
    travel_date = db.Column(db.Date)
    price = db.Column(db.Numeric(10, 2))
    
    admin_status = db.Column(
        db.Enum('pending', 'approved', 'rejected', name="cat2_status_enum"),
        default='pending'
    )
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Category2Listing {self.id}: {self.origin} → {self.destination}>"


# ============================================================================
# CATEGORY 3: PRODUCTS FOR SALE
# ============================================================================

class Category3Product(db.Model):
    """Products for sale from travelers"""
    __tablename__ = "category3_products"

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    product_name = db.Column(db.String(255))
    product_origin_country = db.Column(db.String(255))
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2))
    currency = db.Column(db.String(10), default='AUD')
    authenticity_proof_url = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    
    admin_status = db.Column(
        db.Enum('pending', 'approved', 'rejected', name="cat3_status_enum"),
        default='pending'
    )
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Category3Product {self.id}: {self.product_name}>"


# ============================================================================
# ANALYTICS & TRACKING MODELS
# ============================================================================

class SiteVisit(db.Model):
    """Track page visits for analytics"""
    __tablename__ = "site_visits"
    
    id = db.Column(db.Integer, primary_key=True)
    page_url = db.Column(db.String(500))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<SiteVisit {self.id}: {self.page_url}>"


class UserLoginLog(db.Model):
    """Track user login history"""
    __tablename__ = "user_login_logs"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<UserLoginLog {self.id}: User {self.user_id} at {self.login_time}>"