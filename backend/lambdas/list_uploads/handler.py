import json
import os
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
uploads_table = dynamodb.Table(os.environ["UPLOADS_TABLE"])


def resp(code, body):
    return {
        "statusCode": code,
        "headers": {"content-type": "application/json", "access-control-allow-origin": "*"},
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    user_id = (event.get("headers") or {}).get("x-user-id", "").strip()
    try:
        result = uploads_table.query(
            KeyConditionExpression=Key("pk").eq(user_id)
        )
        return resp(200, {"uploads": result["Items"]})
    except Exception as e:
        return resp(500, {"error": str(e)})