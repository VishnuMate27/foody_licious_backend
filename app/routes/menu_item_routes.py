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
        data = request.get_json()
        
        required_fields = ['restaurant_id']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"{field} is required"}), 400
            
        restaurant_id = data['restaurant_id']
        restaurant = Restaurant.find_by_id(restaurant_id)
        if not restaurant:
            return jsonify({"error": "Invalid Request! Restaurant does not exist"}), 404
        
        menuItems = MenuItem.find_items_by_restaurant_id(restaurant_id)
        
        if not menuItems:
            return jsonify({"error": "MenuItems not found"}), 404
        
        return jsonify({"message": "Fetched all menu items","menuItems": menuItems}), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to get all menu items", "details": str(e)}), 500

@menu_item_bp.route('/addNewItem', methods=['POST'])
def add_new_Item():
    """"Add new item in menu"""
    try:
        data = request.get_json()
        
        required_fields = ['restaurant_id','name', 'description', 'price', 'image', 'ingredients']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"{field} is required"}), 400    
            
        restaurantId = data['restaurant_id'].strip()
        name = data['name'].strip()
        description = data['description'].strip()
        price = data['price']
        image = data['image'].strip()
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
            menuItem = MenuItem(restaurantId, name, description, price, image, ingredients)
            saved_id = menuItem.save()  
            return jsonify({
                "message": "Menu Item added successfully",
                "menuItem": {
                    "id": saved_id,
                    "name": name,
                    "description": description,
                    "price": price,
                    "image":image,
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
            "_id": item['_id'],
            "availableQuantity": newAvailableQuantity
        }
        
        success = MenuItem.update_item(id, item_data)
        if not success:
            return jsonify({"error": "Failed to increase item quantity"}), 500
        
        # Get updated menuItem data
        updated_item = MenuItem.find_item_by_id(id)
        upadted_item_data = {
            "id": updated_item['_id'],
            "restaurant_id": updated_item['restaurantId'],
            "availableQuantity": updated_item['availableQuantity']
        }
        
        return jsonify({
            "message": "Item quantity increased successfully",
            "menuItems": upadted_item_data
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
            "_id": item['_id'],
            "availableQuantity": newAvailableQuantity
        }
        
        success = MenuItem.update_item(id, item_data)
        if not success:
            return jsonify({"error": "Failed to decrease item quantity"}), 500
        
        # Get updated menuItem data
        updated_item = MenuItem.find_item_by_id(id)
        upadted_item_data = {
            "id": updated_item['_id'],
            "restaurant_id": updated_item['restaurantId'],
            "availableQuantity": updated_item['availableQuantity']
        }
        
        return jsonify({
            "message": "Item quantity decreased successfully",
            "restaurant": upadted_item_data
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to increase item quantity", "details": str(e)}), 500        

@menu_item_bp.route('/deleteItem', methods=['DELETE'])
def delete_Item():
    """"Delete item in menu"""
    try:
        data = request.get_json()
        
        required_fields = ['restaurant_id','name']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"{field} is required"}), 400    
            
        restaurantId = data['restaurant_id'].strip()
        name = data['name'].strip()
        
        # For checking the restaurant exists
        restaurant = Restaurant.find_by_id(restaurantId)        
        if not restaurant:
            return jsonify({"error": "Invalid Request! Restaurant does not exist"}), 404  
        
        # For checking the item already exist
        menuItem = MenuItem.find_item_by_name(restaurantId, name)
        if not menuItem:
            return jsonify({"error": "Invalid Request! Item does not exists!"}), 409         
        else:
            MenuItem.delete_item(menuItem['_id'])
            return jsonify({"message": "Item Deleted Successfully!", "menuItem": menuItem['_id']}), 200
    except Exception as e:
        return jsonify({"error": "Failed to delete item.", "details": str(e)}), 500                       