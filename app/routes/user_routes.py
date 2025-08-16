from flask import Blueprint, request, jsonify, session, current_app
from app.models.user import User
from app.utils.decorators import login_required, admin_required
from bson.objectid import ObjectId

user_bp = Blueprint('users', __name__)

def get_mongo():
    return current_app.extensions['pymongo'][0]

def get_bcrypt():
    return current_app.extensions['bcrypt']

@user_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """Get current user profile"""
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Remove sensitive data
        user_data = {
            "id": str(user['_id']),
            "email": user['email'],
            "first_name": user['first_name'],
            "last_name": user['last_name'],
            "role": user.get('role', 'customer'),
            "created_at": user.get('created_at'),
            "email_verified": user.get('email_verified', False),
            "last_login": user.get('last_login')
        }
        
        return jsonify({"user": user_data}), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to get profile", "details": str(e)}), 500

@user_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """Update current user profile"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        # Fields that can be updated
        allowed_fields = ['first_name', 'last_name']
        update_data = {}
        
        for field in allowed_fields:
            if field in data and data[field]:
                update_data[field] = data[field].strip()
        
        if not update_data:
            return jsonify({"error": "No valid fields to update"}), 400
        
        # Update user
        success = User.update_user(user_id, update_data)
        if not success:
            return jsonify({"error": "Failed to update profile"}), 500
        
        # Get updated user data
        user = User.find_by_id(user_id)
        user_data = {
            "id": str(user['_id']),
            "email": user['email'],
            "first_name": user['first_name'],
            "last_name": user['last_name'],
            "role": user.get('role', 'customer')
        }
        
        return jsonify({
            "message": "Profile updated successfully",
            "user": user_data
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to update profile", "details": str(e)}), 500

@user_bp.route('/change-password', methods=['PUT'])
@login_required
def change_password():
    """Change user password"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        # Validate required fields
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({"error": "Current password and new password are required"}), 400
        
        current_password = data['current_password']
        new_password = data['new_password']
        
        # Get current user
        user = User.find_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Verify current password
        if not User.check_password(user['password'], current_password):
            return jsonify({"error": "Current password is incorrect"}), 400
        
        # Validate new password
        is_valid, message = User.validate_password(new_password)
        if not is_valid:
            return jsonify({"error": message}), 400
        
        # Hash new password
        bcrypt = get_bcrypt()
        new_password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        # Update password
        success = User.update_user(user_id, {"password": new_password_hash})
        if not success:
            return jsonify({"error": "Failed to update password"}), 500
        
        return jsonify({"message": "Password changed successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to change password", "details": str(e)}), 500

@user_bp.route('/deactivate', methods=['PUT'])
@login_required
def deactivate_account():
    """Deactivate user account"""
    try:
        user_id = session['user_id']
        
        # Update user status
        success = User.update_user(user_id, {"is_active": False})
        if not success:
            return jsonify({"error": "Failed to deactivate account"}), 500
        
        # Clear session
        session.clear()
        
        return jsonify({"message": "Account deactivated successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to deactivate account", "details": str(e)}), 500

@user_bp.route('/list', methods=['GET'])
@admin_required
def list_users():
    """List all users (admin only)"""
    try:
        mongo = get_mongo()
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        # Calculate skip value for pagination
        skip = (page - 1) * per_page
        
        # Get users with pagination
        users_cursor = mongo.db.users.find(
            {},
            {"password": 0}  # Exclude password field
        ).skip(skip).limit(per_page).sort("created_at", -1)
        
        users = []
        for user in users_cursor:
            user['id'] = str(user['_id'])
            del user['_id']
            users.append(user)
        
        # Get total count
        total_users = mongo.db.users.count_documents({})
        
        return jsonify({
            "users": users,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total_users,
                "pages": (total_users + per_page - 1) // per_page
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to list users", "details": str(e)}), 500