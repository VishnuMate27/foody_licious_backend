# ✔TODO(1): Add checkout routes here
from enum import Enum
import traceback
from flask import Blueprint, current_app, jsonify, request
from app.core.exceptions import BusinessException
from app.models.cart import Cart
from app.models.order import Order
from app.services.checkout_service import CheckoutService

user_checkout_bp = Blueprint('checkout', __name__)

class CartStatus(Enum):
    ACTIVE = "active"
    LOCKED = "locked"

@user_checkout_bp.route('/',  methods = ['POST'])
def checkout():
    """Checkout the cart and create an order snapshot"""
    try:
        data = request.get_json()
        userId = data.get("userId")

        if not userId:
            current_app.logger.warning(
                "CheckoutFailed | reason=UserIdMissing | payload=%s",
                data
            )
            return jsonify({"error": "userId is required"}), 400

        result = CheckoutService.checkout(userId)

        current_app.logger.info(
            "CheckoutSuccess | userId=%s | orderId=%s | amount=%s",
            userId, result["orderId"], result["amount"]
        )

        return jsonify(result), 201

    except BusinessException as e:
        current_app.logger.warning(
            "CheckoutFailed | userId=%s | reason=%s",
            userId, str(e)
        )
        return jsonify({"error": str(e)}), 409

    except Exception as e:
        current_app.logger.error(
            "CheckoutError | userId=%s | error=%s\n%s",
            userId, str(e), traceback.format_exc()
        )
        return jsonify({"error": "Checkout failed"}), 500
   
# Backend: POST /checkout
# What backend does (transaction)
# 1. Fetch ACTIVE cart
# 2. Validate cart is not empty
# 3. Ensure no existing PENDING_PAYMENT order
# 4. Create Order snapshot
# 5. Calculate:
#     -itemTotal
#     -gstAmount (5%)
#     -finalAmount
# 6. Set order status → PENDING_PAYMENT
# 7. Set expiresAt = now + 10 min
# 8. Lock cart

# // Order
# {
#   "orderId": "o1",
#   "status": "PENDING_PAYMENT",
#   "itemTotal": 500,
#   "gstAmount": 25,
#   "finalAmount": 525,
#   "expiresAt": "2026-01-16T22:40:00Z"
# }

# // Cart
# {
#   "status": "LOCKED"
# }

# ------------------------------------------------


# Backend: POST /checkout/{orderId}/cancel
# Backend actions


# 1. Verify order is PENDING_PAYMENT
# 2. Set order → CANCELLED
# 3. Unlock cart

# Order → CANCELLED
# Cart  → ACTIVE


# ✔ User can edit cart again
# ✔ No data loss


@user_checkout_bp.route('/cancel',  methods = ['POST'])
def cancelCheckout():
    """Cancel checkout and unlock the cart"""
    try:
        data = request.get_json()
        orderId = data.get("orderId")

        if not orderId:
            current_app.logger.warning(
                "CancelCheckoutFailed | reason=OrderIdMissing | payload=%s",
                data
            )
            return jsonify({"error": "orderId is required"}), 400

        result = CheckoutService.cancelCheckout(orderId)

        current_app.logger.info(
            "CancelCheckoutSuccess | orderId=%s",
            orderId
        )

        return jsonify(result), 200

    except BusinessException as e:
        current_app.logger.warning(
            "CancelCheckoutFailed | orderId=%s | reason=%s",
            orderId, str(e)
        )
        return jsonify({"error": str(e)}), 409

    except Exception as e:
        current_app.logger.error(
            "CancelCheckoutError | orderId=%s | error=%s\n%s",
            orderId, str(e), traceback.format_exc()
        )
        return jsonify({"error": "Cancel Checkout failed"}), 500
   