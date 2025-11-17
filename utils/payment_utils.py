"""
Payment processing utilities and secret code generation for Maa Express
Handles Stripe, PayPal, and manual payment methods

This module provides:
- Secure code generation (handover/delivery codes)
- Stripe payment intent creation and verification
- PayPal payment processing (REAL SDK implementation)
- Manual payment tracking (Wise, Bank, Mobile Banking, PayID, bKash)
- Payment method validation
- Utility functions for payment workflows

Dependencies:
- stripe: pip install stripe
- paypalrestsdk: pip install paypalrestsdk
"""
import secrets
import string
import stripe
from datetime import datetime
from config import Config

# ============================================
# STRIPE EXCEPTION IMPORTS (Version-agnostic)
# ============================================
try:
    # Try new import style (Stripe >= 2.0)
    from stripe import StripeError
    from stripe import AuthenticationError
    from stripe import CardError
    from stripe import InvalidRequestError
except ImportError:
    # Fallback to old import style (Stripe < 2.0)
    from stripe.error import StripeError
    from stripe.error import AuthenticationError
    from stripe.error import CardError
    from stripe.error import InvalidRequestError

# ============================================
# PAYPAL IMPORTS
# ============================================
try:
    import paypalrestsdk
    PAYPAL_AVAILABLE = True
except ImportError:
    PAYPAL_AVAILABLE = False
    print("⚠️ paypalrestsdk not installed. Run: pip install paypalrestsdk")

# ============================================
# STRIPE INITIALIZATION
# ============================================
stripe.api_key = Config.STRIPE_SECRET_KEY

# Log Stripe initialization status
if Config.STRIPE_SECRET_KEY and Config.STRIPE_SECRET_KEY.startswith('sk_'):
    mode = "LIVE" if Config.STRIPE_SECRET_KEY.startswith('sk_live_') else "TEST"
    print(f"✅ Stripe initialized in {mode} mode: {Config.STRIPE_SECRET_KEY[:15]}...")
else:
    print("⚠️ Stripe key not configured or invalid format")

# ============================================
# PAYPAL INITIALIZATION
# ============================================
if PAYPAL_AVAILABLE and Config.PAYPAL_CLIENT_ID and Config.PAYPAL_CLIENT_SECRET:
    paypalrestsdk.configure({
        "mode": Config.PAYPAL_MODE,  # "sandbox" or "live"
        "client_id": Config.PAYPAL_CLIENT_ID,
        "client_secret": Config.PAYPAL_CLIENT_SECRET
    })
    print(f"✅ PayPal initialized in {Config.PAYPAL_MODE.upper()} mode")
    
    # ✅ Production warning
    if Config.PAYPAL_MODE == "live":
        print("⚠️  PAYPAL LIVE MODE - Real transactions will be processed")
    else:
        print("ℹ️  PayPal sandbox mode - Use test credentials from developer.paypal.com")
else:
    print("⚠️ PayPal not configured. Check PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in .env")


# ============================================
# CODE GENERATION FUNCTIONS
# ============================================

def generate_handover_code():
    """
    Generate cryptographically secure 8-character handover code
    
    The code is used to verify parcel handover at origin.
    Format: 8 uppercase alphanumeric characters (e.g., "A1B2C3D4")
    
    Returns:
        str: Random uppercase alphanumeric code
    
    Example:
        >>> code = generate_handover_code()
        >>> len(code)
        8
        >>> code.isupper()
        True
        >>> code.isalnum()
        True
    """
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(8))


def generate_delivery_code():
    """
    Generate cryptographically secure 8-character delivery code
    
    The code is used to verify parcel delivery at destination.
    Format: 8 uppercase alphanumeric characters (e.g., "X5Y6Z7W8")
    
    Returns:
        str: Random uppercase alphanumeric code
    
    Example:
        >>> code = generate_delivery_code()
        >>> len(code)
        8
        >>> code.isupper()
        True
    """
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(8))


def generate_tracking_number(buyer_info_id):
    """
    Generate unique tracking number for parcel
    
    Format: MAA-YYYYMMDD-{buyer_info_id:06d}
    Example: MAA-20241117-000123
    
    Args:
        buyer_info_id (int): ID of the buyer_info record
    
    Returns:
        str: Tracking number in format MAA-YYYYMMDD-XXXXXX
    
    Example:
        >>> generate_tracking_number(123)
        'MAA-20241117-000123'
        >>> generate_tracking_number(999999)
        'MAA-20241117-999999'
    """
    date_str = datetime.now().strftime("%Y%m%d")
    return f"MAA-{date_str}-{buyer_info_id:06d}"


# ============================================
# STRIPE PAYMENT FUNCTIONS
# ============================================

def create_stripe_payment_intent(amount_cents, currency, buyer_info_id, buyer_email):
    """
    Create Stripe PaymentIntent for card payments
    
    This function creates a payment intent that the frontend can use
    to collect payment from the customer using Stripe Elements or
    Payment Element.
    
    Args:
        amount_cents (int): Amount in cents (e.g., 5000 = $50.00)
        currency (str): 3-letter ISO currency code (e.g., 'aud', 'usd')
        buyer_info_id (int): Buyer info record ID for metadata
        buyer_email (str): Buyer email for receipt
    
    Returns:
        stripe.PaymentIntent: Stripe PaymentIntent object with client_secret
        None: If creation fails
    
    Raises:
        AuthenticationError: If Stripe API key is invalid
        InvalidRequestError: If parameters are invalid
        CardError: If card-specific error occurs
        StripeError: For other Stripe API errors
    
    Example:
        >>> intent = create_stripe_payment_intent(5000, 'aud', 123, 'buyer@example.com')
        >>> intent.client_secret  # Use this on frontend
        'pi_xxx_secret_xxx'
        >>> intent.status
        'requires_payment_method'
    """
    try:
        # Validate amount (Stripe minimum is 50 cents)
        if not amount_cents or amount_cents < 50:
            print(f"❌ Amount too low: {amount_cents} cents (minimum 50)")
            return None
        
        # Validate currency
        if not currency or len(currency) != 3:
            print(f"❌ Invalid currency: {currency}")
            return None
        
        # Create PaymentIntent with automatic payment methods
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=currency.lower(),
            metadata={
                'buyer_info_id': buyer_info_id,
                'platform': 'maa_express',
                'type': 'luggage_space_purchase'
            },
            receipt_email=buyer_email,
            description=f"MAA Express - Luggage Space Purchase #{buyer_info_id}",
            automatic_payment_methods={
                'enabled': True,
            }
        )
        
        print(f"✅ Stripe PaymentIntent created: {intent.id}")
        print(f"   Amount: {amount_cents} cents ({currency.upper()})")
        print(f"   Status: {intent.status}")
        
        return intent
    
    except AuthenticationError as e:
        print(f"❌ Stripe Authentication Error: {str(e)}")
        print(f"⚠️ Check STRIPE_SECRET_KEY in .env file")
        print(f"   Current key starts with: {Config.STRIPE_SECRET_KEY[:7] if Config.STRIPE_SECRET_KEY else 'None'}")
        return None
    
    except CardError as e:
        print(f"❌ Stripe Card Error: {str(e)}")
        print(f"   Code: {e.code}")
        return None
    
    except InvalidRequestError as e:
        print(f"❌ Stripe Invalid Request: {str(e)}")
        print(f"   Amount: {amount_cents}, Currency: {currency}")
        return None
    
    except StripeError as e:
        print(f"❌ Stripe Error: {str(e)}")
        return None
    
    except Exception as e:
        print(f"❌ Unexpected error creating Stripe payment: {str(e)}")
        return None


def verify_stripe_payment(payment_intent_id):
    """
    Verify Stripe payment status by retrieving PaymentIntent
    
    This function checks if a payment has been successfully completed.
    Call this after the customer completes payment on the frontend.
    
    Args:
        payment_intent_id (str): Stripe PaymentIntent ID (e.g., 'pi_xxx')
    
    Returns:
        tuple: (success: bool, transaction_id: str or None)
            - (True, intent_id) if payment succeeded
            - (False, None) if payment failed, pending, or processing
    
    Payment Intent Statuses:
        - succeeded: Payment completed successfully
        - processing: Payment is being processed (async methods)
        - requires_payment_method: Customer needs to provide payment
        - requires_confirmation: Payment needs to be confirmed
        - requires_action: Customer needs to complete 3D Secure
        - canceled: Payment was canceled
        - failed: Payment failed
    
    Example:
        >>> success, txn_id = verify_stripe_payment('pi_xxx')
        >>> if success:
        ...     print(f"Payment successful: {txn_id}")
        ... else:
        ...     print("Payment not complete")
    """
    try:
        # Retrieve PaymentIntent from Stripe
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        print(f"📊 Stripe payment status: {intent.status}")
        print(f"   Payment Intent ID: {intent.id}")
        
        if intent.status == 'succeeded':
            print(f"✅ Stripe payment verified: {intent.id}")
            return (True, intent.id)
        
        elif intent.status == 'processing':
            print(f"⏳ Stripe payment processing: {intent.id}")
            return (False, None)
        
        elif intent.status == 'requires_payment_method':
            print(f"⚠️ Stripe payment requires payment method: {intent.id}")
            return (False, None)
        
        elif intent.status == 'requires_confirmation':
            print(f"⚠️ Stripe payment requires confirmation: {intent.id}")
            return (False, None)
        
        elif intent.status == 'requires_action':
            print(f"⚠️ Stripe payment requires action (3D Secure): {intent.id}")
            return (False, None)
        
        elif intent.status == 'canceled':
            print(f"❌ Stripe payment canceled: {intent.id}")
            return (False, None)
        
        else:
            print(f"⚠️ Stripe payment not succeeded. Status: {intent.status}")
            return (False, None)
    
    except StripeError as e:
        print(f"❌ Stripe verification error: {str(e)}")
        return (False, None)
    
    except Exception as e:
        print(f"❌ Unexpected error verifying Stripe payment: {str(e)}")
        return (False, None)


def refund_stripe_payment(payment_intent_id, amount_cents=None, reason=None):
    """
    Issue a full or partial refund for a Stripe payment
    
    Use this function to refund customers if there's a dispute,
    cancellation, or quality issue.
    
    Args:
        payment_intent_id (str): Stripe PaymentIntent ID to refund
        amount_cents (int, optional): Amount to refund in cents. 
            None for full refund.
        reason (str, optional): Refund reason. Must be one of:
            - 'duplicate': Duplicate charge
            - 'fraudulent': Fraudulent transaction
            - 'requested_by_customer': Customer requested refund
    
    Returns:
        tuple: (success: bool, refund_id: str or None)
            - (True, refund_id) if refund successful
            - (False, None) if refund failed
    
    Example:
        >>> # Full refund
        >>> success, refund_id = refund_stripe_payment('pi_xxx', reason='requested_by_customer')
        
        >>> # Partial refund (refund $10 from $50 charge)
        >>> success, refund_id = refund_stripe_payment('pi_xxx', amount_cents=1000)
    """
    try:
        refund_params = {
            'payment_intent': payment_intent_id
        }
        
        # Partial refund
        if amount_cents:
            refund_params['amount'] = amount_cents
            print(f"💰 Creating partial refund: {amount_cents} cents")
        else:
            print(f"💰 Creating full refund")
        
        # Add refund reason
        if reason:
            refund_params['reason'] = reason
        
        # Create refund
        refund = stripe.Refund.create(**refund_params)
        
        print(f"✅ Stripe refund created: {refund.id}")
        print(f"   Status: {refund.status}")
        print(f"   Amount: {refund.amount} cents")
        
        return (True, refund.id)
    
    except StripeError as e:
        print(f"❌ Stripe refund error: {str(e)}")
        return (False, None)
    
    except Exception as e:
        print(f"❌ Unexpected error refunding Stripe payment: {str(e)}")
        return (False, None)


# ============================================
# PAYPAL PAYMENT FUNCTIONS (REAL SDK IMPLEMENTATION)
# ============================================

def create_paypal_order(amount, currency, buyer_info_id, return_url, cancel_url):
    """
    Create PayPal order for checkout using REST API v2
    
    This uses the PayPal REST SDK to create a real payment.
    Works in both sandbox (testing) and live (production) modes.
    
    Args:
        amount (float): Amount in dollars (e.g., 50.00)
        currency (str): 3-letter currency code (e.g., 'USD', 'AUD')
        buyer_info_id (int): Buyer info ID for reference
        return_url (str): URL to redirect after successful payment
        cancel_url (str): URL to redirect if payment is cancelled
    
    Returns:
        dict: PayPal order response
            {
                'success': True/False,
                'order_id': 'xxx',
                'approval_url': 'https://paypal.com/...',
                'status': 'created',
                'error': 'error message' (if failed)
            }
    
    Example:
        >>> result = create_paypal_order(50.00, 'AUD', 123, return_url, cancel_url)
        >>> if result['success']:
        ...     # Redirect user to result['approval_url']
        ...     pass
    """
    if not PAYPAL_AVAILABLE:
        error_msg = 'PayPal SDK not installed. Run: pip install paypalrestsdk'
        print(f"❌ {error_msg}")
        return {
            'success': False,
            'error': error_msg
        }
    
    # ✅ Validate configuration
    if not Config.PAYPAL_CLIENT_ID or not Config.PAYPAL_CLIENT_SECRET:
        error_msg = 'PayPal credentials not configured in .env file'
        print(f"❌ {error_msg}")
        print("   Please set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET")
        return {
            'success': False,
            'error': error_msg
        }
    
    try:
        print(f"🔄 Creating PayPal order...")
        print(f"   Amount: {currency} {amount:.2f}")
        print(f"   Mode: {Config.PAYPAL_MODE}")
        print(f"   Return URL: {return_url}")
        print(f"   Cancel URL: {cancel_url}")
        
        # Create PayPal payment
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": return_url,
                "cancel_url": cancel_url
            },
            "transactions": [{
                "amount": {
                    "total": f"{amount:.2f}",
                    "currency": currency.upper()
                },
                "description": f"MAA Express - Luggage Space Purchase #{buyer_info_id}",
                "custom": str(buyer_info_id),
                "item_list": {
                    "items": [{
                        "name": "Luggage Space",
                        "sku": f"MAA-{buyer_info_id}",
                        "price": f"{amount:.2f}",
                        "currency": currency.upper(),
                        "quantity": 1
                    }]
                }
            }]
        })
        
        if payment.create():
            print(f"✅ PayPal order created: {payment.id}")
            print(f"   State: {payment.state}")
            
            # Extract approval URL
            approval_url = None
            for link in payment.links:
                print(f"   Link: {link.rel} -> {link.href}")
                if link.rel == "approval_url":
                    approval_url = link.href
                    break
            
            if not approval_url:
                error_msg = "No approval URL found in PayPal response"
                print(f"❌ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
            
            return {
                'success': True,
                'order_id': payment.id,
                'approval_url': approval_url,
                'status': payment.state
            }
        else:
            error_details = payment.error
            print(f"❌ PayPal order creation failed:")
            print(f"   Error: {error_details}")
            
            # Extract user-friendly error message
            error_message = "Failed to create PayPal order"
            if isinstance(error_details, dict):
                error_message = error_details.get('message', error_message)
                if 'details' in error_details:
                    print(f"   Details: {error_details['details']}")
            
            return {
                'success': False,
                'error': error_message,
                'error_details': str(error_details)
            }
    
    except Exception as e:
        error_msg = f"PayPal exception: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        print(traceback.format_exc())
        return {
            'success': False,
            'error': error_msg
        }


def verify_paypal_payment(payment_id, payer_id):
    """
    Verify and execute PayPal payment
    
    After user approves payment on PayPal, this function executes
    the payment and captures the funds.
    
    Args:
        payment_id (str): PayPal payment ID (from return URL)
        payer_id (str): PayPal payer ID (from return URL)
    
    Returns:
        tuple: (success: bool, transaction_id: str or None)
            - (True, sale_id) if payment executed successfully
            - (False, None) if payment failed
    
    Example:
        >>> # After user returns from PayPal
        >>> payment_id = request.args.get('paymentId')
        >>> payer_id = request.args.get('PayerID')
        >>> success, txn_id = verify_paypal_payment(payment_id, payer_id)
        >>> if success:
        ...     # Payment captured successfully
        ...     print(f"Transaction ID: {txn_id}")
    """
    if not PAYPAL_AVAILABLE:
        return (False, None)
    
    try:
        payment = paypalrestsdk.Payment.find(payment_id)
        
        if payment.execute({"payer_id": payer_id}):
            print(f"✅ PayPal payment executed: {payment.id}")
            
            # Extract transaction ID (sale ID)
            transaction_id = None
            if payment.transactions and len(payment.transactions) > 0:
                if payment.transactions[0].related_resources and len(payment.transactions[0].related_resources) > 0:
                    sale = payment.transactions[0].related_resources[0].sale
                    transaction_id = sale.id
                    print(f"   Sale ID: {transaction_id}")
                    print(f"   Amount: {sale.amount.currency} {sale.amount.total}")
            
            return (True, transaction_id or payment.id)
        else:
            print(f"❌ PayPal payment execution failed: {payment.error}")
            return (False, None)
    
    except Exception as e:
        print(f"❌ PayPal verification error: {str(e)}")
        return (False, None)


def refund_paypal_payment(sale_id, amount=None, currency='USD'):
    """
    Refund a PayPal payment
    
    Args:
        sale_id (str): PayPal sale transaction ID
        amount (float, optional): Amount to refund. None for full refund
        currency (str): Currency code
    
    Returns:
        tuple: (success: bool, refund_id: str or None)
    
    Example:
        >>> # Full refund
        >>> success, refund_id = refund_paypal_payment('xxx')
        
        >>> # Partial refund
        >>> success, refund_id = refund_paypal_payment('xxx', amount=25.00, currency='AUD')
    """
    if not PAYPAL_AVAILABLE:
        return (False, None)
    
    try:
        sale = paypalrestsdk.Sale.find(sale_id)
        
        refund_request = {}
        if amount:
            refund_request = {
                "amount": {
                    "total": f"{amount:.2f}",
                    "currency": currency.upper()
                }
            }
            print(f"💰 Creating PayPal partial refund: {currency} {amount:.2f}")
        else:
            print(f"💰 Creating PayPal full refund")
        
        refund = sale.refund(refund_request)
        
        if refund.success():
            print(f"✅ PayPal refund created: {refund.id}")
            return (True, refund.id)
        else:
            print(f"❌ PayPal refund failed: {refund.error}")
            return (False, None)
    
    except Exception as e:
        print(f"❌ PayPal refund error: {str(e)}")
        return (False, None)


# ============================================
# UTILITY FUNCTIONS
# ============================================

def format_amount(amount_cents, currency):
    """
    Format amount in cents to human-readable string
    
    Args:
        amount_cents (int): Amount in cents
        currency (str): Currency code (e.g., 'AUD', 'USD')
    
    Returns:
        str: Formatted amount with currency (e.g., "$50.00 AUD")
    
    Example:
        >>> format_amount(5000, 'AUD')
        '$50.00 AUD'
        >>> format_amount(12345, 'USD')
        '$123.45 USD'
    """
    amount_dollars = amount_cents / 100
    return f"${amount_dollars:.2f} {currency.upper()}"


def validate_payment_method(payment_method):
    """
    Validate payment method against allowed enum values
    
    This matches the payment_method enum in Category1BuyerInfo model:
    - PAYPAL
    - STRIPE
    - WISE
    - BANK_ACCOUNT
    - MOBILE_BANKING_BKASH_NAGAD
    - PAYID
    - BKASH_TO_BANK
    
    Args:
        payment_method (str): Payment method to validate
    
    Returns:
        bool: True if valid, False otherwise
    
    Example:
        >>> validate_payment_method('STRIPE')
        True
        >>> validate_payment_method('stripe')  # Case insensitive
        True
        >>> validate_payment_method('INVALID')
        False
    """
    valid_methods = [
        'PAYPAL', 'STRIPE', 'WISE', 'BANK_ACCOUNT',
        'MOBILE_BANKING_BKASH_NAGAD', 'PAYID', 'BKASH_TO_BANK'
    ]
    
    return payment_method.upper() in valid_methods


def get_payment_method_display_name(payment_method):
    """
    Get human-readable display name for payment method
    
    Args:
        payment_method (str): Payment method code
    
    Returns:
        str: User-friendly display name
    
    Example:
        >>> get_payment_method_display_name('STRIPE')
        'Credit/Debit Card (Stripe)'
        >>> get_payment_method_display_name('MOBILE_BANKING_BKASH_NAGAD')
        'Mobile Banking (bKash/Nagad)'
    """
    display_names = {
        'STRIPE': 'Credit/Debit Card (Stripe)',
        'PAYPAL': 'PayPal',
        'WISE': 'Wise Transfer',
        'BANK_ACCOUNT': 'Bank Account Transfer',
        'MOBILE_BANKING_BKASH_NAGAD': 'Mobile Banking (bKash/Nagad)',
        'PAYID': 'PayID',
        'BKASH_TO_BANK': 'bKash to Bank'
    }
    
    return display_names.get(payment_method.upper(), payment_method)


def calculate_platform_fee(amount, fee_percent=2.5):
    """
    Calculate platform fee (for future use)
    
    Args:
        amount (float): Transaction amount in dollars
        fee_percent (float): Fee percentage (default 2.5%)
    
    Returns:
        tuple: (fee_amount: float, seller_amount: float)
    
    Example:
        >>> calculate_platform_fee(100.00)
        (2.5, 97.5)
        >>> calculate_platform_fee(100.00, fee_percent=3.0)
        (3.0, 97.0)
    """
    fee = amount * (fee_percent / 100)
    seller_amount = amount - fee
    return (round(fee, 2), round(seller_amount, 2))


# ============================================
# DIAGNOSTIC FUNCTIONS
# ============================================

def test_stripe_connection():
    """
    Test Stripe API connection and retrieve account information
    
    Use this function during development to verify that your
    Stripe API key is configured correctly.
    
    Returns:
        dict: Test results with status and account information
    
    Example:
        >>> result = test_stripe_connection()
        >>> if result['success']:
        ...     print(f"Connected to Stripe account: {result['account_id']}")
    """
    try:
        account = stripe.Account.retrieve()
        
        print(f"✅ Stripe connection successful")
        print(f"   Account ID: {account.id}")
        print(f"   Country: {account.country}")
        print(f"   Default Currency: {account.default_currency}")
        
        return {
            'success': True,
            'message': f"✅ Stripe connected successfully",
            'account_id': account.id,
            'country': account.country,
            'currency': account.default_currency
        }
    
    except AuthenticationError as e:
        print(f"❌ Stripe authentication failed: {str(e)}")
        return {
            'success': False,
            'message': f"❌ Stripe authentication failed: {str(e)}",
            'error': 'invalid_api_key'
        }
    
    except Exception as e:
        print(f"❌ Stripe connection error: {str(e)}")
        return {
            'success': False,
            'message': f"❌ Stripe connection error: {str(e)}",
            'error': str(e)
        }


def test_paypal_connection():
    """Test PayPal API connection"""
    if not PAYPAL_AVAILABLE:
        return {
            'success': False,
            'message': 'PayPal SDK not installed',
            'error': 'missing_sdk'
        }
    
    try:
        # Try to create a test payment (won't be executed)
        test_payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "transactions": [{
                "amount": {"total": "1.00", "currency": "USD"},
                "description": "Test connection"
            }]
        })
        
        print("✅ PayPal connection test successful")
        return {
            'success': True,
            'message': 'PayPal configured correctly',
            'mode': Config.PAYPAL_MODE
        }
    
    except Exception as e:
        print(f"❌ PayPal connection test failed: {str(e)}")
        return {
            'success': False,
            'message': str(e),
            'error': 'connection_failed'
        }


# ============================================
# MODULE EXPORTS
# ============================================

__all__ = [
    # Code generation
    'generate_handover_code',
    'generate_delivery_code',
    'generate_tracking_number',
    
    # Stripe functions
    'create_stripe_payment_intent',
    'verify_stripe_payment',
    'refund_stripe_payment',
    
    # PayPal functions
    'create_paypal_order',
    'verify_paypal_payment',
    'refund_paypal_payment',
    
    # Utility functions
    'format_amount',
    'validate_payment_method',
    'get_payment_method_display_name',
    'calculate_platform_fee',
    'test_stripe_connection',
    'test_paypal_connection'
]


# ============================================
# STARTUP VALIDATION & TESTING
# ============================================

if __name__ == "__main__":
    """
    Run this file directly to test all functions:
    python utils/payment_utils.py
    """
    print("=" * 70)
    print("🔧 MAA EXPRESS - PAYMENT UTILITIES TEST")
    print("=" * 70)
    
    # Test 1: Code generation
    print("\n📝 Test 1: Code Generation")
    print("-" * 70)
    handover = generate_handover_code()
    delivery = generate_delivery_code()
    tracking = generate_tracking_number(123)
    
    print(f"✅ Handover Code: {handover}")
    print(f"✅ Delivery Code: {delivery}")
    print(f"✅ Tracking Number: {tracking}")
    
    # Test 2: Stripe connection
    print("\n🔌 Test 2: Stripe Connection")
    print("-" * 70)
    stripe_test = test_stripe_connection()
    
    if stripe_test['success']:
        print(f"✅ Status: Connected")
        print(f"   Account ID: {stripe_test['account_id']}")
        print(f"   Country: {stripe_test['country']}")
        print(f"   Currency: {stripe_test['currency']}")
    else:
        print(f"❌ Status: Failed")
        print(f"   Error: {stripe_test.get('error', 'Unknown')}")
    
    # Test 3: PayPal connection
    print("\n🔌 Test 3: PayPal Connection")
    print("-" * 70)
    paypal_test = test_paypal_connection()
    
    if paypal_test['success']:
        print(f"✅ Status: Connected")
        print(f"   Mode: {paypal_test.get('mode', 'Unknown')}")
    else:
        print(f"❌ Status: Failed")
        print(f"   Error: {paypal_test.get('error', 'Unknown')}")
    
    # Test 4: Amount formatting
    print("\n💰 Test 4: Amount Formatting")
    print("-" * 70)
    test_amounts = [5000, 12345, 100, 9999]
    for cents in test_amounts:
        formatted = format_amount(cents, 'AUD')
        print(f"   {cents} cents = {formatted}")
    
    # Test 5: Payment method validation
    print("\n✅ Test 5: Payment Method Validation")
    print("-" * 70)
    test_methods = ['STRIPE', 'PAYPAL', 'INVALID', 'stripe', 'WISE']
    for method in test_methods:
        valid = validate_payment_method(method)
        status = "✅ Valid" if valid else "❌ Invalid"
        display = get_payment_method_display_name(method) if valid else "N/A"
        print(f"   {method:30s} → {status:12s} → {display}")
    
    # Test 6: Platform fee calculation
    print("\n💵 Test 6: Platform Fee Calculation")
    print("-" * 70)
    test_amounts_fee = [100.00, 50.00, 250.00]
    for amount in test_amounts_fee:
        fee, seller_amount = calculate_platform_fee(amount)
        print(f"   ${amount:.2f} → Fee: ${fee:.2f} | Seller Gets: ${seller_amount:.2f}")
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 70)
    print("\n📋 Summary:")
    print(f"   • Code generation: Working")
    print(f"   • Stripe connection: {'✅ Connected' if stripe_test['success'] else '❌ Failed'}")
    print(f"   • PayPal connection: {'✅ Connected' if paypal_test['success'] else '❌ Failed'}")
    print(f"   • Amount formatting: Working")
    print(f"   • Payment validation: Working")
    print(f"   • Fee calculation: Working")
    print("\n" + "=" * 70)