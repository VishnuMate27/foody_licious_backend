from datetime import datetime, timedelta
from app import mongo
from app.core.exceptions import BusinessException
from app.models.cart import Cart
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentMode, PaymentStatus

class PaymentService:
    
    @staticmethod
    def generatePaymentRequest(orderId: str, session):    
        # Fetch order
        order = Order.find_order_by_id(orderId=orderId, session=session)  
                
        if not order:
            raise BusinessException(
                code="ORDER_NOT_FOUND",
                message="Order not found"
            )
                
        if order["status"] != OrderStatus.PENDING_PAYMENT.value:
            raise BusinessException(
                code="ORDER_STATUS_NOT_PENDING_PAYMENT",
                message="Order status is not PENDING_PAYMENT"
            )            
                
        payment = Payment.find_payment_by_orderId(orderId=orderId, session=session)
                
        if payment:
            if payment["paymentStatus"] == PaymentStatus.SUCCESS.value:
                raise BusinessException(
                    code="PAYMENT_STATUS_ALREADY_SUCCESS",
                    message="Payment status is already success!"
                )
            elif payment["paymentStatus"] == PaymentStatus.PENDING.value:
                raise BusinessException(
                    code="OLD_PAYMENT_STATUS_ALREADY_PENDING",
                    message="Payment status is already pending! You can retry after old payment window is expired!"
                )
            else:
                new_payment = Payment(userId= order["userId"] , restaurantId= order["restaurantId"],orderId= order["_id"],finalAmount=order["grandTotalAmount"], paymentStatus=PaymentStatus.PENDING.value , paymentWindowExpireAt= datetime.utcnow() + timedelta(minutes=15))
                paymentId = new_payment.save(session)     
        else:
            new_payment = Payment(userId= order["userId"] , restaurantId= order["restaurantId"],orderId= order["id"],finalAmount=order["grandTotalAmount"], paymentStatus=PaymentStatus.PENDING.value , paymentWindowExpireAt= datetime.utcnow() + timedelta(minutes=15))
            paymentId = new_payment.save(session)                    
                
        return {
            "message": "Payment Record geneartion successful",
            "paymentId": paymentId
        }   
                
    @staticmethod
    def completePayment(paymentId: str, paymentMode: str):
        client = mongo.cx
        session = client.start_session()

        try:
            with session.start_transaction():
                
                # Fetch payment
                payment = Payment.find_payment_by_id(paymentId, session=session) 
                
                if not payment:
                    raise BusinessException(
                        code="PAYMENT_REQUEST_NOT_FOUND",
                        message="Payment request not found."
                    )
                
                if payment["paymentStatus"] != PaymentStatus.PENDING.value:
                    raise BusinessException(
                        code="PAYMENT_STATUS_IS_NOT_PENDING",
                        message="Payment status is not PENDING"
                    )
                
                if payment["paymentMode"] != PaymentMode.NOT_SELECTED.value:
                    raise BusinessException(
                        code="PAYMENT_STATUS_IS_NOT_SELECTED",
                        message="Payment mode is not NOT_SELECTED"
                    )
                
                # Update Payment Mode
                # For Payment mode COD, Only update payment mode, update payment window expiry at and keep rest of the things as it is.
                if paymentMode == PaymentMode.COD.value:
                    paymentWindowExpireAt = datetime.utcnow() + timedelta(days=7)
                    success = Payment.update_payment(paymentId=paymentId,update_data={"paymentMode": paymentMode, "paymentWindowExpireAt": paymentWindowExpireAt},session=session)
                    
                # In Future
                # For other Payment modes update payment mode & Payment Status.
                if not success:
                    raise BusinessException(
                        code="FAILED_TO_UPDATE_PAYMENT_MODE",
                        message=f"Failed to update payment mode to {paymentMode}"
                    )
                
                # Fetch Order
                order = Order.find_order_by_paymentId(paymentId=paymentId, session=session)
                
                if not order:
                    raise BusinessException(
                        code="ORDER_NOT_FOUND",
                        message="Order not found"
                    )
                
                # Update Order Status to Confirmed
                Order.update_order(orderId=order["id"], update_data={"status":OrderStatus.CONFIRMED.value}, session=session) 
                
                # Delete cart on order success
                Cart.delete_cart(cartId=order["cartId"], session=session) 
                                    
                return {
                    "message": "Payment Completed succesful. For COD paymentmode updated succesfully.",
                    "paymentId": paymentId
                }
        finally:
           session.end_session()         
                   