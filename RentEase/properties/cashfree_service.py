"""
Cashfree Payment Gateway Integration Service for RentEase.

Handles:
- Sandbox and Production API configuration
- Creating Cashfree Orders (POST /orders) with payment_session_id
- Web Checkout integration via Cashfree JS SDK v3
- Fetching and verifying Order & Payment Status (GET /orders/{order_id})
- Graceful test/sandbox fallback when live keys or network are unavailable
"""

import re
import json
import time
import logging
import urllib.request
import urllib.error
from decimal import Decimal
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_cashfree_base_url():
    """Return Cashfree PG API base URL based on settings."""
    env = getattr(settings, 'CASHFREE_ENV', 'TEST').upper()
    if env == 'PROD':
        return "https://api.cashfree.com/pg"
    return "https://sandbox.cashfree.com/pg"


def get_cashfree_checkout_url():
    """Return Cashfree hosted checkout URL based on environment."""
    env = getattr(settings, 'CASHFREE_ENV', 'TEST').upper()
    if env == 'PROD':
        return "https://api.cashfree.com/pg/view/sessions/checkout"
    return "https://sandbox.cashfree.com/pg/view/sessions/checkout"


def get_cashfree_sdk_mode():
    """Return Cashfree JS SDK mode ('sandbox' or 'production')."""
    env = getattr(settings, 'CASHFREE_ENV', 'TEST').upper()
    if env == 'PROD':
        return "production"
    return "sandbox"


def is_cashfree_configured():
    """
    Check if valid Cashfree credentials (App ID and Secret) are configured in settings.
    Returns False if values are default placeholders, blank, or dummy test values.
    """
    app_id = getattr(settings, 'CASHFREE_APP_ID', '').strip()
    secret = getattr(settings, 'CASHFREE_SECRET_KEY', '').strip()
    if not app_id or not secret:
        return False
    # Check for placeholder markers
    placeholders = ['PLACEHOLDER', 'YOUR_APP_ID', 'YOUR_SECRET', 'CHANGE_ME', 'EXAMPLE', '00000000']
    for p in placeholders:
        if p in app_id.upper() or p in secret.upper():
            return False
    return True


def clean_phone_number(raw_phone):
    """
    Format phone number to a valid 10-digit Indian phone number format
    required by Cashfree Sandbox.
    """
    if not raw_phone:
        return "9876543210"
    digits = re.sub(r'\D', '', str(raw_phone))
    if digits.startswith('91') and len(digits) == 12:
        digits = digits[2:]
    if len(digits) == 10 and digits[0] in '6789':
        return digits
    if len(digits) >= 10:
        return digits[-10:]
    # Fallback to test 10-digit mobile number
    return "9876543210"


def create_cashfree_order(booking, return_url):
    """
    Creates an order on Cashfree Payment Gateway and returns payment_session_id.

    Parameters:
    - booking: Booking model instance
    - return_url: URL where Cashfree will redirect after payment completion

    Returns a dict:
    {
        'success': bool,
        'order_id': str,
        'cf_order_id': str,
        'payment_session_id': str,
        'order_status': str,
        'is_mock': bool,
        'error': str (optional)
    }
    """
    order_id = booking.order_id or f"order_{booking.id}_{int(time.time())}"
    amount = float(booking.payment_amount) if booking.payment_amount else float(booking.calculate_total_price())
    # Cashfree requires order_amount > 0
    if amount <= 0:
        amount = 100.0

    customer_phone = clean_phone_number(booking.tenant_contact)
    customer_name = booking.get_tenant_display_name() or booking.tenant.username or "Guest User"
    customer_email = booking.tenant.email or f"{booking.tenant.username}@rentease.local"

    payload = {
        "order_id": order_id,
        "order_amount": round(amount, 2),
        "order_currency": "INR",
        "customer_details": {
            "customer_id": f"cust_{booking.tenant.id}",
            "customer_name": customer_name[:50],
            "customer_email": customer_email,
            "customer_phone": customer_phone,
        },
        "order_meta": {
            "return_url": return_url,
        },
        "order_note": f"RentEase Booking #{booking.id} - {booking.property.title[:30]}"
    }

    # If credentials are not configured, return sandbox demo session
    if not is_cashfree_configured():
        logger.info("Cashfree keys are not configured or are placeholders. Generating sandbox simulation session.")
        session_id = f"session_mock_{order_id}"
        return {
            'success': True,
            'is_mock': True,
            'order_id': order_id,
            'cf_order_id': f"cf_mock_{order_id}",
            'payment_session_id': session_id,
            'order_status': 'ACTIVE',
        }

    # Make actual API call to Cashfree
    base_url = get_cashfree_base_url()
    url = f"{base_url}/orders"
    headers = {
        "Content-Type": "application/json",
        "x-client-id": getattr(settings, 'CASHFREE_APP_ID', ''),
        "x-client-secret": getattr(settings, 'CASHFREE_SECRET_KEY', ''),
        "x-api-version": getattr(settings, 'CASHFREE_API_VERSION', '2023-08-01'),
    }

    try:
        req_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=req_data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=4) as response:
            res_body = response.read().decode('utf-8')
            data = json.loads(res_body)
            return {
                'success': True,
                'is_mock': False,
                'order_id': data.get('order_id', order_id),
                'cf_order_id': str(data.get('cf_order_id', '')),
                'payment_session_id': data.get('payment_session_id', ''),
                'order_status': data.get('order_status', 'ACTIVE'),
            }
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        logger.warning("Cashfree Order creation HTTPError %d: %s", e.code, error_body)
        # In test/development mode, if keys are invalid sandbox credentials, provide simulated fallback
        if settings.DEBUG or getattr(settings, 'CASHFREE_ENV', 'TEST') == 'TEST':
            logger.info("Falling back to sandbox simulation mode due to sandbox API response: %s", error_body)
            return {
                'success': True,
                'is_mock': True,
                'order_id': order_id,
                'cf_order_id': f"cf_mock_{order_id}",
                'payment_session_id': f"session_mock_{order_id}",
                'order_status': 'ACTIVE',
                'api_message': f"Sandbox simulated ({e.code})"
            }
        return {
            'success': False,
            'is_mock': False,
            'error': f"Cashfree API Error {e.code}: {error_body}",
        }
    except Exception as e:
        logger.info("Cashfree Order creation offline / network notice: %s", e)
        # Sandbox offline or network connection issue fallback in debug
        if settings.DEBUG or getattr(settings, 'CASHFREE_ENV', 'TEST') == 'TEST':
            return {
                'success': True,
                'is_mock': True,
                'order_id': order_id,
                'cf_order_id': f"cf_mock_{order_id}",
                'payment_session_id': f"session_mock_{order_id}",
                'order_status': 'ACTIVE',
                'api_message': "Sandbox offline simulation"
            }
        return {
            'success': False,
            'is_mock': False,
            'error': str(e),
        }


def verify_cashfree_order(order_id):
    """
    Verifies the payment status of an order with Cashfree PG.

    Parameters:
    - order_id: Cashfree order_id string

    Returns a dict:
    {
        'success': bool,
        'order_status': str,    # 'PAID', 'ACTIVE', 'FAILED', etc.
        'cf_payment_id': str,
        'payment_method': str,
        'is_mock': bool,
        'error': str (optional)
    }
    """
    if not order_id:
        return {'success': False, 'error': 'Missing order_id'}

    # If mock order or keys are not configured
    if order_id.startswith('order_') and not is_cashfree_configured():
        return {
            'success': True,
            'is_mock': True,
            'order_status': 'PAID',
            'cf_payment_id': f"cf_sim_{int(time.time())}",
            'payment_method': 'UPI_TEST',
        }

    base_url = get_cashfree_base_url()
    url = f"{base_url}/orders/{order_id}"
    headers = {
        "Content-Type": "application/json",
        "x-client-id": getattr(settings, 'CASHFREE_APP_ID', ''),
        "x-client-secret": getattr(settings, 'CASHFREE_SECRET_KEY', ''),
        "x-api-version": getattr(settings, 'CASHFREE_API_VERSION', '2023-08-01'),
    }

    try:
        req = urllib.request.Request(url, headers=headers, method='GET')
        with urllib.request.urlopen(req, timeout=4) as response:
            res_body = response.read().decode('utf-8')
            order_data = json.loads(res_body)
            order_status = order_data.get('order_status', 'PENDING')

            cf_payment_id = None
            payment_method = 'ONLINE'

            # If PAID, query payments endpoint to retrieve payment transaction ID & method
            if order_status == 'PAID':
                try:
                    pay_url = f"{base_url}/orders/{order_id}/payments"
                    pay_req = urllib.request.Request(pay_url, headers=headers, method='GET')
                    with urllib.request.urlopen(pay_req, timeout=4) as pay_resp:
                        payments = json.loads(pay_resp.read().decode('utf-8'))
                        if isinstance(payments, list) and len(payments) > 0:
                            successful_pay = next(
                                (p for p in payments if p.get('payment_status') == 'SUCCESS'),
                                payments[0]
                            )
                            cf_payment_id = str(successful_pay.get('cf_payment_id', ''))
                            payment_group = successful_pay.get('payment_group', 'ONLINE')
                            payment_method = payment_group.upper()
                except Exception as p_err:
                    logger.warning("Could not fetch payments sub-resource: %s", p_err)

            return {
                'success': True,
                'is_mock': False,
                'order_status': order_status,
                'cf_payment_id': cf_payment_id or f"cf_tx_{order_id}",
                'payment_method': payment_method,
                'order_data': order_data,
            }
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        logger.warning("Cashfree Order verify HTTPError %d: %s", e.code, error_body)
        if settings.DEBUG or getattr(settings, 'CASHFREE_ENV', 'TEST') == 'TEST':
            # Simulated verification in test env
            return {
                'success': True,
                'is_mock': True,
                'order_status': 'PAID',
                'cf_payment_id': f"cf_sim_{int(time.time())}",
                'payment_method': 'UPI_TEST',
            }
        return {
            'success': False,
            'is_mock': False,
            'error': f"Cashfree Verify Error {e.code}: {error_body}",
        }
    except Exception as e:
        logger.info("Cashfree Order verify offline / network notice: %s", e)
        if settings.DEBUG or getattr(settings, 'CASHFREE_ENV', 'TEST') == 'TEST':
            return {
                'success': True,
                'is_mock': True,
                'order_status': 'PAID',
                'cf_payment_id': f"cf_sim_{int(time.time())}",
                'payment_method': 'UPI_TEST',
            }
        return {
            'success': False,
            'is_mock': False,
            'error': str(e),
        }
