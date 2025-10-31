from bson import ObjectId
from datetime import datetime

def serialize_object_id(value):
    """Convert ObjectId to string safely."""
    if isinstance(value, ObjectId):
        return str(value)
    return value

def serialize_datetime(value):
    """Format datetime to JSON-friendly dict with $date."""
    if isinstance(value, datetime):
        return {"$date": value.isoformat()}
    return value

def serialize_doc(doc):
    """
    Recursively convert MongoDB document into clean JSON-serializable dict.
    - Converts _id -> id
    - Converts ObjectId to string
    - Converts datetime to { "$date": ISO_STRING }
    """
    if isinstance(doc, list):
        return [serialize_doc(d) for d in doc]

    if isinstance(doc, dict):
        new_doc = {}
        for k, v in doc.items():
            # Rename _id -> id
            if k == "_id":
                new_doc["id"] = serialize_object_id(v)
            else:
                new_doc[k] = serialize_doc(v)
        return new_doc

    # Handle special types
    if isinstance(doc, ObjectId):
        return serialize_object_id(doc)
    if isinstance(doc, datetime):
        return serialize_datetime(doc)

    return doc
