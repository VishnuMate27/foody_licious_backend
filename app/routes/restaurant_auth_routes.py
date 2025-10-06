import requests
from requests.auth import HTTPBasicAuth
from flask import Blueprint, request, jsonify, session, current_app
from firebase_admin import auth as firebase_auth
from app.models.restaurant import Restaurant
from bson.objectid import ObjectId
from datetime import datetime
import os

restaurant_auth_bp = Blueprint('restaurant_auth', __name__)

def get_mongo():
    return current_app.extensions['pymongo'][0]

@restaurant_auth_bp.route('/register', methods=['POST'])
def register():
    """Restaurant registration endpoint"""
    try:
        data = request.get_json()
        # Validate required fields
        required_fields = ['id','name','authProvider']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"{field} is required"}), 400
        id = data['id']
        email = data['email'].lower().strip()
        name = data['name'].strip()
        phone = data['phone']
        authProvider = data['authProvider']
        # Validate email format
        if not Restaurant.validate_email(email):
            return jsonify({"error": "Invalid email format"}), 400
        
        # Check if restaurant already exists
        if Restaurant.find_by_id(id):
            return jsonify({"error": "Restaurant with this id already exists"}), 409
        
        restaurant = Restaurant(id, email, name, phone, authProvider)
        restaurant_id = restaurant.save()
        
        return jsonify({
            "message": "Restaurant registered successfully",
            "restaurant": {
                "id": restaurant_id,
                "email": email,
                "name": name,
                "phone": phone,
                "authProvider":authProvider,
            }
        }), 201
        
    except Exception as e:
        return jsonify({"error": "Registration failed", "details": str(e)}), 500
