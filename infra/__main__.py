import pulumi
import pulumi_aws as aws
from cdn import make_cdn, make_clips_cdn
from dynamo import make_table
from lambdas import make_lambda, make_worker_lambda
from roles import basic_logs_role, list_clips_role, list_uploads_role, poll_job_role, presign_upload_role, presign_view_role, process_video_role, start_job_role, thumbnail_role, update_status_role, validate_file_role
from s3 import make_bucket
from api import RouteConfig, make_api
from sqs import make_queue
from step_function import make_step_function

app = f"miniclip2"
ALLOWED_USERS = "u1,u2,u3"


thumbnail_queue = make_queue(f"{app}-thumbnail-queue")

uploads_bucket = make_bucket(f"{app}-uploads", notify_queue_arn=thumbnail_queue.arn)
clips_bucket = make_bucket(f"{app}-clips")
clips_cdn = make_clips_cdn(f"{app}-clips-cdn", clips_bucket)


# uploads: 
# pk = user_id
# sk = created_at
# gsi = upload_id (query one specific upload)
uploads_table = make_table(f"{app}-uploads", gsi_keys=["upload_id"])

# clips: 
# pk = clip_id
# sk = created_at, 
# gsi1 = upload_id (list clips for an upload)
# gsi2 = user_id (list all clips for a user)
clips_table = make_table(f"{app}-clips", gsi_keys=["upload_id", "user_id"])



thumbnail_fn = make_worker_lambda(
    f"{app}-generate-thumbnail",
    "generate_thumbnail",
    thumbnail_role(f"{app}-generate-thumbnail", uploads_bucket, uploads_table, thumbnail_queue),
    { "UPLOADS_BUCKET": uploads_bucket.id, "UPLOADS_TABLE": uploads_table.name},
)

aws.lambda_.EventSourceMapping(
    f"{app}-thumbnail-event",
    event_source_arn=thumbnail_queue.arn,
    function_name=thumbnail_fn.name,
    batch_size=5,
)

validate_file_fn = make_worker_lambda(
    f"{app}-validate-file", "validate_file",
    validate_file_role(f"{app}-validate-file", uploads_bucket),
    {"UPLOADS_BUCKET": uploads_bucket.id},
)
process_video_fn = make_worker_lambda(
    f"{app}-process-video", "process_video",
    process_video_role(f"{app}-process-video", uploads_bucket, clips_bucket, clips_table),
    {"UPLOADS_BUCKET": uploads_bucket.id, "CLIPS_BUCKET": clips_bucket.id, "CLIPS_TABLE": clips_table.name},
)
update_status_fn = make_lambda(
    f"{app}-update-status", "update_status",
    update_status_role(f"{app}-update-status", clips_table),
    {"CLIPS_TABLE": clips_table.name},
)

state_machine = make_step_function(
    f"{app}-clip-pipeline",
    validate_file_fn,
    process_video_fn,
    update_status_fn,
)


validate_user_fn = make_lambda(
    f"{app}-validate-user", "validate_user",
    basic_logs_role(f"{app}-validate-user"),
    {"ALLOWED_USERS": ALLOWED_USERS},
)

presign_upload_fn = make_lambda(
    f"{app}-presign-upload", "presign_upload",
    presign_upload_role(f"{app}-presign-upload", uploads_bucket, uploads_table),
    {"BUCKET_NAME": uploads_bucket.id, "UPLOADS_TABLE": uploads_table.name, "URL_EXPIRY_SECONDS": "600", "MAX_UPLOAD_BYTES": "500000000"},
)
presign_view_fn = make_lambda(
    f"{app}-presign-view", "presign_view",
    presign_view_role(f"{app}-presign-view", uploads_bucket),
    {"BUCKET_NAME": uploads_bucket.id, "URL_EXPIRY_SECONDS": "600"},
)
start_job_fn = make_lambda(
    f"{app}-start-job", "start_job",
    start_job_role(f"{app}-start-job", clips_table, state_machine),
    {"CLIPS_TABLE": clips_table.name, "STATE_MACHINE_ARN": state_machine.arn},
)
poll_job_fn = make_lambda(
    f"{app}-poll-job", "poll_job",
    poll_job_role(f"{app}-poll-job", clips_table),
    {"CLIPS_TABLE": clips_table.name},
)
list_uploads_fn = make_lambda(
    f"{app}-list-uploads", "list_uploads",
    list_uploads_role(f"{app}-list-uploads", uploads_table),
    {"UPLOADS_TABLE": uploads_table.name},
)
list_clips_fn = make_lambda(
    f"{app}-list-clips", "list_clips",
    list_clips_role(f"{app}-list-clips", clips_table),
    {"CLIPS_TABLE": clips_table.name},
)


api = make_api(
    f"{app}-api",
    routes=[
        RouteConfig(method="POST", path="/uploads/presign", lambda_fn=presign_upload_fn, caching_ttl=None),
        RouteConfig(method="GET", path="/uploads/presign", lambda_fn=presign_view_fn, caching_ttl=None),
        RouteConfig(method="GET", path="/uploads", lambda_fn=list_uploads_fn, caching_ttl=60),
        RouteConfig(method="POST", path="/jobs", lambda_fn=start_job_fn, caching_ttl=None),
        RouteConfig(method="GET", path="/jobs/{id}", lambda_fn=poll_job_fn, caching_ttl=None),
        RouteConfig(method="GET", path="/clips", lambda_fn=list_clips_fn, caching_ttl=None),
    ],
    validate_user_fn=validate_user_fn,
)




dummy_fn = make_worker_lambda(
    f"{app}-dummy",
    "dummy",
    basic_logs_role(f"{app}-dummy"),
    {}
)

probe_url = aws.lambda_.FunctionUrl(
    f"{app}-dummy-url",
    function_name=dummy_fn.name,
    authorization_type="NONE",
)

pulumi.export("ffmpegDummyUrl", probe_url.function_url)

pulumi.export("clipscdnUrl", clips_cdn.domain_name)
pulumi.export("apiUrl", api.api_endpoint)
