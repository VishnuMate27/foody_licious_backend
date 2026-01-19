from typing import Any, Optional
from bson import ObjectId
from app import mongo
from datetime import datetime
from enum import Enum

from app.models import restaurant
from app.utils.mongo_utils import flatten
from app.utils.serializers import serialize_doc

class PaymentMode(Enum):
    NOT_SELECTED = "NOT_SELECTED"
    COD = "COD"
    UPI = "UPI"
    CARD = "CARD"
    NETBANKING = "NETBANKING"
    
class PaymentStatus(Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"  

class SettlementToRestaurantStatus(Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class SettlementToUserStatus(Enum): # Incase of order is undelivered
    NOT_REQUESTED = "NOT_REQUESTED"
    REQUESTED = "REQUESTED" # Incase of user asks for refund
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"     

class Payment:
    def __init__(self, userId: str, restaurantId: str, orderId: str, finalAmount: float, paymentStatus: str, paymentWindowExpireAt: datetime):
        self.userId = userId
        self.restaurantId = restaurantId
        self.orderId = orderId
        self.finalAmount = finalAmount
        self.paymentStatus = paymentStatus
        self.paymentMode = PaymentMode.NOT_SELECTED.value
        self.paymentWindowExpireAt = paymentWindowExpireAt
        self.createdAt = datetime.utcnow()
        self.updatedAt = datetime.utcnow()
        
    def save(self,session: Optional[Any]=None):
        """Save Cart to database"""
        payment_data = {
            "userId": self.userId,
            "orderId": self.orderId,
            "finalAmount": self.finalAmount,
            "paymentStatus": self.paymentStatus,
            "paymentMode": self.paymentMode,
            "paymentWindowExpireAt": self.paymentWindowExpireAt,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt
        }
        result = mongo.db.payments.insert_one(payment_data,session=session)
        return str(result.inserted_id)

    @staticmethod
    def find_payment_by_id(paymentId,session: Any):
        """Find payment by payment id"""
        payment = mongo.db.payments.find_one({"_id": ObjectId(paymentId)},session=session)
        return serialize_doc(payment) if payment else None    
    
    @staticmethod
    def find_payment_by_userId(userId: str,session: Any):
        """Find payment by user id"""
        payment = mongo.db.payments.find_one({"userId": userId},session=session)
        return serialize_doc(payment) if payment else None
    
    @staticmethod
    def find_payment_by_orderId(orderId: str,session: Optional[Any] = None):
        """Find payment by order id"""
        query = {"orderId": orderId}

        kwargs = {}
        if session is not None:
            kwargs["session"] = session

        payment = mongo.db.payments.find_one(query, **kwargs)
        return serialize_doc(payment) if payment else None
    
    @staticmethod
    def update_payment(paymentId: str, update_data: Any,session: Optional[Any] = None):
        """Update payment data"""
        update_data['updatedAt'] = datetime.utcnow()
        # Flatten nested fields into dot-notation
        flattened_data = flatten(update_data)
        result = mongo.db.payments.update_one(
            {"_id": ObjectId(paymentId)},
            {"$set": flattened_data},
            session=session
        )
        return result.modified_count > 0    
