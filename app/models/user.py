from flask import current_app
from app.routes import mongo
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

class User:
    def __init__(self, id, email, name, phone, authProvider):
        self.id = id
        self.email = email
        self.name = name
        self.phone = phone
        self.email = email
        self.address = {
                    "addressText":"",
                    "city":"",
                    "coordinates":{
                        "type":"Point",
                        "coordinates":[0,0]
                    }
                }
        self.authProvider = authProvider
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def save(self):
        """Save user to database"""
        user_data = {
                "_id": self.id,
                "email": self.email,
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
                "created_at": self.created_at,
                "updated_at": self.updated_at,
        }
        result = mongo.db.users.insert_one(user_data)
        return str(result.inserted_id)

    @staticmethod
    def find_by_email(email):
        """Find user by email"""
        return mongo.db.users.find_one({"email": email})

    @staticmethod
    def find_by_id(user_id):
        """Find user by ID"""
        return mongo.db.users.find_one({"id": user_id})
    
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
    def check_password(hashed_password, password):
        """Check if password matches hash"""
        bcrypt = get_bcrypt()
        return bcrypt.check_password_hash(hashed_password, password)

    @staticmethod
    def update_user(user_id, update_data):
        """Update user data"""
        update_data['updated_at'] = datetime.utcnow()
        result = mongo.db.users.update_one(
            {"id": user_id}, 
            {"$set": update_data}
        )
        return result.modified_count > 0