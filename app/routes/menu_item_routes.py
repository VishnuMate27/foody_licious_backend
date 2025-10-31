from flask import Blueprint, request, jsonify, session, current_app
from app.models.menu_item import MenuItem
from app.models.restaurant import Restaurant
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
        return jsonify({"error": "Failed to increase item quantity", "details": str(e)}), 500                                 

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

            menu_item = MenuItem.find_by_id(item_id)
            if not menu_item:
                return jsonify({"error": "Item does not exist!"}), 404

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
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    MAX_IMAGES = 3

    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

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

    uploaded_urls = []

    try:
        for index, image in enumerate(images):
            if image.filename == "":
                return jsonify({"error": "One of the image files has no filename."}), 400
            if not allowed_file(image.filename):
                return jsonify({"error": f"Unsupported file type: {image.filename}"}), 400

            # Secure and deterministic filename
            filename = secure_filename(image.filename)
            file_ext = filename.rsplit('.', 1)[1].lower()
            filename = f"image_{index + 1}.{file_ext}"

            # Build S3 key
            if sub_folder:
                s3_key = f"{folder.rstrip('/')}/{restaurant_id}/{sub_folder.rstrip('/')}/{item_id}/{filename}"
            else:
                s3_key = f"{folder.rstrip('/')}/{restaurant_id}/{item_id}/{filename}"

            # Delete existing image if present (overwrite)
            try:
                s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
                s3_client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
                print(f"Deleted old image: {s3_key}")
            except ClientError as e:
                if e.response["Error"]["Code"] != "404":
                    raise e

            # Upload new file
            s3_client.upload_fileobj(
                image,
                S3_BUCKET,
                s3_key,
                ExtraArgs={"ContentType": image.content_type}
            )

            # Build public URL
            file_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
            uploaded_urls.append(file_url)

        # Update the menu item in MongoDB
        update_data = {"images": uploaded_urls}
        success = MenuItem.update_item(item_id, update_data)
        if not success:
            return jsonify({"error": "Failed to update menu item images."}), 501

        # Fetch updated menu item
        updated_item = MenuItem.find_item_by_id(item_id)
        updated_item["_id"] = str(updated_item["_id"])  # Convert ObjectId to string for JSON

        return jsonify({
            "message": f"Uploaded {len(uploaded_urls)} image(s) successfully.",
            "uploaded_urls": uploaded_urls,
            "menuItem": updated_item
        }), 200

    except (NoCredentialsError, ClientError) as e:
        print(f"S3 Upload Error: {e}")
        return jsonify({"error": "Image upload failed. Please check server logs."}), 500
                       