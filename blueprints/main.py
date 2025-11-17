from flask import Blueprint, render_template, session, request
from models import Category1Listing, Category2Listing, Category3Product, SiteVisit, User
from datetime import datetime
from sqlalchemy import or_, and_

main_bp = Blueprint("main", __name__)


# Find line ~9-16 (track_visit function):
@main_bp.before_app_request
def track_visit():
    """Track page visits for analytics"""
    try:
        visit = SiteVisit(
            page_url=request.path,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        from models import db
        db.session.add(visit)
        db.session.commit()
    except Exception as e:
        # ✅ ADD ROLLBACK TO PREVENT SESSION ERRORS
        from models import db
        db.session.rollback()
        print(f"⚠️ Failed to track visit: {e}")

@main_bp.app_context_processor
def inject_current_user():
    """Make current user available in all templates"""
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    return dict(current_user=user)


@main_bp.route("/")
def index():
    """
    Homepage with left sidebar filters and all 3 categories
    """
    # Get filter parameters
    category_filter = request.args.get('category', 'category1')
    sort_by = request.args.get('sort', 'newest')
    
    # Category 1 filters
    origin_airport = request.args.get('origin_airport', '').strip().upper()
    destination_airport = request.args.get('destination_airport', '').strip().upper()
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Category 2 filters
    gender = request.args.get('gender', '')
    travel_from = request.args.get('travel_from', '').strip()
    travel_to = request.args.get('travel_to', '').strip()
    travel_date = request.args.get('travel_date', '')
    
    # Category 3 filters
    product_name = request.args.get('product_name', '').strip()
    origin_country = request.args.get('origin_country', '').strip()
    in_stock = request.args.get('in_stock', '')
    
    # Common filters
    max_price = request.args.get('max_price', '')
    min_discount = request.args.get('min_discount', '')
    search_query = request.args.get('q', '').strip()
    
    # ========================================
    # Query Category 1 Listings
    # ========================================
    cat1_query = Category1Listing.query.filter_by(admin_status="approved")
    
    if origin_airport:
        cat1_query = cat1_query.filter(Category1Listing.origin_airport.ilike(f'%{origin_airport}%'))
    if destination_airport:
        cat1_query = cat1_query.filter(Category1Listing.destination_airport.ilike(f'%{destination_airport}%'))
    if date_from:
        cat1_query = cat1_query.filter(Category1Listing.travel_date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    if date_to:
        cat1_query = cat1_query.filter(Category1Listing.travel_date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    if max_price:
        cat1_query = cat1_query.filter(Category1Listing.final_price <= float(max_price))
    if min_discount:
        cat1_query = cat1_query.filter(Category1Listing.discount_percent >= float(min_discount))
    if search_query:
        cat1_query = cat1_query.filter(
            or_(
                Category1Listing.title.ilike(f'%{search_query}%'),
                Category1Listing.origin.ilike(f'%{search_query}%'),
                Category1Listing.destination.ilike(f'%{search_query}%')
            )
        )
    
    # Apply sorting
    if sort_by == 'price_low':
        cat1_query = cat1_query.order_by(Category1Listing.final_price.asc())
    elif sort_by == 'price_high':
        cat1_query = cat1_query.order_by(Category1Listing.final_price.desc())
    elif sort_by == 'discount':
        cat1_query = cat1_query.order_by(Category1Listing.discount_percent.desc())
    else:  # newest
        cat1_query = cat1_query.order_by(Category1Listing.created_at.desc())
    
    category1_listings = cat1_query.all()
    
    # ========================================
    # Query Category 2 Listings
    # ========================================
    cat2_query = Category2Listing.query.filter_by(admin_status="approved")
    
    if gender:
        cat2_query = cat2_query.filter_by(gender=gender)
    if travel_from:
        cat2_query = cat2_query.filter(Category2Listing.travel_from.ilike(f'%{travel_from}%'))
    if travel_to:
        cat2_query = cat2_query.filter(Category2Listing.travel_to.ilike(f'%{travel_to}%'))
    if travel_date:
        cat2_query = cat2_query.filter(Category2Listing.travel_date == datetime.strptime(travel_date, '%Y-%m-%d').date())
    if max_price:
        cat2_query = cat2_query.filter(Category2Listing.final_price <= float(max_price))
    if min_discount:
        cat2_query = cat2_query.filter(Category2Listing.discount_percent >= float(min_discount))
    if search_query:
        cat2_query = cat2_query.filter(
            or_(
                Category2Listing.name.ilike(f'%{search_query}%'),
                Category2Listing.travel_from.ilike(f'%{search_query}%'),
                Category2Listing.travel_to.ilike(f'%{search_query}%')
            )
        )
    
    # Apply sorting
    if sort_by == 'price_low':
        cat2_query = cat2_query.order_by(Category2Listing.final_price.asc())
    elif sort_by == 'price_high':
        cat2_query = cat2_query.order_by(Category2Listing.final_price.desc())
    elif sort_by == 'discount':
        cat2_query = cat2_query.order_by(Category2Listing.discount_percent.desc())
    else:  # newest
        cat2_query = cat2_query.order_by(Category2Listing.created_at.desc())
    
    category2_listings = cat2_query.all()
    
    # ========================================
    # Query Category 3 Products
    # ========================================
    cat3_query = Category3Product.query.filter_by(admin_status="approved")
    
    if product_name:
        cat3_query = cat3_query.filter(Category3Product.product_name.ilike(f'%{product_name}%'))
    if origin_country:
        cat3_query = cat3_query.filter(Category3Product.product_origin_country.ilike(f'%{origin_country}%'))
    if in_stock == 'yes':
        cat3_query = cat3_query.filter(Category3Product.stock > 0)
    if max_price:
        cat3_query = cat3_query.filter(Category3Product.final_price <= float(max_price))
    if min_discount:
        cat3_query = cat3_query.filter(Category3Product.discount_percent >= float(min_discount))
    if search_query:
        cat3_query = cat3_query.filter(
            or_(
                Category3Product.product_name.ilike(f'%{search_query}%'),
                Category3Product.product_origin_country.ilike(f'%{search_query}%')
            )
        )
    
    # Apply sorting
    if sort_by == 'price_low':
        cat3_query = cat3_query.order_by(Category3Product.final_price.asc())
    elif sort_by == 'price_high':
        cat3_query = cat3_query.order_by(Category3Product.final_price.desc())
    elif sort_by == 'discount':
        cat3_query = cat3_query.order_by(Category3Product.discount_percent.desc())
    else:  # newest
        cat3_query = cat3_query.order_by(Category3Product.created_at.desc())
    
    category3_products = cat3_query.all()
    
    return render_template(
        "home.html",
        category1_listings=category1_listings,
        category2_listings=category2_listings,
        category3_products=category3_products
    )


@main_bp.route("/search")
def search():
    """Global search - redirect to index with query params"""
    return redirect(url_for('main.index', **request.args))


@main_bp.route("/page/<template>")
def render_template_name(template):
    """Render static pages"""
    return render_template(template)