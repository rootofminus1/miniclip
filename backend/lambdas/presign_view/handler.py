import json
import os
import boto3
from botocore.client import Config

s3 = boto3.client(
    "s3",
    region_name="eu-west-1",
    config=Config(
        signature_version="s3v4",
        s3={"addressing_style": "virtual"}
    )
)

BUCKET = os.environ["BUCKET_NAME"]
EXPIRY = int(os.environ.get("URL_EXPIRY_SECONDS", "600"))


def resp(code, body):
    return {
        "statusCode": code,
        "headers": {
            "content-type": "application/json",
            "access-control-allow-origin": "*",
        },
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    params = event.get("queryStringParameters") or {}
    key = (params.get("key") or "").strip()
    kind = (params.get("kind") or "video").strip()

    if not key:
        return resp(400, {"error": "missing key"})

    try:
        response_type = "video/mp4" if kind == "video" else "image/jpeg"

        url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": BUCKET,
                "Key": key,
                "ResponseContentType": response_type,
                "ResponseContentDisposition": "inline",
            },
            ExpiresIn=EXPIRY,
        )

        return resp(200, {
            "url": url,
            "type": "s3_presigned",
            "kind": kind,
        })

    except Exception as e:
        return resp(500, {"error": str(e)})