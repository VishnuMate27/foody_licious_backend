import traceback
from bson import ObjectId
from flask import Blueprint, current_app, jsonify, request
from app.models.cart import Cart
from app.models.menu_item import MenuItem
from app.models.restaurant import Restaurant

user_cart_bp = Blueprint('cart', __name__)

@user_cart_bp.route('/allMenuItems', methods = ['GET'])
def get_all_cart_items():
    """Get all cart items with pagination support"""
    try:
        # Get userId from query params
        userId = request.args.get('userId')
        # Get pagination parameters with defaults
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))

        # Validate pagination parameters
        if page < 1:
            current_app.logger.warning(f"Failed to fetch cart items | userId={userId} | Page number must be greater than 0")
            return jsonify({"error": "Page number must be greater than 0"}), 400
        if page_size < 1:
            current_app.logger.warning(f"Failed to fetch cart items | userId={userId} | Page size must be greater than 0")
            return jsonify({"error": "Page size must be greater than 0"}), 400
        if page_size > 100:  # Limit maximum page size
            current_app.logger.warning(f"Failed to fetch cart items | userId={userId} | Page size cannot exceed 100")
            return jsonify({"error": "Page size cannot exceed 100"}), 400

        if not userId:
            current_app.logger.warning(f"Failed to fetch cart items | userId={userId} | userId is required")
            return jsonify({"error": "userId is required"}), 400
                
        cart = Cart.find_cart_by_userId(userId)
        if not cart:
            current_app.logger.warning(f"Failed to fetch cart items | userId={userId} | Invalid Request! Cart does not exist (because no item is added).")
            return jsonify({"error": "Cart does not exist (because no item is added)."}), 404
        
        # Get total count of cart items
        total_count = len(cart['items'])
        # if total_count == 0:
        #     return jsonify({"error": "CartItems not found"}), 404
        
        total_pages = (total_count + page_size - 1) // page_size
        
        # Calculate skip and limit for pagination
        skip = (page - 1) * page_size 
        limit = page_size
        cartItems = cart['items'][skip : skip + limit]
        
        for cartItem in cartItems:
            # Get menu item details and restaurant name details
            menuItem = MenuItem.find_item_by_id(cartItem["menuItemId"])
            restaurant = Restaurant.find_by_id(menuItem["restaurantId"])
            menuItem['restaurantName'] = restaurant['name']
            cartItem['menuItem'] = menuItem
        current_app.logger.info("Fetched cart items successfully | userId={userId}")
        return jsonify({
            "message": "Fetched cart items successfully",
            "cartItems": cartItems,
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
        current_app.logger.error(
            "Error in get_all_cart_items: %s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Failed to get all cart items", "details": str(e)}), 500

@user_cart_bp.route('/addNewItem', methods=['POST'])
def add_new_Item():
    """Add new item to cart""" 
    try:
        data = request.get_json()
        required_fields = ['menuItemId','restaurantId','userId']  
        for field in required_fields:
            if field not in data or not data[field]:
                current_app.logger.warning(
                    "AddCartItemValidationFailed | field=%s | payload=%s",
                    field, data
                )
                return jsonify({"error": f"{field} is required"}), 400 
        
        menuItemId = data['menuItemId'].strip()
        restaurantId = data['restaurantId'].strip()
        userId = data['userId'].strip()
        
        menuItem = MenuItem.find_item_by_id(menuItemId)
        if not menuItem:
            current_app.logger.warning(
                    "AddCartItemFailed | restaurantId=%s | userId=%s | reason=MenuItemNotFound",
                    restaurantId, userId
                )
            return jsonify({"error": "Menu item not found"}), 404
        
        if menuItem['availableQuantity'] < 1:
            current_app.logger.warning("IncreaseCartItemQuantityFailed | id=%s | userId=%s | reason=MenuItemIsOutOfStock")
            return jsonify({"error": "Menu Item is Out of Stock!"}), 500 
        
        defaultItemQuantity = 1
        item = {
            "menuItemId": menuItemId,
            "quantity": defaultItemQuantity,
            "price": menuItem['price'],
            "totalPrice": menuItem['price'] * defaultItemQuantity
        }
        
        # Check if cart exist for this user
        cart = Cart.find_cart_by_userId(userId)
        # If cart exist
        if cart:
            # then check if the item adding to cart is from same restaurant (have same restaurantId)
            if cart['restaurantId'] != restaurantId:
                current_app.logger.warning(
                    "AddCartItemFailed | restaurantId=%s | userId=%s | reason=DifferentRestaurantId",
                    restaurantId, userId
                )
                return jsonify({
                    "error": "You can add items from only one restaurant at a time"
                }), 400
            
            # Check the item exist in the list
            # if item exist in cart increase its quantity and total price
            itemExists = False
            for existing_item in cart['items']:
                if existing_item['menuItemId'] == item['menuItemId']:
                    itemExists = True
                    existing_item['quantity'] += item['quantity']
                    existing_item['totalPrice'] += item['totalPrice']
                    break
                
            if not itemExists:               
                # Append item
                cart['items'].append(item)
                
            # Calculate total amount
            totalAmount = 0
            for item in cart['items']:
                totalAmount += item['totalPrice']
            
            # Save updated cart
            success = Cart.update_cart(cart['id'], {"items": cart['items'], "totalAmount": totalAmount})
            
            if success:
                updated_cart = Cart.find_cart_by_id(cart['id'])
                current_app.logger.info(
                    "CartItemAdded | id=%s | restaurantId=%s | userId=%s",
                    cart["id"], restaurantId, userId
                )
                return jsonify({"message": "Item added to cart successfully", "cart": updated_cart}), 200  
            
        else:
            # If Cart not exist create new cart and add item in it.
            new_cart = Cart(restaurantId, userId, [item])
            
            # Create cart
            saved_id = new_cart.save()
            
            updated_cart = Cart.find_cart_by_id(saved_id)
            current_app.logger.info(
                "CartItemAdded | id=%s | restaurantId=%s | userId=%s",
                saved_id, restaurantId, userId
            )
            
            return jsonify({"message": "Item added to cart successfully", "cart": updated_cart}), 200    
          
    except Exception as e:
        current_app.logger.error(
            "AddCartItemException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Failed to add new item to cart", "details": str(e)}), 500
    # Remaining/Still not required: Do not take restaurantId of item internally check belongs to same restaurant of cart

@user_cart_bp.route('/increaseItemQuantity', methods = ['PUT'])    
def increaseItemQuantity():
    """Increase Quantity of Items in Cart"""
    try:
        data = request.get_json()
        
        required_fields = ['cartId','menuItemId','userId']
        for field in required_fields:
            if field not in data or not data[field]:
                current_app.logger.warning(
                    "IncreaseCartItemQuantityValidationFailed | field=%s | payload=%s",
                    field, data
                )
                return jsonify({"error": f"{field} is required"}), 400
            
        cartId = data['cartId'].strip()
        menuItemId = data['menuItemId'].strip()
        userId = data['userId'].strip()
        
        # Check if menuItem available in stock
        menuItem = MenuItem.find_item_by_id(menuItemId)  
        if not menuItem:
            current_app.logger.warning("IncreaseCartItemQuantityFailed | id=%s | userId=%s | reason=MenuItemNotExist")
            return jsonify({"error": "Invalid Request! Menu Item does not exist"}), 404 
        
        if menuItem['availableQuantity'] < 1:
            current_app.logger.warning("IncreaseCartItemQuantityFailed | id=%s | userId=%s | reason=MenuItemIsOutOfStock")
            return jsonify({"error": "Menu Item is currently Out of Stock!", "cartId": cartId}), 500      
        
        # Check if cart exist for this user  
        cart = Cart.find_cart_by_id(cartId)
        if not cart:
            # If Cart not exist
            current_app.logger.warning(
                "IncreaseCartItemQuantityFailed | id=%s | userId=%s | reason=CartNotExists",
                cartId, userId
            )
            return jsonify({"error": "Invalid Request! Cart not exist.", "cartId": cartId}), 404       
        else:
            # Check menuItem exist in this cart  
            itemExists = False
            for existing_item in cart['items']:
                if existing_item['menuItemId'] == menuItemId:
                    itemExists = True
                    existing_item['quantity'] += 1
                    existing_item['totalPrice'] += existing_item['price']
                    break
            if not itemExists:
                # If item not exist
                current_app.logger.warning(
                    "IncreaseCartItemQuantityFailed | id=%s | menuItemId=%s | userId=%s | reason=ItemNotExistsInCart",
                    cartId, menuItemId, userId
                )
                return jsonify({"error": "Invalid Request! Item not exist in Cart.", "cartId": cartId}), 404
            
            # Calculate total amount
            totalAmount = 0                                                                                                                                             
            for item in cart['items']:
                totalAmount += item['totalPrice']
                
            # Save updated cart
            success = Cart.update_cart(cart['id'], {"items": cart['items'], "totalAmount": totalAmount})
            
            if success:
                # Get updated menuItem data
                updated_cart = Cart.find_cart_by_id(cart['id'])
                current_app.logger.info(
                    "IncreaseCartItemQuantitySuccess | id=%s | userId=%s",
                    cart["id"], userId
                )
                return jsonify({"message": "Item quantity increased successfully!", "cart": updated_cart}), 200    
    except Exception as e:
        current_app.logger.error(
            "IncreaseCartItemQuantityException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Failed to increase cart item quantity", "details": str(e)}), 500  
            
@user_cart_bp.route('/decreaseItemQuantity', methods = ['PUT'])    
def decreaseItemQuantity():
    """Decrease Quantity of Items in Cart"""
    try:
        data = request.get_json()
        
        required_fields = ['cartId','menuItemId','userId']
        for field in required_fields:
            if field not in data or not data[field]:
                current_app.logger.warning(
                    "DecreaseCartItemQuantityValidationFailed | field=%s | payload=%s",
                    field, data
                )
                return jsonify({"error": f"{field} is required"}), 400
            
        cartId = data['cartId'].strip()
        menuItemId = data['menuItemId'].strip()
        userId = data['userId'].strip()
        
        # Check if menuItem available in stock
        menuItem = MenuItem.find_item_by_id(menuItemId)  
        if not menuItem:
            current_app.logger.warning("DecreaseCartItemQuantityFailed | id=%s | userId=%s | reason=MenuItemNotExist")
            return jsonify({"error": "Invalid Request! Menu Item does not exist"}), 404 
        
        ### I think this checker is not necessary for this api. Ask chatgpt whether i should include this or not
        # if menuItem['availableQuantity'] < 1:
        #     current_app.logger.warning("IncreaseCartItemQuantityFailed | id=%s | userId=%s | reason=MenuItemIsOutOfStock")
        #     return jsonify({"error": "Menu Item is Out of Stock!", "cartId": cartId}), 500      
        
        # Check if cart exist for this user  
        cart = Cart.find_cart_by_id(cartId)
        if not cart:
            # If Cart not exist
            current_app.logger.warning(
                "DecreaseCartItemQuantityFailed | id=%s | userId=%s | reason=CartNotExists",
                cartId, userId
            )
            return jsonify({"error": "Invalid Request! Cart not exist.", "cartId": cartId}), 404       
        # Check menuItem exist in this cart  
        itemExists = False
        for existing_item in cart['items']:
            if existing_item['menuItemId'] == menuItemId:
                itemExists = True
                # Check if the quantity is above 1
                if existing_item['quantity'] > 1:
                    # Decrease cart item quantity and price
                    existing_item['quantity'] -= 1
                    existing_item['totalPrice'] -= existing_item['price']
                else:
                    cart['items'].remove(existing_item)
                break        
        if not itemExists:
            # If item not exist
            current_app.logger.warning(
                "DecreaseCartItemQuantityFailed | id=%s | menuItemId=%s | userId=%s | reason=ItemNotExistsInCart",
                cartId, menuItemId, userId
            )
            return jsonify({"error": "Invalid Request! Item not exist in Cart.", "cartId": cartId}), 404
        
        if len(cart['items']) == 0:
            # delete this cart
            success = Cart.delete_cart(cartId)
            if success:
                current_app.logger.info(
                    "DecreaseCartItemQuantityFailed | id=%s | userId=%s",
                    cartId, userId
                )
                return jsonify({"message": "Item quantity decreased successfully! Cart Deleted!", "cartId": cartId}), 200 
        else:        
            # Calculate total amount
            totalAmount = 0                                                                                                                                             
            for item in cart['items']:
                totalAmount += item['totalPrice'] 
        
        # Save updated cart
        success = Cart.update_cart(cart['id'], {"items": cart['items'], "totalAmount": totalAmount})
            
        if success:
            # Get updated menuItem data
            updated_cart = Cart.find_cart_by_id(cart['id'])
            current_app.logger.info(
                "DecreaseCartItemQuantitySuccess | id=%s | userId=%s",
                cart["id"], userId
            )
            return jsonify({"message": "Item quantity decreased successfully!", "cart": updated_cart}), 200    
        
    
    except Exception as e:
        current_app.logger.error(
            "IncreaseCartItemQuantityException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Failed to increase cart item quantity", "details": str(e)}), 500  

@user_cart_bp.route('/deleteItem', methods=['DELETE'])
def delete_Item():
    """delete item from cart""" 
    try:
        data = request.get_json()
        required_fields = ['cartId','menuItemId','userId']  
        for field in required_fields:
            if field not in data or not data[field]:
                current_app.logger.warning(
                    "DeleteCartItemValidationFailed | field=%s | payload=%s",
                    field, data
                )
                return jsonify({"error": f"{field} is required"}), 400 
        
        cartId = data['cartId'].strip()
        menuItemId = data['menuItemId'].strip()
        userId = data['userId'].strip()
        
        # Check if cart exist for this user
        cart = Cart.find_cart_by_id(cartId)
        # If cart exist
        if cart:
            # Check the item exist in the list
            # if item exist in cart increase its quantity and total price
            itemExists = False
            for existing_item in cart['items']:
                if existing_item['menuItemId'] == menuItemId:
                    itemExists = True
                    founded_item = existing_item
                    break
                
            if not itemExists:
                 # If item not exist
                current_app.logger.warning(
                    "CartItemDeleteFailed | id=%s | menuItemId=%s | userId=%s | reason=ItemNotExistsInCart",
                    cartId, menuItemId, userId
                )
                return jsonify({"error": "Invalid Request! Item not exist in Cart.", "cartId": cartId}), 404     
            
            # If item exist               
            # Remove item
            cart['items'].remove(founded_item) 
            
            if len(cart['items']) == 0:
                # delete this cart
                success = Cart.delete_cart(cartId)
                if success:
                    current_app.logger.info(
                        "CartItemDeleted | id=%s | userId=%s",
                        cartId, userId
                    )
                    return jsonify({"message": "Item removed from cart successfully! Cart Deleted!", "cartId": cartId}), 200 
            else:        
                # Calculate total amount
                totalAmount = 0                                                                                                                                             
                for item in cart['items']:
                    totalAmount += item['totalPrice']
            
            # Save updated cart
            success = Cart.update_cart(cart['id'], {"items": cart['items'], "totalAmount": totalAmount})
            
            if success:
                updated_cart = Cart.find_cart_by_id(cart['id'])
                current_app.logger.info(
                    "CartItemDeleted | id=%s | userId=%s",
                    cart["id"], userId
                )
                return jsonify({"message": "Item removed from cart successfully", "cartId": cartId}), 200
            else:
                current_app.logger.warning(
                    "CartItemDeleteFailed | id=%s | userId=%s | reason=CartUpdateFailed",
                    cart["id"], userId
                )
                return jsonify({"error": "Failed to update cart.", "cartId": cartId}), 500  
            
        else:
            # If Cart not exist
            current_app.logger.warning(
                "CartItemDeleteFailed | id=%s | userId=%s | reason=CartNotExists",
                cartId, userId
            )
            return jsonify({"error": "Invalid Request! Cart not exist.", "cartId": cartId}), 404    
          
    except Exception as e:
        current_app.logger.error(
            "CartItemDeleteException | error=%s\n%s",
            str(e),
            traceback.format_exc()
        )
        return jsonify({"error": "Failed to remove item from cart", "details": str(e)}), 500
    # Remaining/Still not required: Do not take restaurantId of item internally check belongs to same restaurant of cart

        
                           
            
         
            
            
            
            
                    
                
                
        
        