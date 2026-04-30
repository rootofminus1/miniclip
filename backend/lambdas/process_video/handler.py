import os
import subprocess
import boto3
from boto3.dynamodb.conditions import Key

s3 = boto3.client("s3", region_name="eu-west-1")
dynamodb = boto3.resource("dynamodb")
clips_table = dynamodb.Table(os.environ["CLIPS_TABLE"])

UPLOADS_BUCKET = os.environ["UPLOADS_BUCKET"]
CLIPS_BUCKET = os.environ["CLIPS_BUCKET"]

TMP = "/tmp"
FFMPEG = "/opt/bin/ffmpeg"

def set_status(clip_id, status):
    result = clips_table.query(
        KeyConditionExpression=Key("pk").eq(clip_id),
        Limit=1,
    )
    items = result.get("Items", [])
    if not items:
        return
    clips_table.update_item(
        Key={"pk": clip_id, "sk": items[0]["sk"]},
        UpdateExpression="SET #st = :status",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={":status": status},
    )

def lambda_handler(event, context):
    print("process_video?")
    print("ffmpeg_exists: ", os.path.exists(FFMPEG))
    print("opt_bin: ", os.listdir("/opt/bin") if os.path.exists("/opt/bin") else None)

    clip_id = event["clip_id"]
    s3_key = event["s3_key"]
    start_sec = float(event["start_sec"])
    end_sec = float(event["end_sec"])
    duration = end_sec - start_sec

    set_status(clip_id, "processing")

    input_path = f"{TMP}/{clip_id}_input.mp4"
    output_path = f"{TMP}/{clip_id}_output.mp4"

    s3.download_file(UPLOADS_BUCKET, s3_key, input_path)

    print("file good")

    cmd = [
        FFMPEG, "-y",
        "-ss", str(start_sec),
        "-i", input_path,
        "-t", str(duration),
        "-vcodec", "libx264",
        "-crf", "28",
        "-preset", "fast",
        "-movflags", "+faststart",
        "-acodec", "aac",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"ffmpeg video failed: {result.stderr[-500:]}")

    print("all good still")


    set_status(clip_id, "uploading")

    output_key = f"{clip_id}.mp4"

    s3.upload_file(
        output_path,
        CLIPS_BUCKET,
        output_key,
        ExtraArgs={"ContentType": "video/mp4"},
    )

    print("uploaded")

    os.remove(input_path)
    os.remove(output_path)

    print("cleaned")

    return {**event, "output_key": output_key}