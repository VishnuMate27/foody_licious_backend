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
        required_fields = ['id','ownerName','authProvider']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"{field} is required"}), 400
        id = data['id']
        email = data['email'].lower().strip()
        ownerName = data['ownerName'].strip()
        phone = data['phone']
        authProvider = data['authProvider']
        photoUrl = data['photoUrl']
        # Validate email format
        if not Restaurant.validate_email(email):
            return jsonify({"error": "Invalid email format"}), 400
        
        # Check if restaurant already exists
        if Restaurant.find_by_id(id):
            return jsonify({"error": "Restaurant with this id already exists"}), 409
        
        restaurant = Restaurant(id, email, ownerName, phone, authProvider, photoUrl)
        restaurant_id = restaurant.save()
        
        return jsonify({
            "message": "Restaurant registered successfully",
            "restaurant": {
                "id": restaurant_id,
                "email": email,
                "ownerName": ownerName,
                "phone": phone,
                "authProvider": authProvider,
                "photoUrl": photoUrl
            }
        }), 201
        
    except Exception as e:
        return jsonify({"error": "Registration failed", "details": str(e)}), 500

@restaurant_auth_bp.route('/sendVerificationCodeForRegistration', methods=['POST'])
def send_verification_code_for_registration():
    """Send verification code via Twilio Verify if user does not already exist"""
    try:
        data = request.get_json()

        if 'phone' not in data or not data['phone']:
            return jsonify({"error": "phone is required"}), 400

        phone = data['phone'].strip()

        # ✅ Check if user already exists in MongoDB
        if Restaurant.find_by_phone(phone):
            return jsonify({"error": "Restaurant with this phone already exists in MongoDB"}), 409

        # ✅ Check if user already exists in Firebase
        try:
            fb_user = firebase_auth.get_user_by_phone_number(phone)
            if fb_user:
                return jsonify({"error": "Restaurant with this phone already exists in Firebase"}), 409
        except firebase_auth.UserNotFoundError:
            pass  # ✅ Safe, means phone is not registered in Firebase

        # 🔹 If no user in MongoDB or Firebase → send Twilio OTP
        TWILIO_SID = os.getenv("TWILIO_SID")
        TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
        VERIFY_SERVICE_SID = os.getenv("VERIFY_SERVICE_SID")

        url = f"https://verify.twilio.com/v2/Services/{VERIFY_SERVICE_SID}/Verifications"

        response = requests.post(
            url,
            data={
                "To": phone,
                "Channel": "sms"
            },
            auth=HTTPBasicAuth(TWILIO_SID, TWILIO_AUTH_TOKEN)
        )

        # Twilio returns 201 Created on success
        if response.status_code == 201:
            return jsonify({
                "message": "Verification code sent successfully",
                "details": response.json()
            }), 201
        else:
            return jsonify({
                "error": "Failed to send verification code",
                "details": response.json()
            }), response.status_code

    except Exception as e:
        return jsonify({"error": "Verification request failed", "details": str(e)}), 500

@restaurant_auth_bp.route('/verifyCodeAndRegisterWithPhone', methods=['POST'])
def verify_code_and_register_with_phone():
    """Register restaurant with phone number after Twilio Verify + Firebase + MongoDB"""
    try:
        data = request.get_json()

        # Required fields (id removed)
        required_fields = ['ownerName', 'phone', 'authProvider', 'code']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"{field} is required"}), 400

        ownerName = data['ownerName'].strip()
        phone = data['phone'].strip()
        authProvider = data['authProvider']
        code = data['code'].strip()

        # Validate phone format (basic E.164 check)
        if not phone.startswith('+') or not phone[1:].isdigit():
            return jsonify({"error": "Invalid phone number format. Use E.164 format (e.g. +919876543210)"}), 400

        # ✅ Step 1: Verify OTP with Twilio
        TWILIO_SID = os.getenv("TWILIO_SID")
        TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
        VERIFY_SERVICE_SID = os.getenv("VERIFY_SERVICE_SID")

        verify_url = f"https://verify.twilio.com/v2/Services/{VERIFY_SERVICE_SID}/VerificationCheck"

        response = requests.post(
            verify_url,
            data={"To": phone, "Code": code},
            auth=HTTPBasicAuth(TWILIO_SID, TWILIO_AUTH_TOKEN)
        )

        result = response.json()

        if response.status_code != 200 or result.get("status") != "approved":
            return jsonify({
                "error": "Phone verification failed",
                "details": result
            }), 400

        # ✅ Step 2: Check if restaurant already exists in MongoDB
        if Restaurant.find_by_phone(phone):
            return jsonify({"error": "Restaurant with this phone already exists"}), 409

        # ✅ Step 3: Check Firebase user
        try:
            existing_user = firebase_auth.get_user_by_phone_number(phone)
            if not Restaurant.find_by_id(existing_user.uid):
                restaurant = Restaurant(existing_user.uid, None, ownerName, phone, authProvider)
                saved_id = restaurant.save()
            else:
                saved_id = existing_user.uid

            return jsonify({
                "message": "Restaurant already exists in Firebase",
                "firebaseUid": existing_user.uid,
                "restaurant": {
                    "id": saved_id,
                    "ownerName": ownerName,
                    "phone": phone,
                    "authProvider": authProvider
                }
            }), 200

        except firebase_auth.UserNotFoundError:
            # ✅ Step 4: No user → create new in Firebase
            fb_user = firebase_auth.create_user(
                phone_number=phone,
                display_name=ownerName
            )

            restaurant = Restaurant(fb_user.uid, None, ownerName, phone, authProvider, None)
            saved_id = restaurant.save()

            return jsonify({
                "message": "User registered successfully with phone",
                "firebaseUid": fb_user.uid,
                "restaurant": {
                    "id": saved_id,
                    "ownerName": ownerName,
                    "phone": phone,
                    "authProvider": authProvider
                }
            }), 201

    except Exception as e:
        print(e);
        return jsonify({"error": "Registration failed", "details": str(e)}), 500

@restaurant_auth_bp.route('/login', methods=['POST'])
def login():
    """Restaurant login endpoint"""
    try:
        data = request.get_json()

        # Always required
        if 'authProvider' not in data or not data['authProvider']:
            return jsonify({"error": "authProvider is required"}), 400

        authProvider = data['authProvider']

        # If provider = email → need email field
        if authProvider == "email":
            required_fields = ['email']
        else:
            required_fields = ['id']

        # Validate required fields
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"{field} is required"}), 400

        # Find restaurant depending on provider
        if authProvider == "email":
            email = data['email'].lower().strip()
            restaurant = Restaurant.find_by_email(email)
        else:
            restaurant_id = data['id']
            restaurant = Restaurant.find_by_id(restaurant_id)

        if not restaurant:
            return jsonify({"error": "User not found"}), 404

        # Verify authProvider matches
        if restaurant.get("authProvider") != authProvider:
            return jsonify({"error": "Authentication provider mismatch"}), 401

        # Update last_login_at
        Restaurant.update_last_login(restaurant["_id"])

        # Fetch updated restaurant
        updated_restaurant = Restaurant.find_by_id(restaurant["_id"])
        
        return jsonify({
            "message": "Login successful",
            "restaurant": {
                "id": updated_restaurant["_id"],
                "email": updated_restaurant["email"],
                "ownerName": updated_restaurant["ownerName"],
                "name": restaurant["name"],
                "phone": updated_restaurant["phone"],
                "authProvider": updated_restaurant["authProvider"],
                "address": updated_restaurant["address"],
                "photoUrl": restaurant["photoUrl"],
                "description": restaurant["description"],
                "menuItems": restaurant["menuItems"],
                "last_login_at": updated_restaurant["last_login_at"].isoformat() + "Z"
            }
        }), 200

    except Exception as e:
        return jsonify({"error": "Login failed", "details": str(e)}), 500

@restaurant_auth_bp.route('/sendVerificationCodeForLogin', methods=['POST'])
def send_verification_code_for_login():
    """Send verification code via Twilio Verify if user already exist"""
    try:
        data = request.get_json()

        if 'phone' not in data or not data['phone']:
            return jsonify({"error": "phone is required"}), 400

        phone = data['phone'].strip()

        # ✅ Check if user not exists in MongoDB
        if not Restaurant.find_by_phone(phone):
            return jsonify({"error": "Restaurant with this phone does not exists in MongoDB"}), 404

        # ✅ Check if user not already exists in Firebase
        try:
            firebase_auth.get_user_by_phone_number(phone)
        except firebase_auth.UserNotFoundError:
            return jsonify({"error": "Restaurant with this phone does not exists in Firebase"}), 404

        # 🔹 If no user in MongoDB or Firebase → send Twilio OTP
        TWILIO_SID = os.getenv("TWILIO_SID")
        TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
        VERIFY_SERVICE_SID = os.getenv("VERIFY_SERVICE_SID")

        url = f"https://verify.twilio.com/v2/Services/{VERIFY_SERVICE_SID}/Verifications"

        response = requests.post(
            url,
            data={
                "To": phone,
                "Channel": "sms"
            },
            auth=HTTPBasicAuth(TWILIO_SID, TWILIO_AUTH_TOKEN)
        )

        # Twilio returns 201 Created on success
        if response.status_code == 201:
            return jsonify({
                "message": "Verification code sent successfully",
                "details": response.json()
            }), 200
        else:
            return jsonify({
                "error": "Failed to send verification code",
                "details": response.json()
            }), response.status_code

    except Exception as e:
        return jsonify({"error": "Verification request failed", "details": str(e)}), 500

@restaurant_auth_bp.route('/verifyCodeAndLoginWithPhone', methods=['POST'])
def verify_code_and_login_with_phone():
    """Login user with phone number after Twilio Verify + Firebase + MongoDB"""
    try:
        data = request.get_json()

        # Required fields (id removed)
        required_fields = ['phone', 'authProvider', 'code']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"{field} is required"}), 400

        phone = data['phone'].strip()
        authProvider = data['authProvider']
        code = data['code'].strip()

        # Validate phone format (basic E.164 check)
        if not phone.startswith('+') or not phone[1:].isdigit():
            return jsonify({"error": "Invalid phone number format. Use E.164 format (e.g. +919876543210)"}), 400

        # ✅ Step 1: Verify OTP with Twilio
        TWILIO_SID = os.getenv("TWILIO_SID")
        TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
        VERIFY_SERVICE_SID = os.getenv("VERIFY_SERVICE_SID")

        verify_url = f"https://verify.twilio.com/v2/Services/{VERIFY_SERVICE_SID}/VerificationCheck"

        response = requests.post(
            verify_url,
            data={"To": phone, "Code": code},
            auth=HTTPBasicAuth(TWILIO_SID, TWILIO_AUTH_TOKEN)
        )

        result = response.json()

        if response.status_code != 200 or result.get("status") != "approved":
            return jsonify({
                "error": "Phone verification failed",
                "details": result
            }), 400

        # ✅ Step 2: Check if user not exists in MongoDB
        if not Restaurant.find_by_phone(phone):
            return jsonify({"error": "Restaurant with this phone does not exists in MongoDB"}), 404

        # ✅ Step 3: Check Firebase user
        try:
            existing_user = firebase_auth.get_user_by_phone_number(phone)
            if Restaurant.find_by_id(existing_user.uid):
                restaurant = Restaurant.find_by_id(existing_user.uid)
                Restaurant.update_last_login(restaurant["_id"])    

            return jsonify({
                "message": "Restaurant login successful!",
                "firebaseUid": existing_user.uid,
                "restaurant": {
                    "id": restaurant["_id"],
                    "ownerName": restaurant["ownerName"],
                    "name": restaurant["name"],
                    "email": restaurant["email"],
                    "phone": restaurant["phone"],
                    "authProvider": restaurant["authProvider"],
                    "address": restaurant['address'],
                    "photoUrl": restaurant["photoUrl"],
                    "description": restaurant["description"],
                    "menuItems": restaurant["menuItems"],
                    "last_login_at": restaurant["last_login_at"].isoformat() + "Z"
                }
            }), 200

        except firebase_auth.UserNotFoundError:
            # User not exist in firebase
            return jsonify({"message": "Restaurant with this phone does not exists"}), 404

    except Exception as e:
        return jsonify({"error": "Login failed", "details": str(e)}), 500
