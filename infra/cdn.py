import pulumi_aws as aws
import pulumi

from roles import attach



def attach_bucket_policy(name: str, bucket: aws.s3.Bucket, cdn: aws.cloudfront.Distribution):
    identity = aws.get_caller_identity()

    policy = pulumi.Output.all(
        bucket.arn,
        cdn.id,
        identity.account_id,
    ).apply(lambda args: aws.iam.get_policy_document(statements=[{
        "effect": "Allow",
        "principals": [{
            "type": "Service",
            "identifiers": ["cloudfront.amazonaws.com"],
        }],
        "actions": ["s3:GetObject"],
        "resources": [f"{args[0]}/*"],
        "conditions": [{
            "test": "StringEquals",
            "variable": "AWS:SourceArn",
            "values": [f"arn:aws:cloudfront::{args[2]}:distribution/{args[1]}"],
        }],
    }]).json)

    return aws.s3.BucketPolicy(
        f"{bucket._name}-cloudfront-bucket-policy",
        bucket=bucket.id,
        policy=policy,
    )


def make_cdn(name: str, bucket: aws.s3.Bucket) -> aws.cloudfront.Distribution:

    oac = aws.cloudfront.OriginAccessControl(
        f"{name}-oac",
        origin_access_control_origin_type="s3",
        signing_behavior="always",
        signing_protocol="sigv4",
    )

    origin_id = f"{name}-s3-origin"

    cdn =  aws.cloudfront.Distribution(
        name,
        enabled=True,
        origins=[aws.cloudfront.DistributionOriginArgs(
            domain_name=bucket.bucket_regional_domain_name,
            origin_id=origin_id,
            origin_access_control_id=oac.id,
        )],
        default_cache_behavior=aws.cloudfront.DistributionDefaultCacheBehaviorArgs(
            target_origin_id=origin_id,
            viewer_protocol_policy="redirect-to-https",
            allowed_methods=["GET", "HEAD"],
            cached_methods=["GET", "HEAD"],
            cache_policy_id="658327ea-f89d-4fab-a63d-7e88639e58f6",  # Managed-CachingOptimized
            compress=True,
        ),
        restrictions=aws.cloudfront.DistributionRestrictionsArgs(
            geo_restriction=aws.cloudfront.DistributionRestrictionsGeoRestrictionArgs(
                restriction_type="none",
            ),
        ),
        viewer_certificate=aws.cloudfront.DistributionViewerCertificateArgs(
            cloudfront_default_certificate=True,
        ),
    )

    attach_bucket_policy(name, bucket, cdn)

    return cdn





def make_clips_cdn(name: str, bucket: aws.s3.Bucket) -> aws.cloudfront.Distribution:
    oac = aws.cloudfront.OriginAccessControl(
        f"{name}-oac",
        origin_access_control_origin_type="s3",
        signing_behavior="always",
        signing_protocol="sigv4",
    )

    origin_id = f"{name}-s3-origin"

    embed_function = aws.cloudfront.Function(
        f"{name}-embed-fn",
        runtime="cloudfront-js-2.0",
        comment="Serve OG embed HTML for bare clip URLs",
        publish=True,
        code=pulumi.Output.from_input(name).apply(lambda n: f"""
async function handler(event) {{
    var request = event.request;
    var uri = request.uri;

    if (uri.includes('.')) {{
        return request;
    }}

    var clipId = uri.replace(/^\\//, '');

    if (!clipId) {{
        return {{
            statusCode: 400,
            statusDescription: 'Bad Request',
            body: {{ encoding: 'text', data: 'Missing clip ID' }},
        }};
    }}

    var host = event.request.headers.host.value;

    var videoUrl = 'https://' + host + '/' + clipId + '.mp4';
    var thumbnailUrl = 'https://' + host + '/' + clipId + '.jpg';

    var createdAt = new Date().toISOString();

    var html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">

  <meta property="og:type" content="video.other">
  <meta property="og:url" content="https://${{host}}/${{clipId}}">
  <meta property="og:title" content="Clipped on ${{createdAt}} • Powered by Miniclip">
  <meta property="og:description" content="Clip ${{clipId}}">

  <meta property="og:video" content="${{videoUrl}}">
  <meta property="og:video:secure_url" content="${{videoUrl}}">
  <meta property="og:video:type" content="video/mp4">
  <meta property="og:video:width" content="1280">
  <meta property="og:video:height" content="720">

  <meta name="twitter:card" content="player">
  <meta name="twitter:title" content="Miniclip Clip">
  <meta name="twitter:description" content="Watch this clip">
  <meta name="twitter:player" content="${{videoUrl}}">
  <meta name="twitter:player:width" content="1280">
  <meta name="twitter:player:height" content="720">
</head>

<body style="margin:0;background:#000;display:flex;align-items:center;justify-content:center;height:100vh">
  <video controls autoplay muted playsinline style="max-width:100%;max-height:100vh">
    <source src="${{videoUrl}}" type="video/mp4">
  </video>
</body>
</html>`;

    return {{
        statusCode: 200,
        statusDescription: 'OK',
        headers: {{
            'content-type': {{ value: 'text/html' }},
            'cache-control': {{ value: 'public, max-age=60' }},
        }},
        body: {{ encoding: 'text', data: html }},
    }};
}}
"""),
    )

    cdn = aws.cloudfront.Distribution(
        name,
        enabled=True,
        origins=[aws.cloudfront.DistributionOriginArgs(
            domain_name=bucket.bucket_regional_domain_name,
            origin_id=origin_id,
            origin_access_control_id=oac.id,
        )],
        default_cache_behavior=aws.cloudfront.DistributionDefaultCacheBehaviorArgs(
            target_origin_id=origin_id,
            viewer_protocol_policy="redirect-to-https",
            allowed_methods=["GET", "HEAD"],
            cached_methods=["GET", "HEAD"],
            cache_policy_id="658327ea-f89d-4fab-a63d-7e88639e58f6",
            compress=True,
            function_associations=[
                aws.cloudfront.DistributionDefaultCacheBehaviorFunctionAssociationArgs(
                    event_type="viewer-request",
                    function_arn=embed_function.arn,
                )
            ],
        ),
        restrictions=aws.cloudfront.DistributionRestrictionsArgs(
            geo_restriction=aws.cloudfront.DistributionRestrictionsGeoRestrictionArgs(
                restriction_type="none",
            ),
        ),
        viewer_certificate=aws.cloudfront.DistributionViewerCertificateArgs(
            cloudfront_default_certificate=True,
        ),
    )

    attach_bucket_policy(name, bucket, cdn)

    return cdn

