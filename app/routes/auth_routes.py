from flask import Blueprint, request, jsonify, session, current_app
from app.models.user import User
from bson.objectid import ObjectId
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

def get_mongo():
    return current_app.extensions['pymongo'][0]

@auth_bp.route('/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        print("I am here0")
        # Validate required fields
        required_fields = ['id','name','authProvider']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"{field} is required"}), 400
        print("I am here0.1")
        id = data['id']
        email = data['email'].lower().strip()
        name = data['name'].strip()
        phone = data['phone']
        authProvider = data['authProvider']
        print("I am here0.2")
        # Validate email format
        if not User.validate_email(email):
            return jsonify({"error": "Invalid email format"}), 400
        print("I am here0.3")
        
        # Check if user already exists
        if User.find_by_id(id):
            return jsonify({"error": "User with this id already exists"}), 409
        
        user = User(id, email, name, phone, authProvider)
        user_id = user.save()
        
        return jsonify({
            "message": "User registered successfully",
            "user": {
                "id": user_id,
                "email": email,
                "name": name,
                "phone": phone,
            }
        }), 201
        
    except Exception as e:
        return jsonify({"error": "Registration failed", "details": str(e)}), 500

# @auth_bp.route('/login', methods=['POST'])
# def login():
#     """User login endpoint"""
#     try:
#         data = request.get_json()
        
#         # Validate required fields
#         if not data.get('email') or not data.get('password'):
#             return jsonify({"error": "Email and password are required"}), 400
        
#         email = data['email'].lower().strip()
#         password = data['password']
        
#         # Find user by email
#         user = User.find_by_email(email)
#         if not user:
#             return jsonify({"error": "Invalid credentials"}), 401
        
#         # Check if user is active
#         if not user.get('is_active', True):
#             return jsonify({"error": "Account is deactivated"}), 401
        
#         # Verify password
#         if not User.check_password(user['password'], password):
#             return jsonify({"error": "Invalid credentials"}), 401
        
#         # Create session
#         user_id = str(user['_id'])
#         session['user_id'] = user_id
#         session['user_email'] = user['email']
#         session['user_role'] = user.get('role', 'customer')
        
#         # Update last login
#         mongo = get_mongo()
#         mongo.db.users.update_one(
#             {"_id": user['_id']},
#             {"$set": {"last_login": datetime.utcnow()}}
#         )
        
#         return jsonify({
#             "message": "Login successful",
#             "user": {
#                 "id": user_id,
#                 "email": user['email'],
#                 "first_name": user['first_name'],
#                 "last_name": user['last_name'],
#                 "role": user.get('role', 'customer')
#             }
#         }), 200
        
#     except Exception as e:
#         return jsonify({"error": "Login failed", "details": str(e)}), 500

# @auth_bp.route('/logout', methods=['POST'])
# def logout():
#     """Logout user and clear session"""
#     try:
#         session.clear()
#         return jsonify({"message": "Successfully logged out"}), 200
        
#     except Exception as e:
#         return jsonify({"error": "Logout failed", "details": str(e)}), 500

# @auth_bp.route('/check-session', methods=['GET'])
# def check_session():
#     """Check if user is logged in"""
#     try:
#         if 'user_id' not in session:
#             return jsonify({"authenticated": False}), 401
        
#         user = User.find_by_id(session['user_id'])
#         if not user or not user.get('is_active', True):
#             session.clear()
#             return jsonify({"authenticated": False}), 401
        
#         return jsonify({
#             "authenticated": True,
#             "user": {
#                 "id": session['user_id'],
#                 "email": session['user_email'],
#                 "first_name": user['first_name'],
#                 "last_name": user['last_name'],
#                 "role": session.get('user_role', 'customer')
#             }
#         }), 200
        
#     except Exception as e:
#         return jsonify({"error": "Session check failed", "details": str(e)}), 500