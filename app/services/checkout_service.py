from app import mongo
from app.models.cart import Cart, CartStatus
from app.services.pricing_service import PricingService
from app.models.order import Order, OrderStatus
from app.core.exceptions import BusinessException
from pymongo.errors import PyMongoError

class CheckoutService:
    
    @staticmethod
    def checkout(userId: str):
        client = mongo.cx
        session = client.start_session()

        try:
            with session.start_transaction():

                cart = Cart.find_cart_by_userId(userId, session)
                if not cart:
                    raise BusinessException("Cart not found")

                if cart["status"] == CartStatus.LOCKED.value:
                    raise BusinessException("Cart is locked")

                if not cart["items"]:
                    raise BusinessException("Cart is empty")

                pending_order = Order.find_pending_order_by_userId(userId=userId, session=session)
                if pending_order:
                    raise BusinessException("Old order is still pending")

                pricing = PricingService.calculate(cart["totalAmount"])

                order_id = Order.create_from_cart(
                    cart=cart,
                    pricing=pricing,
                    session=session
                )

                updated = Cart.lock_cart(cartId=cart["id"], session=session)
                if not updated:
                    raise BusinessException("Failed to lock cart")

                return {
                    "orderId": order_id,
                    "amount": pricing["grandTotalAmount"]
                }

        finally:
            session.end_session()
            
    @staticmethod
    def cancelCheckout(orderId: str):
        client = mongo.cx
        session = client.start_session()

        try:
            with session.start_transaction():
                
                #  Verify order is PENDING_PAYMENT
                order = Order.find_order_by_id(orderId)
            
                if order["status"] != OrderStatus.PENDING_PAYMENT.value:
                   raise BusinessException("Order status is not PENDING_PAYMENT") 
                
                # Set order → CANCELLED
                success = Order.update_order(orderId= orderId,update_data= {"status": OrderStatus.CANCELLED.value},session=session)
                if not success:
                   raise BusinessException("Failed to cancel order")  
                        
                # Unlock cart
                success = Cart.unlock_cart(cartId=order["cartId"], session=session)       
                if not success:
                       raise BusinessException("Failed to unlock cart") 
                 
                return {
                    "orderId": orderId
                }   
        
        finally:
            session.end_session()    