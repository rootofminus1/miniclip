import json
import os
import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource("dynamodb")
clips_table = dynamodb.Table(os.environ["CLIPS_TABLE"])


def resp(code, body):
    return {
        "statusCode": code,
        "headers": {"content-type": "application/json", "access-control-allow-origin": "*"},
        "body": json.dumps(body),
    }

def lambda_handler(event, context):
    params = event.get("queryStringParameters") or {}
    upload_id = params.get("upload_id")
    user_id = (event.get("headers") or {}).get("x-user-id", "").strip()

    try:
        if upload_id:
            result = clips_table.query(
                IndexName="GSI-upload_id",
                KeyConditionExpression=Key("upload_id").eq(upload_id),
                FilterExpression=Attr("deleted").ne(True),
            )
        else:
            result = clips_table.query(
                IndexName="GSI-user_id",
                KeyConditionExpression=Key("user_id").eq(user_id),
                FilterExpression=Attr("deleted").ne(True),
            )
        return resp(200, {"clips": result["Items"]})
    except Exception as e:
        return resp(500, {"error": str(e)})