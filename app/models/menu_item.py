from flask import current_app
from app import mongo
from app.utils.mongo_utils import flatten
from flask_bcrypt import Bcrypt
from bson.objectid import ObjectId
from datetime import datetime
import re

from app.utils.serializers import serialize_doc

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
        item = mongo.db.menuItems.find_one({"_id": ObjectId(item_id)})
        return serialize_doc(item) if item else None
    
    @staticmethod
    def find_item_by_name(restaurant_id, name):
        """Find item by item id"""
        item = mongo.db.menuItems.find_one({"restaurantId": restaurant_id, "name": name})
        return serialize_doc(item) if item else None
        
    @staticmethod
    def find_items_by_restaurant_id(restaurant_id, skip=None, limit=None, count_only=False):
        """
        Find menuItems by restaurant Id with pagination support
        Args:
            restaurant_id: ID of the restaurant
            skip: Number of documents to skip (for pagination)
            limit: Maximum number of documents to return (for pagination)
            count_only: If True, returns only the count of documents
        Returns:
            If count_only is True: returns the total count
            If count_only is False: returns the paginated items
        """
        query = {"restaurantId": restaurant_id}
        
        if count_only:
            return mongo.db.menuItems.count_documents(query)
            
        # Create the base cursor
        cursor = mongo.db.menuItems.find(query)
        
        # Apply pagination if specified
        if skip is not None:
            cursor = cursor.skip(skip)
        if limit is not None:
            cursor = cursor.limit(limit)
            
        # Add sorting by creation date (newest first)
        cursor = cursor.sort("created_at", -1)
            
        items = list(cursor)
        return serialize_doc(items)
    
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
