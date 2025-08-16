from functools import wraps
from flask import jsonify, session
from app.models.user import User

def login_required(f):
    """Decorator to require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required"}), 401
        
        # Verify user still exists and is active
        user = User.find_by_id(session['user_id'])
        if not user or not user.get('is_active', True):
            session.clear()
            return jsonify({"error": "User not found or inactive"}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required"}), 401
        
        user = User.find_by_id(session['user_id'])
        if not user or user.get('role') != 'admin':
            return jsonify({"error": "Admin access required"}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({"error": "Authentication required"}), 401
            
            user = User.find_by_id(session['user_id'])
            if not user or user.get('role') != required_role:
                return jsonify({"error": f"{required_role} access required"}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator