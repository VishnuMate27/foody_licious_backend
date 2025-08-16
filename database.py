from pymongo import MongoClient
from flask import current_app, g
import logging

def get_db():
    """Get database connection from Flask g object or create new one."""
    if 'db' not in g:
        client = MongoClient(current_app.config['MONGODB_URI'])
        g.db = client[current_app.config['MONGODB_DATABASE']]
        g.client = client
    return g.db

def close_db(error):
    """Close database connection."""
    client = g.pop('client', None)
    if client is not None:
        client.close()

def init_db(app):
    """Initialize database with app."""
    app.teardown_appcontext(close_db)
    
    # Test connection
    with app.app_context():
        try:
            db = get_db()
            # Ping the database
            db.command('ping')
            logging.info("Successfully connected to MongoDB")
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {e}")
            raise