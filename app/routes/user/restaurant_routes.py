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

user_restaurant_bp = Blueprint('userRestaurant', __name__)

@user_restaurant_bp.route('/restaurantDetails', methods=['GET'])
def get_restaurant_details():
    """Get all items in restaurants of users city"""
    try:
        # Get restaurant_id from query params 
        restaurant_id = request.args.get('restaurant_id')
        
        if not restaurant_id:
            current_app.logger.warning(f"Failed to Get restaurant details | restaurant_id={restaurant_id} | restaurant_id is required")
            return jsonify({"error": "restaurant_id is required"}), 400

        # Get the restaurant's details   
        restaurant = Restaurant.find_by_id(restaurant_id)
        
        current_app.logger.info(
            "getRestaurantDetailsSuccess | restaurantId=%s",
            restaurant_id
        )
        
        # Show it to user
        return jsonify({
            "message": "Fetched restaurant details successfully",
            "restaurant": restaurant,
        }), 200 
    except Exception as e:
        current_app.logger.error(
            "Error in get all items in restaurants of users city: %s\n%s", 
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Failed to get all items in restaurants of users city", "details": str(e)}), 500      
 