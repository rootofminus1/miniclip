import json
import os
import uuid
from datetime import datetime, timezone
import boto3

dynamodb = boto3.resource("dynamodb")
clips_table = dynamodb.Table(os.environ["CLIPS_TABLE"])
sfn = boto3.client("stepfunctions", region_name="eu-west-1")
STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]


def resp(code, body):
    return {
        "statusCode": code,
        "headers": {"content-type": "application/json", "access-control-allow-origin": "*"},
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return resp(400, {"error": "invalid JSON"})

    upload_id = (body.get("upload_id") or "").strip()
    s3_key = (body.get("s3_key") or "").strip()
    user_id = (event.get("headers") or {}).get("x-user-id", "").strip()
    start_sec = body.get("start_sec")
    end_sec = body.get("end_sec")

    if not upload_id or not s3_key or start_sec is None or end_sec is None:
        return resp(400, {"error": "missing upload_id, s3_key, start_sec or end_sec"})

    clip_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    clips_table.put_item(Item={
        "pk": clip_id,
        "sk": created_at,
        "clip_id": clip_id,
        "upload_id": upload_id,
        "user_id": user_id,
        "start_sec": str(start_sec),
        "end_sec": str(end_sec),
        "status": "pending",
        "deleted": False,
        "created_at": created_at,
    })

    sfn.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        name=clip_id,
        input=json.dumps({
            "clip_id": clip_id,
            "upload_id": upload_id,
            "user_id": user_id,
            "s3_key": s3_key,
            "start_sec": str(start_sec),
            "end_sec": str(end_sec),
        }),
    )

    return resp(202, {"clip_id": clip_id, "status": "pending"})