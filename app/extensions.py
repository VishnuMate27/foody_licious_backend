import boto3
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
import os

mongo = PyMongo()
bcrypt = Bcrypt()

s3_client = None  # will be initialized later
S3_BUCKET = os.getenv("AWS_S3_BUCKET_NAME")
S3_REGION = os.getenv("AWS_REGION")

def init_s3(app):
    """Initialize AWS S3 client with Flask app context."""
    global s3_client
    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "ap-south-1"),
        )
        app.logger.info("AWS S3 client initialized successfully")
    except Exception as e:
        app.logger.error(f"Failed to initialize S3 client: {e}")
        s3_client = None
