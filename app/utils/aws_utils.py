import os
from werkzeug.utils import secure_filename
from botocore.exceptions import ClientError, NoCredentialsError
import boto3
from urllib.parse import urlparse

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_IMAGES = 3

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Working code
# def upload_images_to_s3(s3_client, bucket_name, region, images, restaurant_id, folder, item_id, sub_folder=""):
#     """
#     Reusable helper to upload one or more images to AWS S3.
#     Logic:
#       - If existing images < 3 → append new images
#       - Else → replace (delete and reupload)
#     Returns: (uploaded_urls, error_message)
#     """
#     uploaded_urls = []

#     try:
#         # 1️⃣ Determine base path and list existing images
#         if sub_folder:
#             prefix = f"{folder.rstrip('/')}/{restaurant_id}/{sub_folder.rstrip('/')}/{item_id}/"
#         else:
#             prefix = f"{folder.rstrip('/')}/{restaurant_id}/{item_id}/"

#         existing_objs = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
#         existing_urls = []

#         if "Contents" in existing_objs:
#             for obj in existing_objs["Contents"]:
#                 key = obj["Key"]
#                 file_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{key}"
#                 existing_urls.append(file_url)

#         existing_count = len(existing_urls)
#         print(f"Found {existing_count} existing images for item {item_id}")

#         # 2️⃣ Check max image count rule
#         if len(images) > MAX_IMAGES:
#             return None, f"Maximum {MAX_IMAGES} images are allowed."

#         # 3️⃣ If >= 3 → clear old images first
#         if existing_count >= 3:
#             print(f"Replacing {existing_count} existing images...")
#             for obj in existing_objs.get("Contents", []):
#                 s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])

#         # 4️⃣ Compute starting index for new images
#         start_index = existing_count + 1 if existing_count < 3 else 1

#         for index, image in enumerate(images):
#             if image.filename == "":
#                 return None, "One of the image files has no filename."
#             if not allowed_file(image.filename):
#                 return None, f"Unsupported file type: {image.filename}"

#             # Secure and deterministic filename
#             filename = secure_filename(image.filename)
#             file_ext = filename.rsplit('.', 1)[1].lower()
#             filename = f"image_{start_index + index}.{file_ext}"

#             # Build S3 key
#             if sub_folder:
#                 s3_key = f"{folder.rstrip('/')}/{restaurant_id}/{sub_folder.rstrip('/')}/{item_id}/{filename}"
#             else:
#                 s3_key = f"{folder.rstrip('/')}/{restaurant_id}/{item_id}/{filename}"

#             # Upload file
#             s3_client.upload_fileobj(
#                 image,
#                 bucket_name,
#                 s3_key,
#                 ExtraArgs={"ContentType": image.content_type}
#             )

#             file_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
#             uploaded_urls.append(file_url)

#         # Combine with existing if appending
#         if existing_count < 3:
#             uploaded_urls = existing_urls + uploaded_urls

#         return uploaded_urls, None

#     except (NoCredentialsError, ClientError) as e:
#         print(f"S3 Upload Error: {e}")
#         return None, "Image upload failed. Please check server logs."

def upload_images_to_s3(s3_client, bucket_name, region, images, restaurant_id, folder, item_id, sub_folder=""):
    """
    Reusable helper to upload one or more images to AWS S3.
    Returns:
      uploaded_urls: list of only newly uploaded image URLs
      existing_urls: list of existing image URLs (if needed)
      error_message: str or None
    """
    uploaded_urls = []
    existing_urls = []

    try:
        # 1️⃣ Determine base path and list existing images
        if sub_folder:
            prefix = f"{folder.rstrip('/')}/{restaurant_id}/{sub_folder.rstrip('/')}/{item_id}/"
        else:
            prefix = f"{folder.rstrip('/')}/{restaurant_id}/{item_id}/"

        existing_objs = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

        if "Contents" in existing_objs:
            for obj in existing_objs["Contents"]:
                key = obj["Key"]
                file_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{key}"
                existing_urls.append(file_url)

        existing_count = len(existing_urls)
        print(f"Found {existing_count} existing images for item {item_id}")

        # 2️⃣ Check max image count rule
        if len(images) > MAX_IMAGES:
            return None, None, f"Maximum {MAX_IMAGES} images are allowed."

        # 3️⃣ If >= 3 → clear old images first
        if existing_count >= 3:
            print(f"Replacing {existing_count} existing images...")
            for obj in existing_objs.get("Contents", []):
                s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
            existing_count = 0  # reset count after clearing

        # 4️⃣ Compute starting index for new images
        start_index = existing_count + 1 if existing_count < 3 else 1

        # 5️⃣ Upload new images
        for index, image in enumerate(images):
            if image.filename == "":
                return None, None, "One of the image files has no filename."
            if not allowed_file(image.filename):
                return None, None, f"Unsupported file type: {image.filename}"

            filename = secure_filename(image.filename)
            # file_ext = filename.rsplit('.', 1)[1].lower()
            # filename = f"image_{start_index + index}.{file_ext}"

            if sub_folder:
                s3_key = f"{folder.rstrip('/')}/{restaurant_id}/{sub_folder.rstrip('/')}/{item_id}/{filename}"
            else:
                s3_key = f"{folder.rstrip('/')}/{restaurant_id}/{item_id}/{filename}"

            s3_client.upload_fileobj(
                image,
                bucket_name,
                s3_key,
                ExtraArgs={"ContentType": image.content_type}
            )

            file_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
            uploaded_urls.append(file_url)

        # ✅ Return only newly uploaded images in `uploaded_urls`
        return uploaded_urls, existing_urls, None

    except (NoCredentialsError, ClientError) as e:
        print(f"S3 Upload Error: {e}")
        return None, None, "Image upload failed. Please check server logs."

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
        
# def delete_images_from_s3(image_urls: list[str], bucket_name: str, s3_client=None) -> dict:
#     """
#     Deletes multiple images from AWS S3 using their image URLs.

#     Args:
#         image_urls (list[str]): List of image URLs to delete.
#         bucket_name (str): Name of the S3 bucket.
#         s3_client (boto3.client, optional): Reusable S3 client. If not provided, a new one is created.

#     Returns:
#         dict: {
#             "deleted": [list of deleted keys],
#             "errors": [list of error messages]
#         }
#     """
#     if not image_urls:
#         return {"deleted": [], "errors": ["No image URLs provided."]}

#     if not s3_client:
#         s3_client = boto3.client('s3')

#     deleted_keys = []
#     errors = []

#     try:
#         # Convert URLs to object keys
#         keys_to_delete = []
#         for url in image_urls:
#             try:
#                 parsed = urlparse(url)
#                 key = parsed.path.lstrip('/')
#                 keys_to_delete.append({'Key': key})
#             except Exception as e:
#                 errors.append(f"Invalid URL {url}: {e}")

#         # Perform deletion in batches of 1000
#         for i in range(0, len(keys_to_delete), 1000):
#             batch = keys_to_delete[i:i+1000]
#             response = s3_client.delete_objects(
#                 Bucket=bucket_name,
#                 Delete={'Objects': batch}
#             )

#             # Collect successfully deleted keys
#             if 'Deleted' in response:
#                 deleted_keys.extend([obj['Key'] for obj in response['Deleted']])

#             # Collect errors if any
#             if 'Errors' in response:
#                 for err in response['Errors']:
#                     errors.append(f"{err['Key']}: {err.get('Message', 'Unknown error')}")

#     except Exception as e:
#         errors.append(str(e))

#     return {"deleted": deleted_keys, "errors": errors}      


def delete_images_from_s3(image_urls: list[str], s3_client=None) -> dict:
    """
    Deletes multiple images from AWS S3 using their URLs.
    """
    if not image_urls:
        return {"deleted": [], "errors": ["No image URLs provided."]}

    if not s3_client:
        s3_client = boto3.client('s3')

    deleted_keys = []
    errors = []

    try:
        # Parse bucket and key for each URL
        objects_by_bucket = {}
        for url in image_urls:
            try:
                parsed = urlparse(url)
                bucket = parsed.netloc.split('.')[0]
                key = parsed.path.lstrip('/').split('?')[0]

                objects_by_bucket.setdefault(bucket, []).append({'Key': key})
            except Exception as e:
                errors.append(f"Invalid URL {url}: {e}")

        # Delete per-bucket (in case URLs span multiple buckets)
        for bucket, keys_to_delete in objects_by_bucket.items():
            for i in range(0, len(keys_to_delete), 1000):
                batch = keys_to_delete[i:i + 1000]
                response = s3_client.delete_objects(
                    Bucket=bucket,
                    Delete={'Objects': batch}
                )
                deleted_keys.extend([obj['Key'] for obj in response.get('Deleted', [])])

                for err in response.get('Errors', []):
                    errors.append(f"{err['Key']}: {err.get('Message', 'Unknown error')}")

    except Exception as e:
        errors.append(str(e))

    return {"deleted": deleted_keys, "errors": errors}
  