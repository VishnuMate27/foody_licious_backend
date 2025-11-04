import os
from werkzeug.utils import secure_filename
from botocore.exceptions import ClientError, NoCredentialsError

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_IMAGES = 3

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_images_to_s3(s3_client, bucket_name, region, images, restaurant_id, folder, item_id, sub_folder=""):
    """
    Reusable helper to upload one or more images to AWS S3.
    Returns: (uploaded_urls, error_message)
    """
    uploaded_urls = []

    try:
        for index, image in enumerate(images):
            if image.filename == "":
                return None, "One of the image files has no filename."
            if not allowed_file(image.filename):
                return None, f"Unsupported file type: {image.filename}"
            if len(images) > MAX_IMAGES:
                return None, f"Maximum {MAX_IMAGES} images are allowed."

            # Secure and deterministic filename
            filename = secure_filename(image.filename)
            file_ext = filename.rsplit('.', 1)[1].lower()
            filename = f"image_{index + 1}.{file_ext}"

            # Build S3 key
            if sub_folder:
                s3_key = f"{folder.rstrip('/')}/{restaurant_id}/{sub_folder.rstrip('/')}/{item_id}/{filename}"
            else:
                s3_key = f"{folder.rstrip('/')}/{restaurant_id}/{item_id}/{filename}"

            # Delete existing image if it exists
            try:
                s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
                print(f"Deleted old image: {s3_key}")
            except ClientError as e:
                if e.response["Error"]["Code"] != "404":
                    raise e

            # Upload file
            s3_client.upload_fileobj(
                image,
                bucket_name,
                s3_key,
                ExtraArgs={"ContentType": image.content_type}
            )

            file_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
            uploaded_urls.append(file_url)

        return uploaded_urls, None

    except (NoCredentialsError, ClientError) as e:
        print(f"S3 Upload Error: {e}")
        return None, "Image upload failed. Please check server logs."

def delete_s3_folder(s3_client, bucket_name: str, folder_prefix: str) -> dict:
    """
    Delete all objects under a given prefix (folder) in an existing S3 bucket.

    Args:
        s3_client: An initialized boto3 S3 client (reuse your global one).
        bucket_name (str): The name of the S3 bucket.
        folder_prefix (str): Folder path (prefix) to delete, e.g. 'restaurants/abc123/menu_items/'.

    Returns:
        dict: Summary of deletion results including counts and deleted keys.
    """
    # Ensure prefix ends with '/'
    if not folder_prefix.endswith("/"):
        folder_prefix += "/"

    deleted_files = []
    errors = []

    try:
        paginator = s3_client.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=bucket_name, Prefix=folder_prefix):
            # Skip empty pages (no objects under prefix)
            if "Contents" not in page:
                continue

            # Collect object keys to delete
            objects_to_delete = [{"Key": obj["Key"]} for obj in page["Contents"]]

            # Batch delete
            response = s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={"Objects": objects_to_delete}
            )

            # Aggregate results
            deleted_files.extend([d["Key"] for d in response.get("Deleted", [])])
            errors.extend(response.get("Errors", []))

        return {
            "message": (
                "Folder deleted successfully from S3."
                if deleted_files else "No objects found under the specified prefix."
            ),
            "prefix_deleted": folder_prefix,
            "deleted_count": len(deleted_files),
            "error_count": len(errors),
            "deleted_files": deleted_files,
            "errors": errors,
        }

    except ClientError as e:
        print(f"S3 Deletion Error: {e}")
        return {
            "message": "Failed to delete folder from S3.",
            "prefix_deleted": folder_prefix,
            "deleted_count": 0,
            "error_count": 1,
            "errors": [str(e)],
        }
        
def delete_images_from_s3(image_urls: list[str], bucket_name: str, s3_client=None) -> dict:
    """
    Deletes multiple images from AWS S3 using their image URLs.

    Args:
        image_urls (list[str]): List of image URLs to delete.
        bucket_name (str): Name of the S3 bucket.
        s3_client (boto3.client, optional): Reusable S3 client. If not provided, a new one is created.

    Returns:
        dict: {
            "deleted": [list of deleted keys],
            "errors": [list of error messages]
        }
    """
    if not image_urls:
        return {"deleted": [], "errors": ["No image URLs provided."]}

    if not s3_client:
        s3_client = boto3.client('s3')

    deleted_keys = []
    errors = []

    try:
        # Convert URLs to object keys
        keys_to_delete = []
        for url in image_urls:
            try:
                parsed = urlparse(url)
                key = parsed.path.lstrip('/')
                keys_to_delete.append({'Key': key})
            except Exception as e:
                errors.append(f"Invalid URL {url}: {e}")

        # Perform deletion in batches of 1000
        for i in range(0, len(keys_to_delete), 1000):
            batch = keys_to_delete[i:i+1000]
            response = s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': batch}
            )

            # Collect successfully deleted keys
            if 'Deleted' in response:
                deleted_keys.extend([obj['Key'] for obj in response['Deleted']])

            # Collect errors if any
            if 'Errors' in response:
                for err in response['Errors']:
                    errors.append(f"{err['Key']}: {err.get('Message', 'Unknown error')}")

    except Exception as e:
        errors.append(str(e))

    return {"deleted": deleted_keys, "errors": errors}        