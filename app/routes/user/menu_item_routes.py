import traceback
from flask import Blueprint, app, json, request, jsonify, session, current_app
from app.core.constansts import ALLOWED_IMAGE_EXTENSIONS, S3_FOLDER_MENU_ITEMS, S3_FOLDER_RESTAURANTS
from app.models.menu_item import MenuItem
from app.models.restaurant import Restaurant
from app.models.user import User
from app.utils.aws_utils import MAX_IMAGES, delete_images_from_s3, delete_s3_folder, upload_images_to_s3
from app.utils.decorators import login_required, admin_required
from firebase_admin import auth as firebase_auth
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
from app.extensions import s3_client, S3_BUCKET, S3_REGION
from botocore.exceptions import NoCredentialsError, ClientError

user_menu_item_bp = Blueprint('userMenuItems', __name__)

@user_menu_item_bp.route('/allItems', methods=['GET'])
def get_all_items_in_restaurants_of_users_city():
    """Get all items in restaurants of users city"""
    try:
        # Get user_id from query params 
        user_id = request.args.get('user_id')
        # Get pagination parameters with defaults
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))
        
        # Validate pagination parameters
        if page < 1:
            current_app.logger.warning(f"Failed to Get all items in restaurants of users city | userId={user_id} | Page number must be greater than 0")
            return jsonify({"error": "Page number must be greater than 0"}), 400
        if page_size < 1:
            current_app.logger.warning(f"Failed to Get all items in restaurants of users city | userId={user_id} | Page size must be greater than 0")            
            return jsonify({"error": "Page size must be greater than 0"}), 400
        if page_size > 100:  # Limit maximum page size
            current_app.logger.warning(f"Failed to Get all items in restaurants of users city | userId={user_id} | Page size cannot exceed 100")
            return jsonify({"error": "Page size cannot exceed 100"}), 400
        
        if not user_id:
            current_app.logger.warning(f"Failed to Get all items in restaurants of users city | userId={user_id} | user_id is required")
            return jsonify({"error": "user_id is required"}), 400

        # Get the user's city location    
        user = User.find_by_id(user_id)
        
        city = user['address']['city'] 
        
        # Find out all restaurants in user's city
        restaurants = Restaurant.find_by_city(city)
        restaurant_ids = [r["_id"] for r in restaurants]

        # Count total items
        total_items = MenuItem.find_items_by_restaurant_ids(restaurant_ids, count_only=True)
        
        total_pages = (total_items + page_size - 1) // page_size
        # Calculate skip and limit for pagination
        skip = (page - 1) * page_size
        
        # Fetch paginated menu items
        items_cursor = MenuItem.find_items_by_restaurant_ids(restaurant_ids, skip=skip, limit=page_size)

        items = list(items_cursor)
        
        # Fetch corresponding restaurant name
        for item in items:
            restaurant = Restaurant.find_by_id(item['restaurantId'])
            item['restaurantName'] = restaurant['name']
        
        current_app.logger.info(
            "getAllItemsInRestaurantsOfUsersCitySuccess | user_id=%s",
            user_id
        )
        # Show it to user
        return jsonify({
            "message": "Fetched menu items successfully",
            "menuItems": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }), 200 
    except Exception as e:
        current_app.logger.error(
            "Error in get all items in restaurants of users city: %s\n%s", 
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Failed to get all items in restaurants of users city", "details": str(e)}), 500      
            
@user_menu_item_bp.route('/allItemsInRestaurant', methods=['GET'])
def get_all_items_in_restaurant():
    """Get all items in restaurant"""
    try:
        # Get restaurant_id from query params 
        restaurant_id = request.args.get('restaurant_id')
        # Get pagination parameters with defaults
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))
        
        # Validate pagination parameters
        if page < 1:
            current_app.logger.warning(f"Failed to Get all items in restaurant | restaurantId={restaurant_id} | Page number must be greater than 0")
            return jsonify({"error": "Page number must be greater than 0"}), 400
        if page_size < 1:
            current_app.logger.warning(f"Failed to Get all items in restaurant | restaurantId={restaurant_id} | Page size must be greater than 0")            
            return jsonify({"error": "Page size must be greater than 0"}), 400
        if page_size > 100:  # Limit maximum page size
            current_app.logger.warning(f"Failed to Get all items in restaurant | restaurantId={restaurant_id} | Page size cannot exceed 100")
            return jsonify({"error": "Page size cannot exceed 100"}), 400
        
        if not restaurant_id:
            current_app.logger.warning(f"Failed to Get all items in restaurant | restaurantId={restaurant_id} | restaurant_id is required")
            return jsonify({"error": "restaurant_id is required"}), 400

        # Count total items
        total_items = MenuItem.find_items_by_restaurant_id(restaurant_id, count_only=True)
        
        total_pages = (total_items + page_size - 1) // page_size
        # Calculate skip and limit for pagination
        skip = (page - 1) * page_size
        
        # Fetch paginated menu items
        items_cursor = MenuItem.find_items_by_restaurant_id(restaurant_id, skip=skip, limit=page_size)

        items = list(items_cursor)
        
        # Fetch corresponding restaurant name
        for item in items:
            restaurant = Restaurant.find_by_id(item['restaurantId'])
            item['restaurantName'] = restaurant['name']
        
        current_app.logger.info(
            "getAllItemsInRestaurant | restaurant_id=%s",
            restaurant_id
        )
        # Show it to user
        return jsonify({
            "message": "Fetched menu items successfully",
            "menuItems": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }), 200 
    except Exception as e:
        current_app.logger.error(
            "Error in get all items in restaurant: %s\n%s", 
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Failed to get all items in restaurant", "details": str(e)}), 500      
        