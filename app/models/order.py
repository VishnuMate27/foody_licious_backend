from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from bson import ObjectId
from app import mongo
from app.services.pricing_service import PricingService
from app.utils.mongo_utils import flatten
from app.utils.serializers import serialize_doc

class OrderStatus(Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

class Order:
    def __init__(self,*,cartId: str, restaurantId: str, userId: str, items: list, totalCartAmount: float, gstCharges: float ,platformFees: float,deliveryCharges: float,grandTotalAmount: float):
        self.cartId = cartId
        self.restaurantId = restaurantId
        self.userId = userId
        self.items = items
        self.totalCartAmount = totalCartAmount
        self.gstCharges = gstCharges
        self.platformFees = platformFees
        self.deliveryCharges = deliveryCharges
        self.grandTotalAmount = grandTotalAmount
        self.expireAt = datetime.utcnow() + timedelta(minutes= 10)
        self.status = OrderStatus.PENDING_PAYMENT.value
        self.createdAt = datetime.utcnow()
        self.updatedAt = datetime.utcnow()
        
        
    def save(self,*,session: Any):
        """Save Order to database"""
        order_data = {
            "cartId": self.cartId,
            "restaurantId": self.restaurantId,
            "userId": self.userId,
            "items": self.items,
            "totalCartAmount": self.totalCartAmount,
            "gstCharges": self.gstCharges,
            "deliveryCharges": self.deliveryCharges,
            "grandTotalAmount": self.grandTotalAmount,
            "status": self.status,
            "expireAt": self.expireAt,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
        }
        result = mongo.db.orders.insert_one(order_data, session=session)
        return str(result.inserted_id)
    
    @staticmethod
    def create_from_cart(cart: Any,pricing: Any,session: Any): 
        """Create order from cart"""
        order = Order(
            cartId = cart["id"],
            restaurantId=cart["restaurantId"],
            userId=cart["userId"],
            items=cart["items"],
            totalCartAmount=cart["totalAmount"],
            gstCharges=pricing["gstCharges"],
            platformFees=pricing["platformFees"],
            deliveryCharges=pricing["deliveryCharges"],
            grandTotalAmount=pricing["grandTotalAmount"]
        )
        order_id = order.save(session=session)
        return order_id
    
    @staticmethod
    def find_order_by_id(orderId:str,session: Any):
        """Find order by order id"""
        query = {"_id": ObjectId(orderId)}

        kwargs = {}
        if session is not None:
            kwargs["session"] = session

        order = mongo.db.orders.find_one(query, **kwargs)
        return serialize_doc(order) if order else None 
    
    @staticmethod
    def find_orders_by_userId(userId):
        """Find order by user id"""
        order = mongo.db.orders.find({"userId": userId})
        return serialize_doc(order) if order else None 
    
    @staticmethod
    def find_pending_order_by_userId(userId: str, session: Any):
        """Find order by user id"""
        order = mongo.db.orders.find_one({"userId": userId, "status": OrderStatus.PENDING_PAYMENT.value},session=session)
        return serialize_doc(order) if order else None 
    
    @staticmethod
    def update_order(orderId: str, update_data: Any, session: Any):
        """Update order data"""
        update_data['updatedAt'] = datetime.utcnow()
        # Flatten nested fields into dot-notation
        flattened_data = flatten(update_data)
        result = mongo.db.orders.update_one(
            {"_id": ObjectId(orderId)},
            {"$set": flattened_data},
            session=session
        )
        return result.modified_count > 0
    
    @staticmethod
    def delete_cart(cartId):
        """Delete Cart from Carts collection of MongoDB"""
        result = mongo.db.carts.delete_one({"_id": ObjectId(cartId)})
        return result.deleted_count > 0
    

