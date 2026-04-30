import os
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
clips_table = dynamodb.Table(os.environ["CLIPS_TABLE"])


def lambda_handler(event, context):
    clip_id = event["clip_id"]
    status = event["status"]  # "done" or "failed"
    error = event.get("error")
    output_key = event.get("output_key")


    result = clips_table.query(
        KeyConditionExpression=Key("pk").eq(clip_id),
        Limit=1,
    )
    items = result.get("Items", [])
    if not items:
        raise Exception(f"clip not found: {clip_id}")

    sk = items[0]["sk"]

    expr = "SET #st = :status"
    names = {"#st": "status"}
    values = {":status": status}

    if output_key:
        expr += ", output_key = :output_key"
        values[":output_key"] = output_key

    if error:
        expr += ", error_message = :error"
        values[":error"] = error


    clips_table.update_item(
        Key={"pk": clip_id, "sk": sk},
        UpdateExpression=expr,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )

    return event