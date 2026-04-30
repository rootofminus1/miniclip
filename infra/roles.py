import pulumi_aws as aws
import json


def lambda_logs_policy(name: str):
    return aws.iam.Policy(
        name,
        policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                "Resource": "arn:aws:logs:*:*:*",
            }]
        })
    )


def s3_write_policy(name: str, bucket_arn, prefix: str = "*"):
    return aws.iam.Policy(
        name,
        policy=bucket_arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": ["s3:PutObject"],
                "Resource": f"{arn}/{prefix}",
            }]
        }))
    )


def s3_read_policy(name: str, bucket_arn, prefix: str = "*"):
    return aws.iam.Policy(
        name,
        policy=bucket_arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": ["s3:GetObject"],
                "Resource": f"{arn}/{prefix}",
            }]
        }))
    )


def s3_delete_policy(name: str, bucket_arn, prefix: str = "*"):
    return aws.iam.Policy(
        name,
        policy=bucket_arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": ["s3:DeleteObject"],
                "Resource": f"{arn}/{prefix}",
            }]
        }))
    )


def dynamo_put_policy(name: str, table_arn):
    return aws.iam.Policy(
        name,
        policy=table_arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": ["dynamodb:PutItem"],
                "Resource": arn,
            }]
        }))
    )


def dynamo_get_policy(name: str, table_arn):
    return aws.iam.Policy(
        name,
        policy=table_arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": ["dynamodb:GetItem"],
                "Resource": arn,
            }]
        }))
    )


def dynamo_update_policy(name: str, table_arn):
    return aws.iam.Policy(
        name,
        policy=table_arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": ["dynamodb:UpdateItem", "dynamodb:GetItem"],
                "Resource": [arn, f"{arn}/index/*"],
            }]
        }))
    )


def dynamo_query_policy(name: str, table_arn):
    return aws.iam.Policy(
        name,
        policy=table_arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": ["dynamodb:Query"],
                "Resource": [arn, f"{arn}/index/*"],
            }]
        }))
    )

def sfn_start_policy(name: str, state_machine_arn):
    return aws.iam.Policy(
        name,
        policy=state_machine_arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": "states:StartExecution",
                "Resource": arn,
            }]
        }))
    )

def sqs_consume_policy(name: str, queue_arn):
    return aws.iam.Policy(
        name,
        policy=queue_arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "sqs:ReceiveMessage",
                    "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes",
                ],
                "Resource": arn,
            }]
        }))
    )


def lambda_role(name: str):
    return aws.iam.Role(
        name,
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }]
        })
    )
    


def attach(role, policy, name: str):
    aws.iam.RolePolicyAttachment(
        name,
        role=role.id,
        policy_arn=policy.arn,
    )


logs_policy = lambda_logs_policy("shared-lambda-logs")


def attach_logs(role, name: str):
    attach(role, logs_policy, f"{name}-logs")


def basic_logs_role(name: str):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)
    return role


def presign_upload_role(name: str, bucket, uploads_table):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)
    attach(role, s3_write_policy(f"{name}-s3-write", bucket.arn, "*"), f"{name}-s3-write-attach")
    attach(role, dynamo_put_policy(f"{name}-dynamo-put", uploads_table.arn), f"{name}-dynamo-put-attach")
    return role


def presign_view_role(name: str, bucket):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)
    attach(role, s3_read_policy(f"{name}-s3-read", bucket.arn, "*"), f"{name}-s3-read-attach")
    return role



def start_job_role(name: str, clips_table, state_machine):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)
    attach(role, dynamo_put_policy(f"{name}-dynamo-put", clips_table.arn), f"{name}-dynamo-put-attach")
    attach(role, sfn_start_policy(f"{name}-sfn-start", state_machine.arn), f"{name}-sfn-start-attach")
    return role


def poll_job_role(name: str, clips_table):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)
    attach(role, dynamo_query_policy(f"{name}-dynamo-query", clips_table.arn), f"{name}-dynamo-query-attach")
    return role


def list_uploads_role(name: str, uploads_table):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)
    attach(role, dynamo_query_policy(f"{name}-dynamo-query", uploads_table.arn), f"{name}-dynamo-query-attach")
    return role


def list_clips_role(name: str, clips_table):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)
    attach(role, dynamo_query_policy(f"{name}-dynamo-query", clips_table.arn), f"{name}-dynamo-query-attach")
    return role


def delete_clip_role(name: str, clips_table, clips_bucket):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)
    attach(role, dynamo_update_policy(f"{name}-dynamo-update", clips_table.arn), f"{name}-dynamo-update-attach")
    attach(role, dynamo_query_policy(f"{name}-dynamo-query", clips_table.arn), f"{name}-dynamo-query-attach")
    attach(role, s3_delete_policy(f"{name}-s3-delete", clips_bucket.arn, "*.mp4"), f"{name}-s3-delete-attach")
    return role




def validate_file_role(name: str, uploads_bucket):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)
    attach(role, s3_read_policy(f"{name}-s3-read", uploads_bucket.arn, "*"), f"{name}-s3-read-attach")
    return role


def process_video_role(name: str, uploads_bucket, clips_bucket, clips_table):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)
    attach(role, s3_read_policy(f"{name}-s3-read", uploads_bucket.arn, "*"), f"{name}-s3-read-attach")
    attach(role, s3_write_policy(f"{name}-s3-write", clips_bucket.arn, "*"), f"{name}-s3-write-attach")
    attach(role, dynamo_update_policy(f"{name}-dynamo-update", clips_table.arn), f"{name}-dynamo-update-attach")
    attach(role, dynamo_query_policy(f"{name}-dynamo-query", clips_table.arn), f"{name}-dynamo-query-attach")
    return role


def update_status_role(name: str, clips_table):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)
    attach(role, dynamo_update_policy(f"{name}-dynamo", clips_table.arn), f"{name}-dynamo-attach")
    attach(role, dynamo_query_policy(f"{name}-dynamo-query", clips_table.arn), f"{name}-dynamo-query-attach")
    return role



def thumbnail_role(name: str, uploads_bucket, uploads_table, queue):
    role = lambda_role(f"{name}-role")
    attach_logs(role, name)

    attach(role, s3_read_policy(f"{name}-s3-read", uploads_bucket.arn, "*"), f"{name}-s3-read-attach")
    attach(role, s3_write_policy(f"{name}-s3-write", uploads_bucket.arn, "*.jpg"), f"{name}-s3-write-attach")
    attach(role, dynamo_update_policy(f"{name}-dynamo-update", uploads_table.arn), f"{name}-dynamo-update-attach")
    attach(role, dynamo_query_policy(f"{name}-dynamo-query", uploads_table.arn), f"{name}-dynamo-query-attach")
    attach(role, sqs_consume_policy(f"{name}-sqs", queue.arn), f"{name}-sqs-attach")

    return role