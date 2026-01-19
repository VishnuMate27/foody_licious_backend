from datetime import datetime, timedelta
from app import mongo
from app.core.exceptions import BusinessException
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentMode, PaymentStatus

class PaymentService:
    
    @staticmethod
    def generatePaymentRequest(orderId: str):
        client = mongo.cx
        session = client.start_session()

        try:
            with session.start_transaction():
                
                # Fetch order
                order = Order.find_order_by_id(orderId=orderId, session=session)  
                
                if not order:
                    raise BusinessException("Order not found")
                
                if order["status"] != OrderStatus.PENDING_PAYMENT.value:
                    raise BusinessException("Order status is not PENDING_PAYMENT")
                
                payment = Payment.find_payment_by_orderId(orderId=orderId, session=session)
                
                if payment:
                    if payment["paymentStatus"] == PaymentStatus.SUCCESS.value:
                        raise BusinessException("Payment status is already success!")
                    elif payment["paymentStatus"] == PaymentStatus.PENDING.value:
                        raise BusinessException("Payment status is already pending! You can retry after old payment window is expired")
                    else:
                        new_payment = Payment(userId= order["userId"] , restaurantId= order["restaurantId"],orderId= order["_id"],finalAmount=order["grandTotalAmount"], paymentStatus=PaymentStatus.PENDING.value , paymentWindowExpireAt= datetime.utcnow() + timedelta(minutes=15))
                        paymentId = new_payment.save(session)     
                else:
                    new_payment = Payment(userId= order["userId"] , restaurantId= order["restaurantId"],orderId= order["id"],finalAmount=order["grandTotalAmount"], paymentStatus=PaymentStatus.PENDING.value , paymentWindowExpireAt= datetime.utcnow() + timedelta(minutes=15))
                    paymentId = new_payment.save(session)    
                
                orderUpdateSuccess = Order.update_order(orderId=orderId, update_data={"status": OrderStatus.CONFIRMED.value},session=session) 
                
                if not orderUpdateSuccess: 
                    raise BusinessException("Failed to update order status to confirmed")
                
                return {
                    "message": "Payment Record geneartion successful",
                    "paymentId": paymentId
                }
        finally:
           session.end_session()         
                
    @staticmethod
    def completePayment(paymentId: str, paymentMode: str):
        client = mongo.cx
        session = client.start_session()

        try:
            with session.start_transaction():
                
                # Fetch payment
                payment = Payment.find_payment_by_id(paymentId, session=session) 
                
                if not payment:
                    raise BusinessException("Payment Request not found")
                
                if payment["paymentStatus"] != PaymentStatus.PENDING.value:
                    raise BusinessException("Payment status is not PENDING")
                
                if payment["paymentMode"] != PaymentMode.NOT_SELECTED.value:
                    raise BusinessException("Payment mode is not NOT_SELECTED")
                
                # Update Payment Mode
                # For Payment mode COD, Only update payment mode, update payment window expiry at and keep rest of the things as it is.
                if paymentMode == PaymentMode.COD.value:
                    paymentWindowExpireAt = datetime.utcnow() + timedelta(days=7)
                    success = Payment.update_payment(paymentId=paymentId,update_data={"paymentMode": paymentMode, "paymentWindowExpireAt": paymentWindowExpireAt},session=session)
                
                # In Future
                # For other Payment modes update payment mode & Payment Status.
                
                if not success: 
                    raise BusinessException(f"Failed to update payment mode to {paymentMode}")
                
                return {
                    "message": "Payment Completed succesful. For COD paymentmode updated succesfully.",
                    "paymentId": paymentId
                }
        finally:
           session.end_session()         
                   