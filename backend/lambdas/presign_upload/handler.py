import json
import os
import uuid
import boto3
from datetime import datetime
from botocore.client import Config

s3 = boto3.client("s3", region_name="eu-west-1", config=Config(signature_version="s3v4"))
dynamodb = boto3.resource("dynamodb")
uploads_table = dynamodb.Table(os.environ["UPLOADS_TABLE"])

BUCKET = os.environ["BUCKET_NAME"]
EXPIRY = int(os.environ.get("URL_EXPIRY_SECONDS", "600"))


def resp(code, body):
    return {
        "statusCode": code,
        "headers": {"content-type": "application/json", "access-control-allow-origin": "*"},
        "body": json.dumps(body),
    }

def lambda_handler(event, context):
    print("starting")
    user_id = (event.get("headers") or {}).get("x-user-id", "").strip()
    upload_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    s3_key = f"{user_id}/{upload_id}.mp4"

    raw_body = event.get("body") or "{}"
    try:
        print("trying 1")
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        print("except 1")
        body = {}

    filename = (body.get("filename") or "untitled.mp4").strip().replace("/", "_")[:120]

    try:
        print("trying 2")
        presigned_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": BUCKET,
                "Key": s3_key,
                "ContentType": "video/mp4",
            },
            ExpiresIn=EXPIRY,
        )
        print("url generated")

        uploads_table.put_item(Item={
            "pk": user_id,
            "sk": created_at,
            "upload_id": upload_id,
            "s3_key": s3_key,
            "filename": filename,
            "status": "pending",
            "thumbnail_ready": False,
            "created_at": created_at,
        })

        return resp(200, {
            "upload_id": upload_id,
            "presigned_url": presigned_url,
            "s3_key": s3_key,
        })
    except Exception as e:
        print("except 2")
        return resp(500, {"error": str(e)})