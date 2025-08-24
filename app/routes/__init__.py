import firebase_admin
from firebase_admin import credentials
from flask import Flask
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Extensions
mongo = PyMongo()
bcrypt = Bcrypt()
cred = credentials.Certificate("serviceAccountKey.json")

def create_app():
    load_dotenv()  # Load from .env
    app = Flask(__name__)
    
    # Configuration
    app.config["MONGO_URI"] = os.getenv("MONGODB_URI")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    
    print("App Config", os.getenv("MONGODB_URI"))
    
    # Initialize extensions
    mongo.init_app(app)
    bcrypt.init_app(app)
    firebase_admin.initialize_app(cred)
    CORS(app, supports_credentials=True)
    
    # Register Blueprints - Import inside function to avoid circular imports
    from app.routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    
    from app.routes.user_routes import user_bp
    app.register_blueprint(user_bp, url_prefix="/api/users")
    
    # from app.routes.product_routes import product_bp
    # app.register_blueprint(product_bp, url_prefix="/api/products")
    # from app.routes.cart_routes import cart_bp
    # app.register_blueprint(cart_bp, url_prefix="/api/cart")
    # from app.routes.order_routes import order_bp
    # app.register_blueprint(order_bp, url_prefix="/api/order")
    # from app.routes.admin_routes import admin_bp
    # app.register_blueprint(admin_bp, url_prefix="/api/admin")
    
    return app