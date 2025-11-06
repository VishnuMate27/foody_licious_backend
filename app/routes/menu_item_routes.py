from flask import Blueprint, json, request, jsonify, session, current_app
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

menu_item_bp = Blueprint('menuItems', __name__)

def get_mongo():
    return current_app.extensions['pymongo'][0]

def get_bcrypt():
    return current_app.extensions['bcrypt']

@menu_item_bp.route('/allMenuItems', methods=['GET'])
def get_all_menu_items():
    """Get all menu items"""
    try:
        # Get restaurant_id from query params
        restaurant_id = request.args.get('restaurant_id')

        if not restaurant_id:
            return jsonify({"error": "restaurant_id is required"}), 400

        restaurant = Restaurant.find_by_id(restaurant_id)
        if not restaurant:
            return jsonify({"error": "Invalid Request! Restaurant does not exist"}), 404

        menuItems = MenuItem.find_items_by_restaurant_id(restaurant_id)
        if not menuItems:
            return jsonify({"error": "MenuItems not found"}), 404

        return jsonify({
            "message": "Fetched all menu items",
            "menuItems": menuItems
        }), 200

    except Exception as e:
        return jsonify({
            "error": "Failed to get all menu items",
            "details": str(e)
        }), 500

@menu_item_bp.route('/addNewItem', methods=['POST'])
def add_new_Item():
    """"Add new item in menu"""
    try:
        data = request.get_json()
        
        required_fields = ['restaurant_id','name', 'description', 'price', 'ingredients']
        for field in required_fields:
            if field not in data or not data[field]:
                print(f"{field}")
                return jsonify({"error": f"{field} is required"}), 400    
            
        restaurantId = data['restaurant_id'].strip()
        name = data['name'].strip()
        description = data['description'].strip()
        price = data['price']
        ingredients = data['ingredients']   
        
        # For checking the restaurant exists
        restaurant = Restaurant.find_by_id(restaurantId)        
        if not restaurant:
            return jsonify({"error": "Invalid Request! Restaurant does not exist"}), 404  
        
        # For checking the item already exist
        success = MenuItem.find_item_by_name(restaurantId, name)
        if success:
            return jsonify({"error": "Invalid Request! Item already exists"}), 409  
        else:    
            menuItem = MenuItem(restaurantId, name, description, price, None, ingredients)
            saved_id = menuItem.save()  
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
        return jsonify({"error": "Failed to add new item", "details": str(e)}), 500                                 

@menu_item_bp.route('/increaseItemQuantity', methods=['PUT'])
def increaseItemQuantity():
    """Increase Quantity of Items in Menu"""
    try:
        data = request.get_json()
        
        required_fields = ['id']
        for field in required_fields:
            if field not in data or not data[field]:
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
            return jsonify({"error": "Failed to increase item quantity"}), 500
        
        # Get updated menuItem data
        updated_item = MenuItem.find_item_by_id(id)
        
        return jsonify({
            "message": "Item quantity increased successfully",
            "menuItem": updated_item
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to increase item quantity", "details": str(e)}), 500        

@menu_item_bp.route('/decreaseItemQuantity', methods=['PUT'])
def decreaseItemQuantity():
    """Decrease Quantity of Items in Menu"""
    try:
        data = request.get_json()
        
        required_fields = ['id']
        for field in required_fields:
            if field not in data or not data[field]:
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
            return jsonify({"error": "Failed to decrease item quantity"}), 500
        
        # Get updated menuItem data
        updated_item = MenuItem.find_item_by_id(id)
        
        return jsonify({
            "message": "Item quantity decreased successfully",
            "menuItem": updated_item
        }), 200 
        
    except Exception as e:
        return jsonify({"error": "Failed to increase item quantity", "details": str(e)}), 500        

@menu_item_bp.route('/deleteItem', methods=['DELETE'])
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
                return jsonify({"error": "Invalid Request! Restaurant does not exist"}), 500  

            # Validate menu item existence
            menu_item = MenuItem.find_item_by_name(restaurant_id, name)
            if not menu_item:
                return jsonify({"error": "Item does not exist!"}), 404

            MenuItem.delete_item(menu_item['_id'])
            return jsonify({
                "message": "Item deleted successfully using restaurant_id and name",
                "menuItemId": str(menu_item['_id'])
            }), 200

        # Case 2: Delete using item id
        elif 'id' in data and data['id']:
            item_id = data['id'].strip()

            menu_item = MenuItem.find_item_by_id(item_id)
            if not menu_item:
                return jsonify({"error": "Item does not exist!"}), 404
            
            try:
                restaurant_id = menu_item['restaurantId']
                folder = S3_FOLDER_RESTAURANTS
                sub_folder = S3_FOLDER_MENU_ITEMS
                item_id = menu_item['id']
                delete_s3_folder(s3_client, S3_BUCKET, f"{folder.rstrip('/')}/{restaurant_id}/{sub_folder.rstrip('/')}/{item_id}/")
            except (NoCredentialsError, ClientError) as e:
                print(f"S3 Deletion Error: {e}")
                return jsonify({"error": "Failed to delete image from S3."}), 500
            
            MenuItem.delete_item(item_id)
            return jsonify({
                "message": "Item deleted successfully using item id",
                "menuItemId": str(item_id)
            }), 200

        # Case 3: Missing required parameters
        else:
            return jsonify({
                "error": "Invalid request. Provide either (restaurant_id and name) or (id)."
            }), 400

    except Exception as e:
        return jsonify({
            "error": "Failed to delete item.",
            "details": str(e)
        }), 500

@menu_item_bp.route("/upload_menu_item_images", methods=["POST"])
def upload_menu_item_images():
    """
    Upload or replace up to 3 images for a menu item in S3.
    Required: item_id, restaurant_id, folder
    Optional: sub_folder
    """
    try:
        # --- Required field checks ---
        if "images" not in request.files:
            return jsonify({"error": "At least one image file is required."}), 400

        images = request.files.getlist("images")
        item_id = request.form.get("item_id")
        restaurant_id = request.form.get("restaurant_id")
        folder = request.form.get("folder")
        sub_folder = request.form.get("sub_folder", "").strip()

        if not item_id:
            return jsonify({"error": "item_id is required."}), 400
        if not restaurant_id:
            return jsonify({"error": "restaurant_id is required."}), 400
        if not folder:
            return jsonify({"error": "folder is required."}), 400
        if not images or len(images) == 0:
            return jsonify({"error": "No images provided."}), 400
        if len(images) > MAX_IMAGES:
            return jsonify({"error": f"Maximum {MAX_IMAGES} images are allowed."}), 400

        # Validate menu item existence
        menu_item = MenuItem.find_item_by_id(item_id)
        if not menu_item:
            return jsonify({"error": "Menu item not found."}), 404
        
        uploaded_urls, error = upload_images_to_s3(
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
            return jsonify({"error": error}), 400
        
        # Fetch updated menu item
        updated_item = MenuItem.find_item_by_id(item_id) # Convert ObjectId to string for JSON

        return jsonify({
            "message": f"Uploaded {len(uploaded_urls)} image(s) successfully.",
            "uploaded_urls": uploaded_urls,
            "menuItem": updated_item
        }), 200

    except (NoCredentialsError, ClientError) as e:
        print(f"S3 Upload Error: {e}")
        return jsonify({"error": "Image upload failed. Please check server logs."}), 500
                       
# @menu_item_bp.route('/updateItem', methods=['PUT'])
# def updateItem():
#     """Update Sepecific Items in Menu"""
#     try:
#         data = request.get_json()
        
#         #image folder and sub_folder name 
#         folder = request.form.get("folder")
#         sub_folder = request.form.get("sub_folder", "").strip()
        
#         required_fields = ['id']
#         for field in required_fields:
#             if field not in data or not data[field]:
#                 return jsonify({"error": f"{field} is required"}), 400
        
#         allowed_fields = ['name', 'description', 'price', 'availableQuantity', 'images', 'ingredients']
#         update_data = {}
        
#         for field in allowed_fields:
#             if field in data and data[field]:
#                 update_data[field] = data[field]
        
#         id = data['id']
                
#         # Get available quantity of items
#         item = MenuItem.find_item_by_id(id)
        
#         existingImagesList = item['images']
        
#         newImagesList = data['images']
        
#         # Find images which exists in newImagesList but not exist in existingImagesList
#         #example
#         # newImagesList = ['remote_img1', 'local_img1','local_img2']
#         # existingImagesList = ['remote_img1', 'remote_img2']
#         # i.e imagesToUpload = newImagesList - existingImagesList = ['local_img1','local_img2']
#         # imagesToDeleteFromMongoDBAndStorage = existingImagesList - newImagesList = ['remote_img2']
        
#         imagesToUpload = [item for item in newImagesList if item not in existingImagesList]
        
#         imagesToDeleteFromMongoDBAndStorage = [item for item in existingImagesList if item not in newImagesList]
        
#         # Add Code For Deleting images from MongoDB and Storage
#         # TODO: Write fuction for above
#         delete_images_from_s3(imagesToDeleteFromMongoDBAndStorage, S3_BUCKET, s3_client)
        
#         # Add Code For Uploading images to Storage and Add it to MongoDB
#         uploaded_urls, error = upload_images_to_s3(
#             s3_client=s3_client,
#             bucket_name=S3_BUCKET,
#             region=S3_REGION,
#             images=imagesToUpload,
#             restaurant_id=item['restaurantId'],
#             folder=folder,
#             item_id=id,
#             sub_folder=sub_folder
#         )

#         if error:
#             return jsonify({"error": error}), 400    
        
#         # Common images in lists newImagesList & existingImagesList
#         common_images_in_list = [element for element in newImagesList if element in existingImagesList]
        
#         # Final image list = uploaded_urls + common_images_in_list = ['remote_img1]
#         finalImageList = uploaded_urls.append(common_images_in_list)   
                
#         update_data['images'] = finalImageList
               
#         # Update restaurant
#         success = MenuItem.update_item(id, update_data)  
#         if not success:
#             return jsonify({"error": "Failed to update item"}), 500
        
#         # Get updated menuItem data
#         updated_item = MenuItem.find_item_by_id(id)
        
#         return jsonify({
#             "message": "Item updated successfully",
#             "menuItem": updated_item
#         }), 200
        
#     except Exception as e:
#         return jsonify({"error": "Failed to update item.", "details": str(e)}), 500     
                            
@menu_item_bp.route('/updateItem', methods=['PUT'])
def update_item():
    """Update specific menu item"""
    try:
        # Since Flutter sends multipart/form-data, use request.form instead of request.get_json()
        form = request.form
        files = request.files

        # Required fields
        item_id = form.get('id')
        if not item_id:
            return jsonify({"error": "id is required"}), 400

        folder = form.get("folder", "").strip()
        sub_folder = form.get("sub_folder", item_id).strip()

        # Collect allowed fields
        allowed_fields = ['name', 'description', 'price', 'availableQuantity', 'ingredients']
        update_data = normalize_menu_item_data(form, allowed_fields)

        # 🔍 Get the existing item from DB
        item = MenuItem.find_item_by_id(item_id)
        if not item:
            return jsonify({"error": "Item not found"}), 404

        # Step 1
        fetched_list_from_mongodb = item.get('images', [])

        # 🖼️ Handle image uploads
        uploaded_urls = []
        error = None

        # Get existing images from frontend
        existing_remote_images_from_client = []
        if 'images' in form:
            try:
                existing_remote_images_from_client = json.loads(form['images'])
            except Exception as e:
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
            return jsonify({"error": "Failed to update item"}), 500
        
        # Step 4
        updated_item = MenuItem.find_item_by_id(item_id)
        
        current_images = updated_item.get('images', [])
        
        # Identify files to upload (those sent in `request.files`)
        new_images_to_upload = files.getlist("images")

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
                return jsonify({"error": error}), 400 

        # Step 5
        final_image_list = current_images + uploaded_urls
        update_data['images'] = final_image_list

        # Step 6
        success = MenuItem.update_item(item_id, update_data)
        if not success:
            return jsonify({"error": "Failed to update item"}), 500

        # ✅ Fetch updated item to return
        updated_item = MenuItem.find_item_by_id(item_id)

        return jsonify({
            "message": "Item updated successfully",
            "menuItem": updated_item
        }), 200

    except Exception as e:
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
                            