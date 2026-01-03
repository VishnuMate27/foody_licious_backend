from datetime import datetime
from bson import ObjectId
from app import mongo
from app.utils.mongo_utils import flatten
from app.utils.serializers import serialize_doc


class Cart:
    def __init__(self, restaurantId, userId, items):
        self.restaurantId = restaurantId
        self.userId = userId
        self.items = items
        self.totalAmount = 0
        self.status = "active"
        self.createdAt = datetime.utcnow()
        self.updatedAt = datetime.utcnow()
        
        
    def save(self):
        """Save Cart to database"""
        cart_data = {
            "restaurantId": self.restaurantId,
            "userId": self.userId,
            "items": self.items,
            "totalAmount": self.totalAmount,
            "status": self.status,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
        }
        result = mongo.db.carts.insert_one(cart_data)
        return str(result.inserted_id)
    
    @staticmethod
    def find_cart_by_id(cartId):
        """Find cart by cart id"""
        cart = mongo.db.carts.find_one({"_id": ObjectId(cartId)})
        return serialize_doc(cart) if cart else None    
    
    @staticmethod
    def find_cart_by_userId(userId):
        """Find cart by user id"""
        cart = mongo.db.carts.find_one({"userId": userId})
        return serialize_doc(cart) if cart else None 
    
    @staticmethod
    def update_cart(cartId, update_data):
        """Update cart data"""
        update_data['updatedAt'] = datetime.utcnow()
        # Flatten nested fields into dot-notation
        flattened_data = flatten(update_data)
        result = mongo.db.carts.update_one(
            {"_id": ObjectId(cartId)},
            {"$set": flattened_data}
        )
        return result.modified_count > 0
    
    @staticmethod
    def delete_cart(cartId):
        """Delete Cart from Carts collection of MongoDB"""
        result = mongo.db.carts.delete_one({"_id": ObjectId(cartId)})
        return result.deleted_count > 0
