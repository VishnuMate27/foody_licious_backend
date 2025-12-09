from flask import current_app
from app import mongo
from app.utils.mongo_utils import flatten 
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from bson.objectid import ObjectId
from datetime import datetime
import re

# Get extensions from current app context
def get_mongo():
    return current_app.extensions['pymongo']['default']

def get_bcrypt():
    return current_app.extensions['bcrypt']

class Restaurant:
    def __init__(self, id, email, ownerName, phone, authProvider, photoUrl):
        self.id = id
        self.email = email
        self.ownerName = ownerName
        self.name = ""
        self.phone = phone
        self.address = {
                    "addressText":"",
                    "city":"",
                    "coordinates":{
                        "type":"Point",
                        "coordinates":[0,0]
                    }
                }
        self.authProvider = authProvider
        self.photoUrl = photoUrl
        self.description = "description"
        self.menuItems = []
        self.receivedOrders = []
        self.receivedFeedback = []
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.last_login_at = datetime.utcnow()

    def save(self):
        """Save restaurant to database"""
        restaurant_data = {
                "_id": self.id,
                "email": self.email,
                "ownerName": self.ownerName,
                "name": self.name,
                "phone": self.phone,
                "address": {
                    "addressText":"",
                    "city":"",
                    "coordinates":{
                        "type":"Point",
                        "coordinates":[0,0]
                    }
                },
                "authProvider": self.authProvider,
                "photoUrl": self.photoUrl,
                "description": self.description,
                "menuItems": self.menuItems,
                "receivedOrders": self.receivedOrders,
                "receivedFeedback": self.receivedFeedback,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "last_login_at": self.last_login_at
        }
        result = mongo.db.restaurants.insert_one(restaurant_data)
        return str(result.inserted_id)

    @staticmethod
    def find_by_email(email):
        """Find restaurant by email"""
        return mongo.db.restaurants.find_one({"email": email})

    @staticmethod
    def find_by_phone(phone):
        """Find restaurant by phone"""
        return mongo.db.restaurants.find_one({"phone": phone})
    
    @staticmethod
    def find_by_id(restaurant_id):
        """Find restaurant by ID"""
        return mongo.db.restaurants.find_one({"_id": restaurant_id})
    
    @staticmethod
    def find_by_city(city):
        """Find restaurant by city"""
        restaurants = list(
            mongo.db.restaurants.find({"address.city": city})
        )
        return restaurants
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    @staticmethod
    def validate_password(password):
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        return True, "Password is valid"

    @staticmethod
    def update_restaurant(restaurant_id, update_data):
        """Update restaurant data"""
        update_data['updated_at'] = datetime.utcnow()
        # Flatten nested fields into dot-notation
        flattened_data = flatten(update_data)
        result = mongo.db.restaurants.update_one(
            {"_id": restaurant_id}, 
            {"$set": flattened_data}
        )
        return result.modified_count > 0
    
    @staticmethod
    def delete_restaurant(restaurant_id):
        """Delete restaurant data from MongoDB"""
        result = mongo.db.restaurants.delete_one({"_id": restaurant_id})
        return result.deleted_count > 0
    
    @staticmethod
    def update_last_login(restaurant_id):
        """Update last_login_at for restaurant"""
        result = mongo.db.restaurants.update_one(
            {"_id": restaurant_id},
            {"$set": {"last_login_at": datetime.utcnow()}}
        )
        return result.modified_count > 0   