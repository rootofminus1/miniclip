import json
import pulumi
import pulumi_aws as aws


def make_step_function(
    name: str,
    validate_file_fn: aws.lambda_.Function,
    process_video_fn: aws.lambda_.Function,
    update_status_fn: aws.lambda_.Function,
) -> aws.sfn.StateMachine:

    sfn_role = aws.iam.Role(
        f"{name}-sfn-role",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "states.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }],
        }),
    )

    invoke_policy = aws.iam.Policy(
        f"{name}-sfn-invoke-policy",
        policy=pulumi.Output.all(
            validate_file_fn.arn,
            process_video_fn.arn,
            update_status_fn.arn,
        ).apply(lambda arns: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": "lambda:InvokeFunction",
                "Resource": arns,
            }],
        })),
    )

    aws.iam.RolePolicyAttachment(
        f"{name}-sfn-invoke-attach",
        role=sfn_role.name,
        policy_arn=invoke_policy.arn,
    )

    definition = pulumi.Output.all(
        validate_file_fn.arn,
        process_video_fn.arn,
        update_status_fn.arn,
    ).apply(lambda arns: json.dumps({
        "Comment": "Video clip processing pipeline",
        "StartAt": "ValidateFile",
        "States": {
            "ValidateFile": {
                "Type": "Task",
                "Resource": arns[0],
                "Catch": [{
                    "ErrorEquals": ["States.ALL"],
                    "Next": "MarkFailed",
                    "ResultPath": "$.error_info",
                }],
                "Next": "IsFileValid",
            },
            "IsFileValid": {
                "Type": "Choice",
                "Choices": [{
                    "Variable": "$.valid",
                    "BooleanEquals": True,
                    "Next": "WaitBeforeProcessing",
                }],
                "Default": "MarkFailed",
            },
            "WaitBeforeProcessing": {
                "Type": "Wait",
                "Seconds": 1,
                "Next": "ProcessVideo",
            },
            "ProcessVideo": {
                "Type": "Task",
                "Resource": arns[1],
                "Retry": [{
                    "ErrorEquals": ["States.ALL"],
                    "IntervalSeconds": 5,
                    "MaxAttempts": 3,
                    "BackoffRate": 2.0,
                }],
                "Catch": [{
                    "ErrorEquals": ["States.ALL"],
                    "Next": "MarkFailed",
                    "ResultPath": "$.error_info",
                }],
                "Next": "MarkDone",
            },
            "MarkDone": {
                "Type": "Task",
                "Resource": arns[2],
                "Parameters": {
                    "clip_id.$": "$.clip_id",
                    "s3_key.$": "$.s3_key",
                    "start_sec.$": "$.start_sec",
                    "end_sec.$": "$.end_sec",
                    "output_key.$": "$.output_key",
                    "status": "done",
                },
                "End": True,
            },
            "MarkFailed": {
                "Type": "Task",
                "Resource": arns[2],
                "Parameters": {
                    "clip_id.$": "$.clip_id",
                    "s3_key.$": "$.s3_key",
                    "start_sec.$": "$.start_sec",
                    "end_sec.$": "$.end_sec",
                    "status": "failed",
                    "error.$": "States.JsonToString($.error_info)",
                },
                "End": True,
            },
        },
    }))

    return aws.sfn.StateMachine(
        name,
        role_arn=sfn_role.arn,
        definition=definition,
    )