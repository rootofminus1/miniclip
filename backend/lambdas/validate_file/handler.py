import os
import boto3

s3 = boto3.client("s3", region_name="eu-west-1")
UPLOADS_BUCKET = os.environ["UPLOADS_BUCKET"]


def lambda_handler(event, context):
    s3_key = event.get("s3_key", "")

    if not s3_key:
        return {**event, "valid": False, "error": "missing s3_key"}

    try:
        head = s3.head_object(Bucket=UPLOADS_BUCKET, Key=s3_key)
        size = head["ContentLength"]

        if size == 0:
            return {**event, "valid": False, "error": "file is empty"}
            
        return {**event, "valid": True}
    except s3.exceptions.NoSuchKey:
        return {**event, "valid": False, "error": "file not found"}
    except Exception as e:
        return {**event, "valid": False, "error": str(e)}