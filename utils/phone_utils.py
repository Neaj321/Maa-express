"""
Phone utility functions for Maa Express
Handles phone number masking and viewing permissions
"""

from models import Category1BuyerInfo


def mask_phone_number(phone_number, visible_digits=4):
    """
    Mask a phone number, showing only the last N digits
    
    Args:
        phone_number (str): Full phone number (e.g., "+61412345678")
        visible_digits (int): Number of digits to show at the end (default: 4)
    
    Returns:
        str: Masked phone number (e.g., "+61******5678")
    """
    if not phone_number:
        return "N/A"
    
    phone_str = str(phone_number)
    
    if len(phone_str) <= visible_digits:
        return phone_str
    
    # Keep country code visible (if starts with +)
    if phone_str.startswith('+'):
        # Find where country code ends (usually 2-3 digits after +)
        country_code_end = 3  # Default: +XX
        if len(phone_str) > 4 and phone_str[1:4].isdigit():
            country_code_end = 4  # +XXX
        
        country_code = phone_str[:country_code_end]
        remaining = phone_str[country_code_end:]
        
        if len(remaining) <= visible_digits:
            return phone_str
        
        masked_part = '*' * (len(remaining) - visible_digits)
        visible_part = remaining[-visible_digits:]
        
        return f"{country_code}{masked_part}{visible_part}"
    else:
        # No country code
        masked_part = '*' * (len(phone_str) - visible_digits)
        visible_part = phone_str[-visible_digits:]
        return f"{masked_part}{visible_part}"


def can_view_full_phone(user_id, listing_id):
    """
    Check if a user can view the full phone number for a listing
    
    A user can view full phone numbers if:
    1. They are the listing owner, OR
    2. They have purchased from this listing (Category1BuyerInfo record exists)
    
    Args:
        user_id (int): The user's ID
        listing_id (int): The listing's ID
    
    Returns:
        bool: True if user can view full phone, False otherwise
    """
    from models import Category1Listing
    
    # Check if user is the listing owner
    listing = Category1Listing.query.filter_by(id=listing_id).first()
    if listing and listing.user_id == user_id:
        return True
    
    # Check if user has purchased from this listing
    purchase = Category1BuyerInfo.query.filter_by(
        listing_id=listing_id,
        buyer_id=user_id
    ).first()
    
    return purchase is not None


def format_phone_display(phone_number, user_can_view=False):
    """
    Format phone number for display based on viewing permissions
    
    Args:
        phone_number (str): Full phone number
        user_can_view (bool): Whether user has permission to view full number
    
    Returns:
        str: Formatted phone number (full or masked)
    """
    if not phone_number:
        return "Not provided"
    
    if user_can_view:
        return phone_number
    else:
        return mask_phone_number(phone_number)


def extract_country_code(phone_number):
    """
    Extract country code from E.164 format phone number
    
    Args:
        phone_number (str): Phone number in E.164 format (e.g., "+61412345678")
    
    Returns:
        tuple: (country_code, local_number) e.g., ("+61", "412345678")
    """
    if not phone_number or not phone_number.startswith('+'):
        return ("", phone_number)
    
    # Common country code lengths: 1-3 digits after +
    for length in [4, 3, 2]:  # Try +XXX, +XX, +X
        if len(phone_number) >= length:
            code = phone_number[:length]
            if code[1:].isdigit():
                return (code, phone_number[length:])
    
    return ("+", phone_number[1:])


def validate_phone_format(phone_number):
    """
    Validate phone number format (basic validation)
    
    Args:
        phone_number (str): Phone number to validate
    
    Returns:
        bool: True if format is valid, False otherwise
    """
    if not phone_number:
        return False
    
    phone_str = str(phone_number).strip()
    
    # Check E.164 format: starts with +, followed by digits
    if phone_str.startswith('+'):
        return phone_str[1:].replace(' ', '').isdigit()
    
    # Check if only digits (local format)
    return phone_str.replace(' ', '').isdigit()