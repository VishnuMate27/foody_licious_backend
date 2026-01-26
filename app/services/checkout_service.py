from app import mongo
from app.models.cart import Cart, CartStatus
from app.models.payment import Payment
from app.services.payment_service import PaymentService
from app.services.pricing_service import PricingService
from app.models.order import Order, OrderStatus
from app.core.exceptions import BusinessException
from pymongo.errors import PyMongoError

class CheckoutService:
    
    @staticmethod
    def placeOrder(userId: str, name: str, address: str, phone: str):
        client = mongo.cx
        session = client.start_session()

        try:
            with session.start_transaction():

                cart = Cart.find_cart_by_userId(userId, session)
                if not cart:
                    raise BusinessException(
                        code="CART_NOT_FOUND",
                        message="Cart not found"
                    )   

                if cart["status"] == CartStatus.LOCKED.value:
                    raise BusinessException(
                        code="CART_LOCKED",
                        message="Cart is locked"
                    ) 

                if not cart["items"]:
                    raise BusinessException(
                        code="CART_EMPTY",
                        message="Cart is empty"
                    )                     

                pending_order = Order.find_pending_order_by_userId(userId=userId, session=session)
                if pending_order:
                    raise BusinessException(
                        code="OLD_ORDER_PENDING",
                        message="Old order is still pending"
                    )  

                pricing = PricingService.calculate(cart["totalAmount"])

                order_id = Order.create_from_cart(
                    cart=cart,
                    pricing=pricing,
                    session=session,
                    name=name,
                    address=address,
                    phone=phone
                )

                updated = Cart.lock_cart(cartId=cart["id"], session=session)
                if not updated:
                    raise BusinessException(
                        code="CART_LOCK_FAILED",
                        message="Failed to lock cart"
                    )
                    
                result = PaymentService.generatePaymentRequest(orderId=order_id, session=session)
                
                # Update payment id for the order
                Order.update_order(orderId=order_id,update_data={"paymentId": result["paymentId"]},session=session)                     

                return {
                    "orderId": order_id,
                    "paymentId": result["paymentId"],
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
                order = Order.find_order_by_id(orderId,session=session)
            
                if order["status"] != OrderStatus.PENDING_PAYMENT.value:
                   raise BusinessException(
                        code="ORDER_STATUS_IS_NOT_PENDING_PAYMENT",
                        message="Order status is not PENDING_PAYMENT"
                    )
                   
                # Delete Payment
                success = Payment.delete_payment(paymentId= order["paymentId"], session=session)
                if not success:
                    raise BusinessException(
                        code="PAYMENT_DELETE_FAILED",
                        message="Failed to delete payment."
                    )   
                
                # Delete Order
                success = Order.delete_order(orderId= orderId, session=session)
                if not success:
                    raise BusinessException(
                        code="ORDER_DELETE_FAILED",
                        message="Failed to delete order."
                    )    
                        
                # Unlock cart
                success = Cart.unlock_cart(cartId=order["cartId"], session=session)       
                if not success:
                    raise BusinessException(
                        code="CART_UNLOCK_FAILED",
                        message="Failed to unlock cart."
                    )
                 
                return {
                    "orderId": orderId
                }   
        
        finally:
            session.end_session()    