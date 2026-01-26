import traceback
from flask import Blueprint, current_app, jsonify, request
from app.models.order import Order
from app.models.payment import Payment, PaymentStatus
from app.models.restaurant import Restaurant

restaurant_payment_bp = Blueprint('restaurant_payment', __name__)

def get_mongo():
    return current_app.extensions['pymongo'][0]

@restaurant_payment_bp.route('/updatePaymentStatus', methods=['POST'])
def updatePaymentStatus():
    """Update payment status of Order"""
    try:
        data = request.get_json()
        
        required_fields = ['orderId','restaurantId','paymentStatus']
        for field in required_fields:
            if field not in data or not data[field]:
                current_app.logger.warning(
                    f"UpdatePaymentStatusFailed | reason={field}Required",
                )
                return jsonify({"error": f"{field} is required"}), 400
            
        orderId = data['orderId']
        restaurantId = data['restaurantId']
        paymentStatus=data['paymentStatus']    

        restaurant = Restaurant.find_by_id(restaurantId)
        if not restaurant:
            current_app.logger.warning(f"Failed to update orders | restaurantId={restaurantId} | Invalid Request! Restaurant does not exist")
            return jsonify({"error": "Invalid Request! Restaurant does not exist"}), 404
        
        payment = Payment.find_payment_by_orderId(orderId)
        if not payment:
            current_app.logger.warning(f"Failed to update  | restaurantId={restaurantId} | Invalid Request! Order does not exist")
            return jsonify({"error": "Invalid Request! Order does not exist"}), 404
        
        order = Order.find_order_by_id(orderId)
        if not order:
            current_app.logger.warning(f"Failed to update orders | restaurantId={restaurantId} | Invalid Request! Order does not exist")
            return jsonify({"error": "Invalid Request! Order does not exist"}), 404
        
        if order["restaurantId"] != restaurantId:
            current_app.logger.warning(f"Failed to update orders | restaurantId={restaurantId} | Unauthorized Request! restaurantId provided by user not match with orderId.")
            return jsonify({"error": "Unauthorized Request! restaurantId provided by user not match with orderId."}), 401
        
        if paymentStatus not in [s.value for s in PaymentStatus]:
            current_app.logger.warning(
                "UpdatePaymentStatusFailed | reason=InvalidStatus | status=%s",
                paymentStatus
            )
            return jsonify({
                "error": "Invalid status",
                "allowed_statuses": [s.value for s in PaymentStatus]
            }), 400           
        
        update_data = {"paymentStatus": paymentStatus}
        
        success = Payment.update_payment(payment["id"], update_data)
        if not success:
            current_app.logger.warning(
                "UpdatePaymentStatusFailed | reason=FailedToUpdatePaymentStatus",
            )
            return jsonify({"error": "Failed to update payment status."}), 500
        
        order = Order.find_order_by_id(orderId)
        if not order:
            current_app.logger.warning(f"Failed to update order | restaurantId={restaurantId} | Invalid Request! Failed to fetch order again.")
            return jsonify({"error": "Invalid Request! Failed to fetch order again."}), 500
        
        payment = Payment.find_payment_by_orderId(order["id"])

        order["paymentStatus"] = payment["paymentStatus"]
        
        current_app.logger.info(
            "UpdateOrderStatusSuccess | id=%s",
            id
        )        
        return jsonify({
            "message": "Order Status updated successfully!",
            "order": order
        }), 200
        
    except Exception as e:
        current_app.logger.error(
            "UpdateOrderStatusException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Failed to update order status", "details": str(e)}), 500    
  
