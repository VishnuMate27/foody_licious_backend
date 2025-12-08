import traceback
import requests
from requests.auth import HTTPBasicAuth
from flask import Blueprint, app, request, jsonify, session, current_app
from firebase_admin import auth as firebase_auth
from app.models.user import User
from bson.objectid import ObjectId
from datetime import datetime
import os

auth_bp = Blueprint('auth', __name__)

def get_mongo():
    return current_app.extensions['pymongo'][0]

@auth_bp.route('/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        # Validate required fields
        required_fields = ['id','name','authProvider']
        for field in required_fields:
            if field not in data or not data[field]:
                current_app.logger.warning(
                    "UserRegistrationFailed | field=%s | payload=%s",
                    field, data
                )
                return jsonify({"error": f"{field} is required"}), 400
        id = data['id']
        email = data['email'].lower().strip()
        name = data['name'].strip()
        phone = data['phone']
        authProvider = data['authProvider']
        # Validate email format
        if not User.validate_email(email):
            current_app.logger.warning(
                "UserRegistrationFailed | email=%s | reason=InvalidEmailFormat",
                email
            )
            return jsonify({"error": "Invalid email format"}), 400
        
        # Check if user already exists
        if User.find_by_id(id):
            current_app.logger.warning(
                "UserRegistrationFailed | id=%s | reason=UserAlreadyExists",
                id
            )
            return jsonify({"error": "User with this id already exists"}), 409
        
        user = User(id, email, name, phone, authProvider)
        user_id = user.save()
        
        current_app.logger.info(f"UserRegistrationSuccess | userId={id}")
        return jsonify({
            "message": "User registered successfully",
            "user": {
                "id": user_id,
                "email": email,
                "name": name,
                "phone": phone,
                "authProvider":authProvider,
            }
        }), 201
        
    except Exception as e:
        current_app.logger.error(
            "Error in registering user: %s\n%s", 
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Registration failed", "details": str(e)}), 500

@auth_bp.route('/sendVerificationCodeForRegistration', methods=['POST'])
def send_verification_code_for_registration():
    """Send verification code via Twilio Verify if user does not already exist"""
    try:
        data = request.get_json()

        if 'phone' not in data or not data['phone']:
            current_app.logger.warning(
                "UserSendVerificationCodeForRegistrationFailed | payload=%s",
                data
            )
            return jsonify({"error": "phone is required"}), 400

        phone = data['phone'].strip()

        # ✅ Check if user already exists in MongoDB
        if User.find_by_phone(phone):
            current_app.logger.warning(
                "UserSendVerificationCodeForRegistrationFailed | payload=%s | reason=UserAlreadyExistInMongoDB",
                data
            )
            return jsonify({"error": "User with this phone already exists in MongoDB"}), 409

        # ✅ Check if user already exists in Firebase
        try:
            fb_user = firebase_auth.get_user_by_phone_number(phone)
            if fb_user:
                current_app.logger.warning(
                    "UserSendVerificationCodeForRegistrationFailed | payload=%s | reason=UserAlreadyExistInFirebase",
                    data
                )
                return jsonify({"error": "User with this phone already exists in Firebase"}), 409
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
                "UserSendVerificationCodeForRegistrationSuccess",
            )
            return jsonify({
                "message": "Verification code sent successfully",
                "details": response.json()
            }), 201
        else:
            current_app.logger.warning(
                f"UserSendVerificationCodeForRegistrationFailed | reason={response.status_code}",
            )
            return jsonify({
                "error": "Failed to send verification code",
                "details": response.json()
            }), response.status_code

    except Exception as e:
        current_app.logger.error(
            "UserSendVerificationCodeForRegistrationException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Verification request failed", "details": str(e)}), 500

@auth_bp.route('/verifyCodeAndRegisterWithPhone', methods=['POST'])
def verify_code_and_register_with_phone():
    """Register user with phone number after Twilio Verify + Firebase + MongoDB"""
    try:
        data = request.get_json()

        # Required fields (id removed)
        required_fields = ['name', 'phone', 'authProvider', 'code']
        for field in required_fields:
            if field not in data or not data[field]:
                current_app.logger.warning(
                    "UserVerifyCodeAndRegisterWithPhoneFailed | field=%s | payload=%s",
                    field, data
                )
                return jsonify({"error": f"{field} is required"}), 400

        name = data['name'].strip()
        phone = data['phone'].strip()
        authProvider = data['authProvider']
        code = data['code'].strip()

        # Validate phone format (basic E.164 check)
        if not phone.startswith('+') or not phone[1:].isdigit():
            current_app.logger.warning(
                "UserVerifyCodeAndRegisterWithPhoneFailed | reason=ItemIdRequired",
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
                "UserVerifyCodeAndRegisterWithPhoneFailed | reason=PhoneVerificationFailed",
            )
            return jsonify({
                "error": "Phone verification failed",
                "details": result
            }), 400

        # ✅ Step 2: Check if user already exists in MongoDB
        if User.find_by_phone(phone):
            current_app.logger.warning(
                "UserVerifyCodeAndRegisterWithPhoneFailed | payload=%s | reason=UserAlreadyExistInMongoDB",
                data
            )
            return jsonify({"error": "User with this phone already exists"}), 409

        # ✅ Step 3: Check Firebase user
        try:
            existing_user = firebase_auth.get_user_by_phone_number(phone)
            if not User.find_by_id(existing_user.uid):
                user = User(existing_user.uid, None, name, phone, authProvider)
                saved_id = user.save()
            else:
                saved_id = existing_user.uid

            current_app.logger.warning(
                "UserVerifyCodeAndRegisterWithPhoneFailed | payload=%s | reason=UserAlreadyExistInFirebase",
                data
            )  
            return jsonify({
                "message": "User already exists in Firebase",
                "firebaseUid": existing_user.uid,
                "user": {
                    "id": saved_id,
                    "name": name,
                    "phone": phone,
                    "authProvider": authProvider
                }
            }), 200

        except firebase_auth.UserNotFoundError:
            # ✅ Step 4: No user → create new in Firebase
            fb_user = firebase_auth.create_user(
                phone_number=phone,
                display_name=name
            )

            user = User(fb_user.uid, None, name, phone, authProvider)
            saved_id = user.save()
            current_app.logger.info(
                "UserVerifyCodeAndRegisterWithPhoneSuccess",
            )
            return jsonify({
                "message": "User registered successfully with phone",
                "firebaseUid": fb_user.uid,
                "user": {
                    "id": saved_id,
                    "name": name,
                    "phone": phone,
                    "authProvider": authProvider
                }
            }), 201

    except Exception as e:
        current_app.logger.error(
            "UserVerifyCodeAndRegisterWithPhoneException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Registration failed", "details": str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()

        # Always required
        if 'authProvider' not in data or not data['authProvider']:
            current_app.logger.warning(
                "UserLoginFailed | payload=%s | reason=AuthProviderRequired",
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
                    "UserLoginFailed | field=%s | payload=%s",
                    field, data
                )
                return jsonify({"error": f"{field} is required"}), 400

        # Find user depending on provider
        if authProvider == "email":
            email = data['email'].lower().strip()
            user = User.find_by_email(email)
        else:
            user_id = data['id']
            user = User.find_by_id(user_id)

        if not user:
            current_app.logger.warning(
                "UserLoginFailed | payload=%s | reason=UserNotFound",
                data
            )
            return jsonify({"error": "User not found"}), 404

        # Verify authProvider matches
        if user.get("authProvider") != authProvider:
            current_app.logger.warning(
                "UserLoginFailed | payload=%s | reason=AuthenticationProviderMismatch",
                data
            )
            return jsonify({"error": "Authentication provider mismatch"}), 401

        # Update last_login_at
        User.update_last_login(user["_id"])

        # Fetch updated user
        updated_user = User.find_by_id(user["_id"])
        current_app.logger.info(
            "UserLoginSuccess",
        )
        return jsonify({
            "message": "Login successful",
            "user": {
                "id": updated_user["_id"],
                "email": updated_user["email"],
                "name": updated_user["name"],
                "phone": updated_user["phone"],
                "authProvider": updated_user["authProvider"],
                "address": updated_user["address"],
                "last_login_at": updated_user["last_login_at"].isoformat() + "Z"
            }
        }), 200

    except Exception as e:
        current_app.logger.error(
            "UserLoginException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Login failed", "details": str(e)}), 500

@auth_bp.route('/sendVerificationCodeForLogin', methods=['POST'])
def send_verification_code_for_login():
    """Send verification code via Twilio Verify if user already exist"""
    try:
        data = request.get_json()

        if 'phone' not in data or not data['phone']:
            current_app.logger.warning(
                "UserSendVerificationCodeForLoginFailed | payload=%s | reason=PhoneRequired",
                data
            )
            return jsonify({"error": "phone is required"}), 400

        phone = data['phone'].strip()

        # ✅ Check if user not exists in MongoDB
        if not User.find_by_phone(phone):
            current_app.logger.warning(
                "UserSendVerificationCodeForLoginFailed | payload=%s | reason=UserNotExistInMongoDB",
                data
            )
            return jsonify({"error": "User with this phone does not exists in MongoDB"}), 404

        # ✅ Check if user not already exists in Firebase
        try:
            firebase_auth.get_user_by_phone_number(phone)
        except firebase_auth.UserNotFoundError:
            current_app.logger.warning(
                "UserSendVerificationCodeForLoginFailed | payload=%s | reason=UserNotExistInFirebase",
                data
            )
            return jsonify({"error": "User with this phone does not exists in Firebase"}), 404

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
                "UserSendVerificationCodeForLoginSuccess",
            )
            return jsonify({
                "message": "Verification code sent successfully",
                "details": response.json()
            }), 200
        else:
            current_app.logger.warning(
                "UserSendVerificationCodeForLoginFailed | reason={response.status_code}",
            )
            return jsonify({
                "error": "Failed to send verification code",
                "details": response.json()
            }), response.status_code

    except Exception as e:
        current_app.logger.error(
            "UserSendVerificationCodeForLoginException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Verification request failed", "details": str(e)}), 500

@auth_bp.route('/verifyCodeAndLoginWithPhone', methods=['POST'])
def verify_code_and_login_with_phone():
    """Login user with phone number after Twilio Verify + Firebase + MongoDB"""
    try:
        data = request.get_json()

        # Required fields (id removed)
        required_fields = ['phone', 'authProvider', 'code']
        for field in required_fields:
            if field not in data or not data[field]:
                current_app.logger.warning(
                    "UserVerifyCodeAndLoginWithPhoneFailed | field=%s | payload=%s",
                    field, data
                )
                return jsonify({"error": f"{field} is required"}), 400

        phone = data['phone'].strip()
        authProvider = data['authProvider']
        code = data['code'].strip()

        # Validate phone format (basic E.164 check)
        if not phone.startswith('+') or not phone[1:].isdigit():
            current_app.logger.warning(
                "UserVerifyCodeAndLoginWithPhoneFailed | reason=InvalidPhoneNumber",
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
                "UserVerifyCodeAndLoginWithPhoneFailed | reason=PhoneVerificationFailed",
            )
            return jsonify({
                "error": "Phone verification failed",
                "details": result
            }), 400

        # ✅ Step 2: Check if user not exists in MongoDB
        if not User.find_by_phone(phone):
            current_app.logger.warning(
                "UserVerifyCodeAndLoginWithPhoneFailed | payload=%s | reason=UserAlreadyExistInMongoDB",
                data
            )
            return jsonify({"error": "User with this phone does not exists in MongoDB"}), 404

        # ✅ Step 3: Check Firebase user
        try:
            existing_user = firebase_auth.get_user_by_phone_number(phone)
            if User.find_by_id(existing_user.uid):
                user = User.find_by_id(existing_user.uid)
                User.update_last_login(user["_id"])    
            current_app.logger.info(
                "UserVerifyCodeAndLoginWithPhoneSuccess",
            )
            return jsonify({
                "message": "User login successful!",
                "firebaseUid": existing_user.uid,
                "user": {
                    "id": user["_id"],
                    "name": user["name"],
                    "email": user["email"],
                    "phone": user["phone"],
                    "authProvider": user["authProvider"],
                    "address": user['address']
                }
            }), 200

        except firebase_auth.UserNotFoundError:
            # User not exist in firebase
            current_app.logger.warning(
                "UserVerifyCodeAndLoginWithPhoneFailed | payload=%s | reason=UserNotExists",
                data
            )
            return jsonify({"message": "User with this phone does not exists"}), 404

    except Exception as e:
        current_app.logger.error(
            "UserVerifyCodeAndLoginWithPhoneException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Login failed", "details": str(e)}), 500

