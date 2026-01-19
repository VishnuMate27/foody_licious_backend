# ✔TODO(3): Add payment endpoints here 

# Trigger
# User taps Pay Now
# Backend: POST /payment
# Backend actions
# Fetch order
# Validate status = PENDING_PAYMENT
# Charge finalAmount
# Wait for payment result

# -------------------------------------------------------

# Payment SUCCESS
# Backend actions (transaction)
# Order → CONFIRMED
# Cart → CLEARED (or deleted)
# Create new empty ACTIVE cart
# Order → CONFIRMED
# Cart  → CLEARED
# ✔ Order finalized
# ✔ Cart lifecycle complete
        # # Fetch order
        # order = Order.find_order_by_id(orderId)
        
        # if order["status"] != OrderStatus.PENDING_PAYMENT.value:
        #     current_app.logger.warning(
        #         "PaymentRecordCreationFailed | reason=OrderStatusIsNotPendingPayment | payload=%s",
        #         data
        #     )
        #     return jsonify({"error": "Order status is not PENDING_PAYMENT"}), 409
        
        # payment = Payment.find_payment_by_orderId(orderId)
        
        # # Check if payment record for this order already exists
        # if payment:
        #     if payment["status"] == PaymentStatus.SUCCESS:
        #         current_app.logger.warning(
        #             "PaymentRecordCreationFailed | reason=PaymentStatusIsAlreadySuccess | payload=%s",
        #             data
        #         )
        #         return jsonify({"error": "Payment status is already success!"}), 404
        #     elif payment["status"] == PaymentStatus.PENDING:
        #         current_app.logger.warning(
        #             "PaymentRecordCreationFailed | reason=PaymentStatusIsAlreadyPending | payload=%s",
        #             data
        #         )
        #         return jsonify({"error": "Payment status is already pending! You can retry after old payment window is expired"}), 404
        #     else:
        #         new_payment = Payment(userId= order["userId"] , restaurantId= order["restaurantId"],orderId= order["_id"],finalAmount=order["grandTotalAmount"], paymentStatus=PaymentStatus.PENDING , paymentWindowExpireAt= datetime.utcnow() + timedelta(minutes=15))
        #         new_payment.save()                  
        # else:
        #     new_payment = Payment(userId= order["userId"] , restaurantId= order["restaurantId"],orderId= order["_id"],finalAmount=order["grandTotalAmount"], paymentStatus=PaymentStatus.PENDING , paymentWindowExpireAt= datetime.utcnow() + timedelta(minutes=15))
        #     new_payment.save() 
        # Create payment record
        # Check if payment record for this order already exists
            # if exists
                # check payment status 
                # if PaymentStatus = paymentStatus.SUCCESS
                    # return Payment for this order is already success
                # elseif PaymentStatus = paymentStatus.PENDING
                    # return Payment for this order is pending
                # else
                    # Payment for this order was failed previously recreating the payment record
                    ### Create new payment record in this case & Payment status will be set to pending
            # else
                #  Create new payment record in this case & Payment status will be set to pending                        
        
        # orderUpdateSuccess = Order.update_order(orderId=orderId, update_data={"status": OrderStatus.CONFIRMED.value}) 
        
        # if not orderUpdateSuccess:
        # #    Failed to update order status to confirmed
from datetime import datetime, timedelta
import traceback
from flask import Blueprint, current_app, jsonify, request

from app.core.exceptions import BusinessException
from app.models.cart import Cart
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.services.payment_service import PaymentService

user_payment_bp = Blueprint('payment',__name__)

@user_payment_bp.route('/generatePaymentRecord', methods = ['POST'])
def generatePaymentRecord():
    """Create payment record for an order in database for requesting payment from user/payment gateway"""
    try:
        data = request.get_json()
        orderId = data.get("orderId")

        if not orderId:
            current_app.logger.warning(
                "PaymentRecordCreationFailed | reason=OrderIdMissing | payload=%s",
                data
            )
            return jsonify({"error": "orderId is required"}), 400
        
        result = PaymentService.generatePaymentRequest(orderId=orderId)
        
        current_app.logger.info(
            "PaymentRecordCreationSuccess | paymentId=%s",
            result["paymentId"]
        )

        return jsonify(result), 201

    except BusinessException as e:
        current_app.logger.warning(
            "PaymentRecordCreationFailed | orderId=%s | reason=%s",
            orderId, str(e)
        )
        return jsonify({"error": str(e)}), 409        
          
    except Exception as e:
        current_app.logger.error(
            "PaymentRecordCreationException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Failed to create payment record!", "details": str(e)}), 500      


@user_payment_bp.route('/completePayment', methods = ['POST'])
def completePayment():
    """Checks the payment mode selected by user and update payment status in payment record."""
    try:
        data = request.get_json()
                
        required_fields = ['paymentId', 'paymentMode']
        for field in required_fields:
            if field not in data or not data[field]:
                current_app.logger.warning(
                    f"PaymentCompletionFailed | reason={field}Required",
                )
                return jsonify({"error": f"{field} is required"}), 400

        paymentId = data['paymentId']
        paymentMode = data['paymentMode']
        result = PaymentService.completePayment(paymentId=paymentId,paymentMode=paymentMode)
        
        current_app.logger.info(
            "PaymentCompletionSuccess | paymentId=%s",
            result["paymentId"]
        )

        return jsonify(result), 200

    except BusinessException as e:
        current_app.logger.warning(
            "PaymentCompletionFailed | paymentId=%s | reason=%s",
            paymentId, str(e)
        )
        return jsonify({"error": str(e)}), 409        
          
    except Exception as e:
        current_app.logger.error(
            "PaymentCompletionException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Failed to complete payment!", "details": str(e)}), 500      



