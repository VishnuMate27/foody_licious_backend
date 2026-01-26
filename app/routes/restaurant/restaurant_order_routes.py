import traceback
from flask import Blueprint, current_app, jsonify, request
from app.models.order import Order, OrderStatus
from app.models.payment import Payment
from app.models.restaurant import Restaurant


restaurant_order_bp = Blueprint('restaurant_order', __name__)

def get_mongo():
    return current_app.extensions['pymongo'][0]

# TODO(Future Scope): Use websockets for realtime fetching orders 
@restaurant_order_bp.route('/getAllOrders', methods=['GET'])
def getAllOrders():
    """Get all orders of selected statuses with pagination support"""
    try:
        # Get restaurant_id from query params
        restaurant_id = request.args.get('restaurant_id')
        # Get statuses list
        statuses = request.args.getlist('status')
        # Get pagination parameters with defaults
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))

        # Validate pagination parameters
        if page < 1:
            current_app.logger.warning(f"Failed to fetch orders | restaurantId={restaurant_id} | Page number must be greater than 0")
            return jsonify({"error": "Page number must be greater than 0"}), 400
        if page_size < 1:
            current_app.logger.warning(f"Failed to fetch orders | restaurantId={restaurant_id} | Page size must be greater than 0")
            return jsonify({"error": "Page size must be greater than 0"}), 400
        if page_size > 100:  # Limit maximum page size
            current_app.logger.warning(f"Failed to fetch orders | restaurantId={restaurant_id} | Page size cannot exceed 100")
            return jsonify({"error": "Page size cannot exceed 100"}), 400

        if not restaurant_id:
            current_app.logger.warning(f"Failed to fetch orders | restaurantId={restaurant_id} | restaurant_id is required")
            return jsonify({"error": "restaurant_id is required"}), 400
        
        if not statuses:
            current_app.logger.warning(f"Failed to fetch orders | restaurantId={restaurant_id} | status is required")
            return jsonify({"error": "status is required"}), 400

        restaurant = Restaurant.find_by_id(restaurant_id)
        if not restaurant:
            current_app.logger.warning(f"Failed to fetch orders | restaurantId={restaurant_id} | Invalid Request! Restaurant does not exist")
            return jsonify({"error": "Invalid Request! Restaurant does not exist"}), 404

        # Get total count of orders
        total_count = Order.find_orders_by_restaurantId(restaurantId=restaurant_id,statuses=statuses, count_only=True)
            
        total_pages = (total_count + page_size - 1) // page_size

        # Calculate skip and limit for pagination
        skip = (page - 1) * page_size
        orders = Order.find_orders_by_restaurantId(restaurant_id, statuses=statuses, skip=skip, limit=page_size)
        order_ids = [order["id"] for order in orders]

        payments = Payment.find_payments_by_orderIds(order_ids)

        payment_map = {
            payment["orderId"]: payment["paymentStatus"]
            for payment in payments
        }

        for order in orders:
            order["paymentStatus"] = payment_map.get(order["id"])

        current_app.logger.info("Fetched orders successfully | restaurantId={restaurantId}")
        return jsonify({
            "message": "Fetched orders successfully",
            "orders": orders,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }), 200

    except Exception as e:
        current_app.logger.error(
            "Error in getAllOrders: %s\n%s", 
            str(e),
            traceback.format_exc()
        )
        return jsonify({
            "error": "Failed to get all orders",
            "details": str(e)
        }), 500

@restaurant_order_bp.route('/updateOrderStatus', methods=['POST'])
def updateOrderStatus():
    """Update status of Order"""
    try:
        data = request.get_json()
        
        required_fields = ['orderId','restaurantId','status']
        for field in required_fields:
            if field not in data or not data[field]:
                current_app.logger.warning(
                    "UpdateOrderStatusFailed | reason=OrderIdRequired",
                )
                return jsonify({"error": f"{field} is required"}), 400
            
        orderId = data['orderId']
        restaurantId = data['restaurantId']
        status=data['status']    

        restaurant = Restaurant.find_by_id(restaurantId)
        if not restaurant:
            current_app.logger.warning(f"Failed to update orders | restaurantId={restaurantId} | Invalid Request! Restaurant does not exist")
            return jsonify({"error": "Invalid Request! Restaurant does not exist"}), 404
        
        order = Order.find_by_id(orderId)
        if not order:
            current_app.logger.warning(f"Failed to update orders | restaurantId={restaurantId} | Invalid Request! Order does not exist")
            return jsonify({"error": "Invalid Request! Order does not exist"}), 404
        
        if order["restaurantId"] != restaurantId:
            current_app.logger.warning(f"Failed to update orders | restaurantId={restaurantId} | Unauthorized Request! restaurantId provided by user not match with orderId.")
            return jsonify({"error": "Unauthorized Request! restaurantId provided by user not match with orderId."}), 401
        
        if status not in [s.value for s in OrderStatus]:
            current_app.logger.warning(
                "UpdateOrderStatusFailed | reason=InvalidStatus | status=%s",
                status
            )
            return jsonify({
                "error": "Invalid status",
                "allowed_statuses": [s.value for s in OrderStatus]
            }), 400           
        
        update_data = {"status": status}
        
        success = Order.update_order(orderId, update_data)
        if not success:
            current_app.logger.warning(
                "UpdateOrderStatusFailed | reason=FailedToUpdateOrderStatus",
            )
            return jsonify({"error": "Failed to update order status."}), 500
        
        order = Order.find_by_id(orderId)
        if not order:
            current_app.logger.warning(f"Failed to update order | restaurantId={restaurantId} | Invalid Request! Failed to fetch order again.")
            return jsonify({"error": "Invalid Request! Failed to fetch order again."}), 500
        
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
    