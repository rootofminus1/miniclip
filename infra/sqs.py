import json
import pulumi_aws as aws


def make_queue(name: str) -> aws.sqs.Queue:
    queue = aws.sqs.Queue(
        name,
        visibility_timeout_seconds=300,
    )

    aws.sqs.QueuePolicy(
        f"{name}-policy",
        queue_url=queue.id,
        policy=queue.arn.apply(lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "s3.amazonaws.com"},
                "Action": "sqs:SendMessage",
                "Resource": arn,
            }]
        }))
    )

    return queue