import json
import os
import subprocess
import boto3
from boto3.dynamodb.conditions import Key

s3 = boto3.client("s3", region_name="eu-west-1")
dynamodb = boto3.resource("dynamodb")

TABLE = dynamodb.Table(os.environ["UPLOADS_TABLE"])
BUCKET = os.environ["UPLOADS_BUCKET"]

TMP = "/tmp"
FFMPEG = "/opt/bin/ffmpeg"


def lambda_handler(event, context):
    print("thumbnail worker start")
    print("ffmpeg_exists:", os.path.exists(FFMPEG))

    for record in event["Records"]:
        body = json.loads(record["body"])

        print("THE BODY WAS", body)

        if "Records" not in body:
            print("skipping non-s3 message:", body)
            continue

        for s3_event in body["Records"]:
            key = s3_event["s3"]["object"]["key"]
            print("processing:", key)

            user_id, filename = key.split("/", 1)
            upload_id = filename.replace(".mp4", "")
            thumb_key = key.replace(".mp4", ".jpg")

            input_path = f"{TMP}/{upload_id}.mp4"
            output_path = f"{TMP}/{upload_id}.jpg"

            s3.download_file(BUCKET, key, input_path)

            cmd = [
                FFMPEG,
                "-y",
                "-i", input_path,
                "-frames:v", "1",
                output_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"ffmpeg failed: {result.stderr[-500:]}")

            s3.upload_file(
                output_path,
                BUCKET,
                thumb_key,
                ExtraArgs={"ContentType": "image/jpeg"},
            )

            res = TABLE.query(
                IndexName="GSI-upload_id", 
                KeyConditionExpression=Key("upload_id").eq(upload_id),
            )

            items = res.get("Items", [])
            if not items:
                print("no item found for upload_id:", upload_id)
                continue


            item = items[0]

            TABLE.update_item(
                Key={
                    "pk": item["pk"],
                    "sk": item["sk"],
                },
                UpdateExpression="SET thumbnail_ready = :t, thumbnail_key = :k",
                ExpressionAttributeValues={
                    ":t": True,
                    ":k": thumb_key,
                },
            )

            os.remove(input_path)
            os.remove(output_path)

    return {"ok": True}