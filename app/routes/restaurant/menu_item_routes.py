import traceback
from venv import logger
from flask import Blueprint, app, json, request, jsonify, session, current_app
from app.core.constansts import ALLOWED_IMAGE_EXTENSIONS, S3_FOLDER_MENU_ITEMS, S3_FOLDER_RESTAURANTS
from app.models.menu_item import MenuItem
from app.models.restaurant import Restaurant
from app.utils.aws_utils import MAX_IMAGES, delete_images_from_s3, delete_s3_folder, upload_images_to_s3
from app.utils.decorators import login_required, admin_required
from firebase_admin import auth as firebase_auth
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
from app.extensions import s3_client, S3_BUCKET, S3_REGION
from botocore.exceptions import NoCredentialsError, ClientError
import logging
from logging.handlers import RotatingFileHandler

restaurant_menu_item_bp = Blueprint('menuItems', __name__)

def get_mongo():
    return current_app.extensions['pymongo'][0]

def get_bcrypt():
    return current_app.extensions['bcrypt']

@restaurant_menu_item_bp.route('/allMenuItems', methods=['GET'])
def get_all_menu_items():
    """Get all menu items with pagination support"""
    try:
        # Get restaurant_id from query params
        restaurant_id = request.args.get('restaurant_id')
        # Get pagination parameters with defaults
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))

        # Validate pagination parameters
        if page < 1:
            app.logger.warning(f"Failed to fetch menu items | restaurantId={restaurant_id} | Page number must be greater than 0")
            return jsonify({"error": "Page number must be greater than 0"}), 400
        if page_size < 1:
            app.logger.warning(f"Failed to fetch menu items | restaurantId={restaurant_id} | Page size must be greater than 0")
            return jsonify({"error": "Page size must be greater than 0"}), 400
        if page_size > 100:  # Limit maximum page size
            app.logger.warning(f"Failed to fetch menu items | restaurantId={restaurant_id} | Page size cannot exceed 100")
            return jsonify({"error": "Page size cannot exceed 100"}), 400

        if not restaurant_id:
            app.logger.warning(f"Failed to fetch menu items | restaurantId={restaurant_id} | restaurant_id is required")
            return jsonify({"error": "restaurant_id is required"}), 400

        restaurant = Restaurant.find_by_id(restaurant_id)
        if not restaurant:
            app.logger.warning(f"Failed to fetch menu items | restaurantId={restaurant_id} | Invalid Request! Restaurant does not exist")
            return jsonify({"error": "Invalid Request! Restaurant does not exist"}), 404

        # Get total count of menu items
        total_count = MenuItem.find_items_by_restaurant_id(restaurant_id, count_only=True)
        # if total_count == 0:
        #     return jsonify({"error": "MenuItems not found"}), 404
            
        total_pages = (total_count + page_size - 1) // page_size

        # Calculate skip and limit for pagination
        skip = (page - 1) * page_size
        menuItems = MenuItem.find_items_by_restaurant_id(restaurant_id, skip=skip, limit=page_size)
        app.logger.info("Fetched menu items successfully | restaurantId={restaurantId}")
        return jsonify({
            "message": "Fetched menu items successfully",
            "menuItems": menuItems,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }), 200

    except Exception as e:
        app.logger.error(
            "Error in get_all_menu_items: %s\n%s", 
            str(e),
            traceback.format_exc()
        )
        return jsonify({
            "error": "Failed to get all menu items",
            "details": str(e)
        }), 500

@restaurant_menu_item_bp.route('/addNewItem', methods=['POST'])
def add_new_Item():
    """"Add new item in menu"""
    try:
        data = request.get_json()
        
        required_fields = ['restaurant_id','name', 'description', 'price', 'ingredients']
        for field in required_fields:
            if field not in data or not data[field]:
                app.logger.warning(
                    "AddMenuItemValidationFailed | field=%s | payload=%s",
                    field, data
                )
                return jsonify({"error": f"{field} is required"}), 400    
            
        restaurantId = data['restaurant_id'].strip()
        name = data['name'].strip()
        description = data['description'].strip()
        price = data['price']
        ingredients = data['ingredients']   
        
        # For checking the restaurant exists
        restaurant = Restaurant.find_by_id(restaurantId)        
        if not restaurant:
            app.logger.warning(
                "AddMenuItemFailed | restaurantId=%s | reason=RestaurantNotFound",
                restaurantId
            )
            return jsonify({"error": "Invalid Request! Restaurant does not exist"}), 404  
        
        # For checking the item already exist
        success = MenuItem.find_item_by_name(restaurantId, name)
        if success:
            app.logger.warning(
                "AddMenuItemFailed | restaurantId=%s | name=%s | reason=ItemAlreadyExists",
                restaurantId, name
            )
            return jsonify({"error": "Invalid Request! Item already exists"}), 409  
        else:    
            menuItem = MenuItem(restaurantId, name, description, price, None, ingredients)
            saved_id = menuItem.save()  
            app.logger.info(
                "MenuItemAdded | id=%s | restaurantId=%s | name=%s",
                saved_id, restaurantId, name
            )
            return jsonify({
                "message": "Menu Item added successfully",
                "menuItem": {
                    "id": saved_id,
                    "restaurantId": restaurantId,
                    "name": name,
                    "description": description,
                    "price": price,
                    "ingredients":ingredients
                }
            }), 201
    except Exception as e:
        app.logger.error(
            "AddMenuItemException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Failed to add new item", "details": str(e)}), 500                                 

@restaurant_menu_item_bp.route('/increaseItemQuantity', methods=['PUT'])
def increaseItemQuantity():
    """Increase Quantity of Items in Menu"""
    try:
        data = request.get_json()
        
        required_fields = ['id']
        for field in required_fields:
            if field not in data or not data[field]:
                app.logger.warning(
                    "IncreaseItemQuantityFailed | reason=ItemIdRequired",
                )
                return jsonify({"error": f"{field} is required"}), 400
            
        id = data['id']    
        
        # Get available quantity of items
        item = MenuItem.find_item_by_id(id)  
        
        # Increase item quantity by 1
        newAvailableQuantity = item['availableQuantity'] + 1
        
        item_data = {
            "id": item['id'],
            "availableQuantity": newAvailableQuantity
        }
        
        success = MenuItem.update_item(id, item_data)
        if not success:
            app.logger.warning(
                "IncreaseItemQuantityFailed | reason=ItemIdRequired",
            )
            return jsonify({"error": "Failed to increase item quantity"}), 500
        
        # Get updated menuItem data
        updated_item = MenuItem.find_item_by_id(id)
        
        app.logger.info(
            "IncreaseItemQuantitySuccess | id=%s",
            id
        )        
        return jsonify({
            "message": "Item quantity increased successfully",
            "menuItem": updated_item
        }), 200
        
    except Exception as e:
        app.logger.error(
            "IncreaseItemQuantityException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Failed to increase item quantity", "details": str(e)}), 500        

@restaurant_menu_item_bp.route('/decreaseItemQuantity', methods=['PUT'])
def decreaseItemQuantity():
    """Decrease Quantity of Items in Menu"""
    try:
        data = request.get_json()
        
        required_fields = ['id']
        for field in required_fields:
            if field not in data or not data[field]:
                app.logger.warning(
                    f"DecreaseItemQuantityFailed | reason={field}Required",
                )
                return jsonify({"error": f"{field} is required"}), 400
            
        id = data['id']    
        
        # Get available quantity of items
        item = MenuItem.find_item_by_id(id)  
        
        # Decrease item quantity by 1
        if(item['availableQuantity'] != 0):
            newAvailableQuantity = item['availableQuantity'] - 1
        else:
            return jsonify({"error": "Failed to decrease item quantity, Item quantity is already zero."}), 500
        
        item_data = {
            "id": item['id'],
            "availableQuantity": newAvailableQuantity
        }
        
        success = MenuItem.update_item(id, item_data)
        if not success:
            app.logger.warning(
                "DecreaseItemQuantityFailed | reason=ItemIdRequired",
            )
            return jsonify({"error": "Failed to decrease item quantity"}), 500
        
        # Get updated menuItem data
        updated_item = MenuItem.find_item_by_id(id)
        
        app.logger.info(
            "DecreaseItemQuantitySuccess | id=%s",
            id
        )
        return jsonify({
            "message": "Item quantity decreased successfully",
            "menuItem": updated_item
        }), 200 
        
    except Exception as e:
        app.logger.error(
            "DecreaseItemQuantityException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Failed to increase item quantity", "details": str(e)}), 500        

@restaurant_menu_item_bp.route('/deleteItem', methods=['DELETE'])
def delete_item():
    """Delete menu item either by (restaurant_id + name) or by item id."""
    try:
        data = request.get_json()
        restaurant_id = request.args.get('restaurant_id')
        # Case 1: Delete using restaurant_id + name
        if 'restaurant_id' in data and 'name' in data and data['restaurant_id'] and data['name']:
            restaurant_id = data['restaurant_id'].strip()
            name = data['name'].strip()

            # Validate restaurant existence
            restaurant = Restaurant.find_by_id(restaurant_id)
            if not restaurant:
                app.logger.warning(
                    "DeleteItemFailed | reason=RestaurantNotExist",
                )
                return jsonify({"error": "Invalid Request! Restaurant does not exist"}), 500  

            # Validate menu item existence
            menu_item = MenuItem.find_item_by_name(restaurant_id, name)
            if not menu_item:
                app.logger.warning(
                    "DeleteItemFailed | reason=ItemNotExist",
                )
                return jsonify({"error": "Item does not exist!"}), 404

            MenuItem.delete_item(menu_item['_id'])
            app.logger.info(
                "DeleteItemQuantitySuccess | id=%s",
                id
            )            
            return jsonify({
                "message": "Item deleted successfully using restaurant_id and name",
                "menuItemId": str(menu_item['_id'])
            }), 200

        # Case 2: Delete using item id
        elif 'id' in data and data['id']:
            item_id = data['id'].strip()

            menu_item = MenuItem.find_item_by_id(item_id)
            if not menu_item:
                app.logger.warning(
                    "DeleteItemFailed | reason=ItemNotExist",
                )
                return jsonify({"error": "Item does not exist!"}), 404
            
            try:
                restaurant_id = menu_item['restaurantId']
                folder = S3_FOLDER_RESTAURANTS
                sub_folder = S3_FOLDER_MENU_ITEMS
                item_id = menu_item['id']
                delete_s3_folder(s3_client, S3_BUCKET, f"{folder.rstrip('/')}/{restaurant_id}/{sub_folder.rstrip('/')}/{item_id}/")
            except (NoCredentialsError, ClientError) as e:
                print(f"S3 Deletion Error: {e}")
                app.logger.error(
                    "DeleteItemException | reason=FailedToDeleteImgFromS3 | error=%s\n%s",
                    str(e),
                    traceback.format_exc()
                )
                return jsonify({"error": "Failed to delete image from S3."}), 500
            
            MenuItem.delete_item(item_id)
            app.logger.info(
                "DeleteItemSuccess | id=%s",
                id
            )
            return jsonify({
                "message": "Item deleted successfully using item id",
                "menuItemId": str(item_id)
            }), 200

        # Case 3: Missing required parameters
        else:
            app.logger.warning(
                "DeleteItemFailed | reason=InvalidRequest",
            )            
            return jsonify({
                "error": "Invalid request. Provide either (restaurant_id and name) or (id)."
            }), 400

    except Exception as e:
        app.logger.error(
            "DeleteItemException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({
            "error": "Failed to delete item.",
            "details": str(e)
        }), 500

@restaurant_menu_item_bp.route("/upload_menu_item_images", methods=["POST"])
def upload_menu_item_images():
    """
    Upload or replace up to 3 images for a menu item in S3.
    Required: item_id, restaurant_id, folder
    Optional: sub_folder
    """
    try:
        # --- Required field checks ---
        if "images" not in request.files:
            app.logger.warning(
                "UploadItemImageFailed | reason=AtLeastOneImageRequired",
            )
            return jsonify({"error": "At least one image file is required."}), 400

        images = request.files.getlist("images")
        item_id = request.form.get("item_id")
        restaurant_id = request.form.get("restaurant_id")
        folder = request.form.get("folder")
        sub_folder = request.form.get("sub_folder", "").strip()

        if not item_id:
            app.logger.warning(
                "UploadItemImageFailed | reason=ItemIdRequired",
            )
            return jsonify({"error": "item_id is required."}), 400
        if not restaurant_id:
            app.logger.warning(
                "UploadItemImageFailed | reason=RestaurantIdRequired",
            )            
            return jsonify({"error": "restaurant_id is required."}), 400
        if not folder:
            app.logger.warning(
                "UploadItemImageFailed | reason=FolderRequired",
            )            
            return jsonify({"error": "folder is required."}), 400
        if not images or len(images) == 0:
            app.logger.warning(
                "UploadItemImageFailed | reason=NoImageProvided",
            )            
            return jsonify({"error": "No images provided."}), 400
        if len(images) > MAX_IMAGES:
            app.logger.warning(
                "UploadItemImageFailed | reason=Max{MAX_IMAGES}AreAllowed",
            )            
            return jsonify({"error": f"Maximum {MAX_IMAGES} images are allowed."}), 400

        # Validate menu item existence
        menu_item = MenuItem.find_item_by_id(item_id)
        if not menu_item:
            app.logger.warning(
                "UploadItemImageFailed | reason=MenuItemNotFound",
            )            
            return jsonify({"error": "Menu item not found."}), 404
        
        update_data = {}
        
        uploaded_urls, existing_urls, error = upload_images_to_s3(
            s3_client=s3_client,
            bucket_name=S3_BUCKET,
            region=S3_REGION,
            images=images,
            restaurant_id=restaurant_id,
            folder=folder,
            item_id=item_id,
            sub_folder=sub_folder
        )        

        if error:
            app.logger.error(
                "UploadItemImageException | error=%s\n%s",
                str(e),
                traceback.format_exc()
            )    
            return jsonify({"error": error}), 400
        
        update_data['images'] = uploaded_urls
        
        success = MenuItem.update_item(item_id, update_data)
        
        if not success:
            app.logger.warning(
                "UploadItemImageFailed | reason=FailedToUpdateItem",
            )    
            return jsonify({"error": "Failed to update item"}), 500
        
        # Fetch updated menu item
        updated_item = MenuItem.find_item_by_id(item_id) # Convert ObjectId to string for JSON

        app.logger.info(
            "UploadItemImage | itemId=%s",
            item_id
        )        
        return jsonify({
            "message": f"Uploaded {len(uploaded_urls)} image(s) successfully.",
            "uploaded_urls": uploaded_urls,
            "menuItem": updated_item
        }), 200

    except (NoCredentialsError, ClientError) as e:
        app.logger.error(
            "UploadItemImageException | error=%s\n%s | S3 image upload error",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Image upload failed. Please check server logs."}), 500
                                                  
@restaurant_menu_item_bp.route('/updateItem', methods=['PUT'])
def update_item():
    """Update specific menu item"""
    try:
        # Since Flutter sends multipart/form-data, use request.form instead of request.get_json()
        form = request.form
        files = request.files

        # Required fields
        item_id = form.get('id')
        if not item_id:
            app.logger.warning(
                "UpdateItemFailed | reason=ItemIdRequired",
            )            
            return jsonify({"error": "id is required"}), 400

        folder = form.get("folder", "").strip()
        sub_folder = form.get("sub_folder", item_id).strip()

        # Collect allowed fields
        allowed_fields = ['name', 'description', 'price', 'availableQuantity', 'ingredients']
        update_data = normalize_menu_item_data(form, allowed_fields)

        # 🔍 Get the existing item from DB
        item = MenuItem.find_item_by_id(item_id)
        if not item:
            app.logger.warning(
               "UpdateItemFailed | reason=ItemNotFound",
            )    
            return jsonify({"error": "Item not found"}), 404

        # Step 1
        fetched_list_from_mongodb = item.get('images') or []

        # 🖼️ Handle image uploads
        uploaded_urls = []
        error = None

        # Get existing images from frontend
        existing_remote_images_from_client = []
        if 'images' in form:
            try:
                existing_remote_images_from_client = json.loads(form['images'])
            except Exception as e:
                app.logger.warning(
                    "UpdateItemFailed | reason=InvalidImageFormat",
                )   
                return jsonify({"error": "Invalid format for images", "details": str(e)}), 400

        # Step 2
        # images_to_delete = fetched_list_from_mongodb - existing_remote_images_from_client
        images_to_delete = [img for img in fetched_list_from_mongodb if img not in existing_remote_images_from_client]

        # Step 3
        if images_to_delete:
            delete_images_from_s3(images_to_delete, s3_client)
        
        # update_data['images'] = fetched_list_from_mongodb - images_to_delete
        update_data['images'] = [img for img in fetched_list_from_mongodb if img not in images_to_delete]
            
        success = MenuItem.update_item(item_id, update_data)
        if not success:
            app.logger.warning(
                "UpdateItemFailed | reason=FailedToUpdateItems",
            )   
            return jsonify({"error": "Failed to update item"}), 500
        
        # Step 4
        updated_item = MenuItem.find_item_by_id(item_id)
        
        current_images = updated_item.get('images') or []
        
        # Identify files to upload (those sent in `request.files`)
        new_images_to_upload = files.getlist("images") or []

        # Upload new images to S3
        if new_images_to_upload:
            uploaded_urls, existing_urls, error = upload_images_to_s3(
                s3_client=s3_client,
                bucket_name=S3_BUCKET,
                region=S3_REGION,
                images=new_images_to_upload,
                restaurant_id=item['restaurantId'],
                folder=folder,
                item_id=item_id,
                sub_folder=sub_folder
            )

            if error:
                app.logger.warning(
                    "UpdateItemFailed | reason={error}",
                )
                return jsonify({"error": error}), 400 

        # Step 5
        final_image_list = current_images + uploaded_urls
        update_data['images'] = final_image_list

        # Step 6
        success = MenuItem.update_item(item_id, update_data)
        if not success:
            app.logger.warning(
                "UpdateItemFailed | reason={error}",
            )
            return jsonify({"error": "Failed to update item"}), 500

        # ✅ Fetch updated item to return
        updated_item = MenuItem.find_item_by_id(item_id)
        app.logger.info(
            "UpdateItemSuccess | id=%s",
            item_id
        )
        return jsonify({
            "message": "Item updated successfully",
            "menuItem": updated_item
        }), 200

    except Exception as e:
        app.logger.error(
            "UpdateItemException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({
            "error": "Failed to update item.",
            "details": str(e)
        }), 500
                                                       
def normalize_menu_item_data(form, allowed_fields):
    import json
    data = {k: form.get(k) for k in allowed_fields if form.get(k) is not None}

    def safe_int(key):
        try:
            data[key] = int(data[key])
        except (ValueError, TypeError):
            data.pop(key, None)

    if 'price' in data: safe_int('price')
    if 'availableQuantity' in data: safe_int('availableQuantity')

    if 'ingredients' in data:
        try:
            ingredients = json.loads(data['ingredients'])
            data['ingredients'] = [str(i) for i in ingredients] if isinstance(ingredients, list) else [str(ingredients)]
        except (json.JSONDecodeError, TypeError):
            data.pop('ingredients', None)

    return data
                            