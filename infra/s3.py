import pulumi_aws as aws


def make_bucket(name: str, notify_queue_arn=None) -> aws.s3.Bucket:
    bucket = aws.s3.Bucket(
        name,
        force_destroy=True,
    )

    aws.s3.BucketPublicAccessBlock(
        f"{name}-block",
        bucket=bucket.id,
        block_public_acls=True,
        block_public_policy=True,
        ignore_public_acls=True,
        restrict_public_buckets=True,
    )

    aws.s3.BucketCorsConfiguration(
        f"{name}-cors",
        bucket=bucket.id,
        cors_rules=[aws.s3.BucketCorsConfigurationCorsRuleArgs(
            allowed_origins=["*"],
            allowed_methods=["POST", "GET", "HEAD", "PUT"],
            allowed_headers=["*"],
            expose_headers=["ETag"],
            max_age_seconds=3000,
        )],
    )

    aws.s3.BucketLifecycleConfiguration(
        f"{name}-lifecycle",
        bucket=bucket.id,
        rules=[aws.s3.BucketLifecycleConfigurationRuleArgs(
            id="expire-old-uploads",
            status="Enabled",
            expiration=aws.s3.BucketLifecycleConfigurationRuleExpirationArgs(
                days=30,
            ),
        )],
    )

    if notify_queue_arn:
        aws.s3.BucketNotification(
            f"{name}-notifications",
            bucket=bucket.id,
            queues=[aws.s3.BucketNotificationQueueArgs(
                queue_arn=notify_queue_arn,
                events=["s3:ObjectCreated:*"],
                filter_suffix=".mp4",
            )],
        )

    return bucket