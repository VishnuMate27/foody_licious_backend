import random
import traceback
import boto3
import requests
from requests.auth import HTTPBasicAuth
from flask import Blueprint, app, request, jsonify, session, current_app
from firebase_admin import auth as firebase_auth
from app.models.restaurant import Restaurant
from bson.objectid import ObjectId
from datetime import datetime, time
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
                current_app.logger.warning(
                    "RestaurantRegistrationFailed | field=%s | payload=%s",
                    field, data
                )
                return jsonify({"error": f"{field} is required"}), 400
        id = data['id']
        email = data['email'].lower().strip()
        ownerName = data['ownerName'].strip()
        phone = data['phone']
        authProvider = data['authProvider']
        photoUrl = data.get('photoUrl') if 'photoUrl' in data and data['photoUrl'] else None
        # Validate email format
        if not Restaurant.validate_email(email):
            current_app.logger.warning(
                "RestaurantRegistrationFailed | email=%s | reason=InvalidEmailFormat",
                email
            )
            return jsonify({"error": "Invalid email format"}), 400
        
        # Check if restaurant already exists
        if Restaurant.find_by_id(id):
            current_app.logger.warning(
                "RestaurantRegistrationFailed | id=%s | reason=RestaurantAlreadyExists",
                id
            )
            return jsonify({"error": "Restaurant with this id already exists"}), 409
        
        restaurant = Restaurant(id, email, ownerName, phone, authProvider, photoUrl)
        restaurant_id = restaurant.save()
        current_app.logger.info("RestaurantRegistrationSuccess | restaurantId={id}")
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
        current_app.logger.error(
            "Error in registering restaurant: %s\n%s", 
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Registration failed", "details": str(e)}), 500

@restaurant_auth_bp.route('/sendVerificationCodeForRegistration', methods=['POST'])
def send_verification_code_for_registration():
    """Send verification code via Twilio Verify if user does not already exist"""
    try:
        data = request.get_json()

        if 'phone' not in data or not data['phone']:
            current_app.logger.warning(
                "RestaurantSendVerificationCodeForRegistrationFailed | payload=%s",
                data
            )
            return jsonify({"error": "phone is required"}), 400

        phone = data['phone'].strip()

        # ✅ Check if user already exists in MongoDB
        if Restaurant.find_by_phone(phone):
            current_app.logger.warning(
                "RestaurantSendVerificationCodeForRegistrationFailed | payload=%s | reason=RestaurantAlreadyExistInMongoDB",
                data
            )
            return jsonify({"error": "Restaurant with this phone already exists in MongoDB"}), 409

        # ✅ Check if user already exists in Firebase
        try:
            fb_user = firebase_auth.get_user_by_phone_number(phone)
            if fb_user:
                current_app.logger.warning(
                    "RestaurantSendVerificationCodeForRegistrationFailed | payload=%s | reason=RestaurantAlreadyExistInFirebase",
                    data
                )
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
            current_app.logger.info(
                "RestaurantSendVerificationCodeForRegistrationSuccess",
            )
            return jsonify({
                "message": "Verification code sent successfully",
                "details": response.json()
            }), 201
        else:
            current_app.logger.warning(
                f"RestaurantSendVerificationCodeForRegistrationFailed | reason={response.status_code}",
            )    
            return jsonify({
                "error": "Failed to send verification code",
                "details": response.json()
            }), response.status_code

    except Exception as e:
        current_app.logger.error(
            "RestaurantSendVerificationCodeForRegistrationException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Verification request failed", "details": str(e)}), 500
# @restaurant_auth_bp.route('/sendVerificationCodeForRegistration', methods=['POST'])
# def send_verification_code_for_registration():
#     """Send OTP via AWS SNS instead of Twilio"""
#     try:
#         data = request.get_json()

#         if 'phone' not in data or not data['phone']:
#             current_app.logger.warning(
#                 "RestaurantSendVerificationCodeForRegistrationFailed | payload=%s",
#                 data
#             )
#             return jsonify({"error": "phone is required"}), 400

#         phone = data['phone'].strip()

#         # 🔍 Check MongoDB
#         if Restaurant.find_by_phone(phone):
#             current_app.logger.warning(
#                 "RestaurantSendVerificationCodeForRegistrationFailed | reason=RestaurantAlreadyExistInMongoDB",
#                 data
#             )
#             return jsonify({"error": "Restaurant with this phone already exists in MongoDB"}), 409

#         # 🔍 Check Firebase
#         try:
#             firebase_auth.get_user_by_phone_number(phone)
#             current_app.logger.warning(
#                 "RestaurantSendVerificationCodeForRegistrationFailed | reason=RestaurantAlreadyExistInFirebase",
#                 data
#             )
#             return jsonify({"error": "Restaurant with this phone already exists in Firebase"}), 409
#         except firebase_auth.UserNotFoundError:
#             pass

#         # 🎯 Generate OTP
#         otp = random.randint(100000, 999999)

#         # 🟡 Store OTP (use Redis later)
#         otp_store[phone] = {
#             "otp": otp,
#             "timestamp": time.time()
#         }

#         # 🚀 Send SMS using AWS SNS
#         sns = boto3.client("sns", region_name=os.getenv("AWS_REGION"))

#         sns.publish(
#             PhoneNumber=phone,
#             Message=f"Your verification code is {otp}"
#         )

#         current_app.logger.info(
#             "RestaurantSendVerificationCodeForRegistrationSuccess | phone=%s", phone
#         )

#         return jsonify({
#             "message": "Verification code sent successfully",
#             "details": {
#                 "otp_debug": otp   # REMOVE in production
#             }
#         }), 201

#     except Exception as e:
#         current_app.logger.error(
#             "RestaurantSendVerificationCodeForRegistrationException | error=%s\n%s",
#             str(e),
#             traceback.format_exc()
#         )
#         return jsonify({"error": "Verification request failed", "details": str(e)}), 500

@restaurant_auth_bp.route('/verifyCodeAndRegisterWithPhone', methods=['POST'])
def verify_code_and_register_with_phone():
    """Register restaurant with phone number after Twilio Verify + Firebase + MongoDB"""
    try:
        data = request.get_json()

        # Required fields (id removed)
        required_fields = ['ownerName', 'phone', 'authProvider', 'code']
        for field in required_fields:
            if field not in data or not data[field]:
                current_app.logger.warning(
                    "RestaurantVerifyCodeAndRegisterWithPhoneFailed | field=%s | payload=%s",
                    field, data
                )
                return jsonify({"error": f"{field} is required"}), 400

        ownerName = data['ownerName'].strip()
        phone = data['phone'].strip()
        authProvider = data['authProvider']
        code = data['code'].strip()

        # Validate phone format (basic E.164 check)
        if not phone.startswith('+') or not phone[1:].isdigit():
            current_app.logger.warning(
                "RestaurantVerifyCodeAndRegisterWithPhoneFailed | reason=ItemIdRequired",
            )
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
            current_app.logger.warning(
                "RestaurantVerifyCodeAndRegisterWithPhoneFailed | reason=PhoneVerificationFailed",
            )
            return jsonify({
                "error": "Phone verification failed",
                "details": result
            }), 400

        # ✅ Step 2: Check if restaurant already exists in MongoDB
        if Restaurant.find_by_phone(phone):
            current_app.logger.warning(
                "RestaurantVerifyCodeAndRegisterWithPhoneFailed | payload=%s | reason=RestaurantAlreadyExistInMongoDB",
                data
            )            
            return jsonify({"error": "Restaurant with this phone already exists"}), 409

        # ✅ Step 3: Check Firebase user
        try:
            existing_user = firebase_auth.get_user_by_phone_number(phone)
            if not Restaurant.find_by_id(existing_user.uid):
                restaurant = Restaurant(existing_user.uid, None, ownerName, phone, authProvider)
                saved_id = restaurant.save()
            else:
                saved_id = existing_user.uid

            current_app.logger.warning(
                "RestaurantVerifyCodeAndRegisterWithPhoneFailed | payload=%s | reason=RestaurantAlreadyExistInFirebase",
                data
            )  
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
            current_app.logger.info(
                "RestaurantVerifyCodeAndRegisterWithPhoneSuccess",
            )
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
        current_app.logger.error(
            "RestaurantVerifyCodeAndRegisterWithPhoneException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Registration failed", "details": str(e)}), 500
# @restaurant_auth_bp.route('/verifyCodeAndRegisterWithPhone', methods=['POST'])
# def verify_code_and_register_with_phone():
#     """Verify AWS SNS OTP + Register restaurant with Firebase & MongoDB"""
#     try:
#         data = request.get_json()

#         required_fields = ['ownerName', 'phone', 'authProvider', 'code']
#         for field in required_fields:
#             if field not in data or not data[field]:
#                 current_app.logger.warning(
#                     "RestaurantVerifyCodeAndRegisterWithPhoneFailed | field=%s | payload=%s",
#                     field, data
#                 )
#                 return jsonify({"error": f"{field} is required"}), 400

#         ownerName = data['ownerName'].strip()
#         phone = data['phone'].strip()
#         authProvider = data['authProvider']
#         code = data['code'].strip()

#         # 🟡 Validate phone format
#         if not phone.startswith('+') or not phone[1:].isdigit():
#             return jsonify({"error": "Invalid phone number format"}), 400

#         # 🟡 Step 1: Verify OTP locally
#         if phone not in otp_store:
#             return jsonify({"error": "No OTP found for this phone"}), 400

#         stored = otp_store[phone]

#         # Expiry 5 mins
#         if time.time() - stored["timestamp"] > 300:
#             return jsonify({"error": "OTP expired"}), 400

#         if str(stored["otp"]) != str(code):
#             return jsonify({"error": "Invalid OTP"}), 400

#         # OTP success → delete from store
#         del otp_store[phone]

#         # 🟡 Step 2: MongoDB check
#         if Restaurant.find_by_phone(phone):
#             return jsonify({"error": "Restaurant with this phone already exists"}), 409

#         # 🟡 Step 3: Firebase logic
#         try:
#             existing_user = firebase_auth.get_user_by_phone_number(phone)

#             # Create Mongo record if missing
#             if not Restaurant.find_by_id(existing_user.uid):
#                 restaurant = Restaurant(existing_user.uid, None, ownerName, phone, authProvider)
#                 saved_id = restaurant.save()
#             else:
#                 saved_id = existing_user.uid

#             return jsonify({
#                 "message": "Restaurant already exists in Firebase",
#                 "firebaseUid": existing_user.uid,
#                 "restaurant": {
#                     "id": saved_id,
#                     "ownerName": ownerName,
#                     "phone": phone,
#                     "authProvider": authProvider
#                 }
#             }), 200

#         except firebase_auth.UserNotFoundError:
#             # 🟡 Step 4: Create new Firebase user
#             fb_user = firebase_auth.create_user(
#                 phone_number=phone,
#                 display_name=ownerName
#             )

#             restaurant = Restaurant(
#                 fb_user.uid, None, ownerName, phone, authProvider, None
#             )
#             saved_id = restaurant.save()

#             return jsonify({
#                 "message": "User registered successfully with phone",
#                 "firebaseUid": fb_user.uid,
#                 "restaurant": {
#                     "id": saved_id,
#                     "ownerName": ownerName,
#                     "phone": phone,
#                     "authProvider": authProvider
#                 }
#             }), 201

#     except Exception as e:
#         current_app.logger.error(
#             "RestaurantVerifyCodeAndRegisterWithPhoneException | error=%s\n%s",
#             str(e),
#             traceback.format_exc()
#         )
#         return jsonify({"error": "Registration failed", "details": str(e)}), 500

@restaurant_auth_bp.route('/login', methods=['POST'])
def login():
    """Restaurant login endpoint"""
    try:
        data = request.get_json()

        # Always required
        if 'authProvider' not in data or not data['authProvider']:
            current_app.logger.warning(
                "RestaurantLoginFailed | payload=%s | reason=AuthProviderRequired",
                data
            )            
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
                current_app.logger.warning(
                    "RestaurantLoginFailed | field=%s | payload=%s",
                    field, data
                )
                return jsonify({"error": f"{field} is required"}), 400

        # Find restaurant depending on provider
        if authProvider == "email":
            email = data['email'].lower().strip()
            restaurant = Restaurant.find_by_email(email)
        else:
            restaurant_id = data['id']
            restaurant = Restaurant.find_by_id(restaurant_id)

        if not restaurant:
            current_app.logger.warning(
                "RestaurantLoginFailed | payload=%s | reason=RestaurantNotFound",
                data
            )
            return jsonify({"error": "Restaurant not found"}), 404

        # Verify authProvider matches
        if restaurant.get("authProvider") != authProvider:
            current_app.logger.warning(
                "RestaurantLoginFailed | payload=%s | reason=AuthenticationProviderMismatch",
                data
            )    
            return jsonify({"error": "Authentication provider mismatch"}), 401

        # Update last_login_at
        Restaurant.update_last_login(restaurant["_id"])

        # Fetch updated restaurant
        updated_restaurant = Restaurant.find_by_id(restaurant["_id"])
        current_app.logger.info(
            "RestaurantLoginSuccess",
        )        
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
        current_app.logger.error(
            "RestaurantLoginException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Login failed", "details": str(e)}), 500

@restaurant_auth_bp.route('/sendVerificationCodeForLogin', methods=['POST'])
def send_verification_code_for_login():
    """Send verification code via Twilio Verify if user already exist"""
    try:
        data = request.get_json()

        if 'phone' not in data or not data['phone']:
            current_app.logger.warning(
                "RestaurantSendVerificationCodeForLoginFailed | payload=%s | reason=PhoneRequired",
                data
            )           
            return jsonify({"error": "phone is required"}), 400

        phone = data['phone'].strip()

        # ✅ Check if user not exists in MongoDB
        if not Restaurant.find_by_phone(phone):
            current_app.logger.warning(
                "RestaurantSendVerificationCodeForLoginFailed | payload=%s | reason=RestaurantNotExistInMongoDB",
                data
            )
            return jsonify({"error": "Restaurant with this phone does not exists in MongoDB"}), 404

        # ✅ Check if user not already exists in Firebase
        try:
            firebase_auth.get_user_by_phone_number(phone)
        except firebase_auth.UserNotFoundError:
            current_app.logger.warning(
                "RestaurantSendVerificationCodeForLoginFailed | payload=%s | reason=RestaurantNotExistInFirebase",
                data
            )
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
            current_app.logger.info(
                "RestaurantSendVerificationCodeForLoginSuccess",
            )
            return jsonify({
                "message": "Verification code sent successfully",
                "details": response.json()
            }), 200
        else:
            current_app.logger.warning(
                "RestaurantSendVerificationCodeForLoginFailed | reason={response.status_code}",
            )
            return jsonify({
                "error": "Failed to send verification code",
                "details": response.json()
            }), response.status_code

    except Exception as e:
        current_app.logger.error(
            "RestaurantSendVerificationCodeForLoginException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
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
                current_app.logger.warning(
                    "RestaurantVerifyCodeAndLoginWithPhoneFailed | field=%s | payload=%s",
                    field, data
                )
                return jsonify({"error": f"{field} is required"}), 400

        phone = data['phone'].strip()
        authProvider = data['authProvider']
        code = data['code'].strip()

        # Validate phone format (basic E.164 check)
        if not phone.startswith('+') or not phone[1:].isdigit():
            current_app.logger.warning(
                "RestaurantVerifyCodeAndLoginWithPhoneFailed | reason=InvalidPhoneNumber",
            )            
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
            current_app.logger.warning(
                "RestaurantVerifyCodeAndLoginWithPhoneFailed | reason=PhoneVerificationFailed",
            )
            return jsonify({
                "error": "Phone verification failed",
                "details": result
            }), 400

        # ✅ Step 2: Check if user not exists in MongoDB
        if not Restaurant.find_by_phone(phone):
            current_app.logger.warning(
                "RestaurantVerifyCodeAndLoginWithPhoneFailed | payload=%s | reason=RestaurantAlreadyExistInMongoDB",
                data
            )
            return jsonify({"error": "Restaurant with this phone does not exists in MongoDB"}), 404

        # ✅ Step 3: Check Firebase user
        try:
            existing_user = firebase_auth.get_user_by_phone_number(phone)
            if Restaurant.find_by_id(existing_user.uid):
                restaurant = Restaurant.find_by_id(existing_user.uid)
                Restaurant.update_last_login(restaurant["_id"])    
            current_app.logger.info(
                "RestaurantVerifyCodeAndLoginWithPhoneSuccess",
            )  
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
            current_app.logger.warning(
                "RestaurantVerifyCodeAndLoginWithPhoneFailed | payload=%s | reason=RestaurantNotExists",
                data
            )
            return jsonify({"message": "Restaurant with this phone does not exists"}), 404

    except Exception as e:
        current_app.logger.error(
            "RestaurantVerifyCodeAndLoginWithPhoneException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Login failed", "details": str(e)}), 500
