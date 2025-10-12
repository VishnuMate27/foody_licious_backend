from flask import Blueprint, request, jsonify, session, current_app
from app.models.restaurant import Restaurant
from app.utils.decorators import login_required, admin_required
from firebase_admin import auth as firebase_auth
from bson.objectid import ObjectId

restaurant_bp = Blueprint('restaurants', __name__)

def get_mongo():
    return current_app.extensions['pymongo'][0]

def get_bcrypt():
    return current_app.extensions['bcrypt']

@restaurant_bp.route('/profile', methods=['GET'])
def get_profile():
    """Get current restaurant profile"""
    try:
        restaurant_id = session['restaurant_id']
        restaurant = Restaurant.find_by_id(restaurant_id)
        
        if not restaurant:
            return jsonify({"error": "Restaurant not found"}), 404
        
        # Remove sensitive data
        restaurant_data = {
            "id": str(restaurant['_id']),
            "email": restaurant['email'],
            "first_name": restaurant['first_name'],
            "last_name": restaurant['last_name'],
            "role": restaurant.get('role', 'customer'),
            "created_at": restaurant.get('created_at'),
            "email_verified": restaurant.get('email_verified', False),
            "last_login": restaurant.get('last_login')
        }
        
        return jsonify({"restaurant": restaurant_data}), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to get profile", "details": str(e)}), 500

@restaurant_bp.route('/profile', methods=['PUT'])
def update_profile():
    """Update current restaurant profile"""
    try:
        data = request.get_json()
        
        # Fields that can be updated
        required_fields = ['id']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"{field} is required"}), 400
                    
        allowed_fields = ['name', 'email','phone', 'address']
        update_data = {}
        
        for field in allowed_fields:
            if field in data and data[field]:
                update_data[field] = data[field]
        
        id = data['id']       
        
        # Update restaurant
        success = Restaurant.update_restaurant(id, update_data)
        if not success:
            return jsonify({"error": "Failed to update profile"}), 500
        
        # Get updated restaurant data
        restaurant = Restaurant.find_by_id(id)
        restaurant_data = {
            "id": restaurant['_id'],
            "email": restaurant['email'],
            "ownerName": restaurant['ownerName'],
            "name": restaurant['name'],
            "phone": restaurant['phone'],
            "authProvider": restaurant['authProvider'],
            "address": restaurant['address'],
            "photoUrl": restaurant['photoUrl'],
            "description": restaurant['description'],
            "menuItems": restaurant['menuItems'],
        }
        
        return jsonify({
            "message": "Profile updated successfully",
            "restaurant": restaurant_data
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to update profile", "details": str(e)}), 500

@restaurant_bp.route("/delete_restaurant", methods=["POST"])
def delete_restaurant():
    try:
        data = request.get_json()
        
        required_fields = ['id']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"{field} is required"}), 400
            
        id = data['id'] # same for Firebase and MongoDB   

        # --- Step 1: Backup MongoDB restaurant document (for rollback if needed) ---
        restaurant_doc = Restaurant.find_by_id(id)

        # --- Step 2: Delete from Firebase Authentication ---
        try:
            firebase_auth.delete_restaurant(id)
        except firebase_auth.RestaurantNotFoundError:
            return jsonify({"error": "Firebase restaurant not found"}), 404
        except Exception as e:
            return jsonify({"error": f"Firebase deletion failed: {str(e)}"}), 500

        # --- Step 3: Delete from MongoDB ---
        delete_response = Restaurant.delete_restaurant(id)

        if not delete_response:
            # MongoDB deletion failed → rollback: reinsert the restaurant_doc
            if restaurant_doc:
                Restaurant.save(restaurant_doc)
            return jsonify({
                "error": f"Failed to delete restaurant {id} from MongoDB. Rolled back Firebase deletion."
            }), 500

        # --- Both deletions succeeded ---
        return jsonify({"message": f"Successfully deleted restaurant {id}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@restaurant_bp.route('/change-password', methods=['PUT'])
@login_required
def change_password():
    """Change restaurant password"""
    try:
        restaurant_id = session['restaurant_id']
        data = request.get_json()
        
        # Validate required fields
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({"error": "Current password and new password are required"}), 400
        
        current_password = data['current_password']
        new_password = data['new_password']
        
        # Get current restaurant
        restaurant = Restaurant.find_by_id(restaurant_id)
        if not restaurant:
            return jsonify({"error": "Restaurant not found"}), 404
        
        # Verify current password
        if not Restaurant.check_password(restaurant['password'], current_password):
            return jsonify({"error": "Current password is incorrect"}), 400
        
        # Validate new password
        is_valid, message = Restaurant.validate_password(new_password)
        if not is_valid:
            return jsonify({"error": message}), 400
        
        # Hash new password
        bcrypt = get_bcrypt()
        new_password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        # Update password
        success = Restaurant.update_restaurant(restaurant_id, {"password": new_password_hash})
        if not success:
            return jsonify({"error": "Failed to update password"}), 500
        
        return jsonify({"message": "Password changed successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to change password", "details": str(e)}), 500

@restaurant_bp.route('/deactivate', methods=['PUT'])
@login_required
def deactivate_account():
    """Deactivate restaurant account"""
    try:
        restaurant_id = session['restaurant_id']
        
        # Update restaurant status
        success = Restaurant.update_restaurant(restaurant_id, {"is_active": False})
        if not success:
            return jsonify({"error": "Failed to deactivate account"}), 500
        
        # Clear session
        session.clear()
        
        return jsonify({"message": "Account deactivated successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to deactivate account", "details": str(e)}), 500

@restaurant_bp.route('/list', methods=['GET'])
@admin_required
def list_restaurants():
    """List all restaurants (admin only)"""
    try:
        mongo = get_mongo()
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        # Calculate skip value for pagination
        skip = (page - 1) * per_page
        
        # Get restaurants with pagination
        restaurants_cursor = mongo.db.restaurants.find(
            {},
            {"password": 0}  # Exclude password field
        ).skip(skip).limit(per_page).sort("created_at", -1)
        
        restaurants = []
        for restaurant in restaurants_cursor:
            restaurant['id'] = str(restaurant['_id'])
            del restaurant['_id']
            restaurants.append(restaurant)
        
        # Get total count
        total_restaurants = mongo.db.restaurants.count_documents({})
        
        return jsonify({
            "restaurants": restaurants,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total_restaurants,
                "pages": (total_restaurants + per_page - 1) // per_page
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to list restaurants", "details": str(e)}), 500