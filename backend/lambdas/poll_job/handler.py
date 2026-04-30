import json
import os
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
clips_table = dynamodb.Table(os.environ["CLIPS_TABLE"])


def resp(code, body):
    return {
        "statusCode": code,
        "headers": {"content-type": "application/json", "access-control-allow-origin": "*"},
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    clip_id = (event.get("pathParameters") or {}).get("id", "").strip()
    if not clip_id:
        return resp(400, {"error": "missing clip id"})

    result = clips_table.query(
        KeyConditionExpression=Key("pk").eq(clip_id),
        Limit=1,
    )

    items = result.get("Items", [])
    if not items:
        return resp(404, {"error": "clip not found"})

    clip = items[0]
    if clip.get("deleted"):
        return resp(404, {"error": "clip not found"})

    return resp(200, {"clip": clip})