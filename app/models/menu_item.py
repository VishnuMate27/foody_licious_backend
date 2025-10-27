from flask import current_app
from app import mongo
from app.utils.mongo_utils import flatten
from flask_bcrypt import Bcrypt
from bson.objectid import ObjectId
from datetime import datetime
import re

def get_momgo():
    return current_app.extensions['app']['default']

def get_bcrypt():
    return current_app.extensions['bcrypt']

class MenuItem:
    def __init__(self, restaurantId, name, description, price, images, ingredients):
        self.restaurantId = restaurantId
        self.name = name
        self.description = description
        self.price = price
        self.images = images
        self.availableQuantity = 0
        self.ingredients = ingredients
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
    def save(self):
        """Save MenuItem to database"""
        item_data = {
            "restaurantId": self.restaurantId,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "images": self.images,
            "availableQuantity": self.availableQuantity,
            "ingredients": self.ingredients,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        result = mongo.db.menuItems.insert_one(item_data)
        return str(result.inserted_id)
    
    @staticmethod
    def find_item_by_id(item_id):
        """Find item by item id"""
        return mongo.db.menuItems.find_one({"_id": ObjectId(item_id)})
    
    @staticmethod
    def find_item_by_name(restaurant_id, name):
        """Find item by item id"""
        return mongo.db.menuItems.find_one({"restaurantId": restaurant_id, "name": name})
        
    @staticmethod
    def find_items_by_restaurant_id(restaurant_id):
        """Find menuItems by restaurant Id"""
        return mongo.db.menuItems.find({"restaurantId": restaurant_id})
    
    @staticmethod
    def update_item(item_id, update_data):
        """Update item data"""
        update_data['updated_at'] = datetime.utcnow()
        # Flatten nested fields into dot-notation
        flattened_data = flatten(update_data)
        result = mongo.db.menuItems.update_one(
            {"_id": ObjectId(item_id)}, 
            {"$set": flattened_data}
        )
        return result.modified_count > 0    
    
    @staticmethod
    def delete_item(item_id):
        """Delete MenuItem from MenuItems Collection of MongoDB"""
        result = mongo.db.menuItems.delete_one({"_id": ObjectId(item_id)})
        return result.deleted_count > 0      
