import firebase_admin
from firebase_admin import credentials
from flask import Flask
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from dotenv import load_dotenv
from io import StringIO
import os
import json

# Extensions
mongo = PyMongo()
bcrypt = Bcrypt()
# Load Firebase credentials from Hugging Face secret
firebase_creds = os.environ.get("FIREBASE_CREDENTIALS")

if firebase_creds:
    cred_dict = json.loads(firebase_creds)
    cred = credentials.Certificate(cred_dict)
else:
    cred = credentials.Certificate("serviceAccountKey.json")  # fallback for local

def create_app():
    dotenv_content = os.environ.get("DOTENV_FILE")
    if dotenv_content:
        load_dotenv(stream=StringIO(dotenv_content))  # load from Hugging Face secret
    else:
        load_dotenv()
    app = Flask(__name__)
    
    # Configuration
    app.config["MONGO_URI"] = os.getenv("MONGODB_URI")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    
    # Initialize extensions
    mongo.init_app(app)
    bcrypt.init_app(app)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    CORS(app, supports_credentials=True)
    
    # Register Blueprints - Import inside function to avoid circular imports
    from app.routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    
    from app.routes.restaurant_auth_routes import restaurant_auth_bp
    app.register_blueprint(restaurant_auth_bp, url_prefix="/api/restaurant/auth")
    
    from app.routes.user_routes import user_bp
    app.register_blueprint(user_bp, url_prefix="/api/users")
    
    from app.routes.restaurant_routes import restaurant_bp
    app.register_blueprint(restaurant_bp, url_prefix="/api/restaurants")
    
    # from app.routes.product_routes import product_bp
    # app.register_blueprint(product_bp, url_prefix="/api/products")
    # from app.routes.cart_routes import cart_bp
    # app.register_blueprint(cart_bp, url_prefix="/api/cart")
    # from app.routes.order_routes import order_bp
    # app.register_blueprint(order_bp, url_prefix="/api/order")
    # from app.routes.admin_routes import admin_bp
    # app.register_blueprint(admin_bp, url_prefix="/api/admin")
    
    return app