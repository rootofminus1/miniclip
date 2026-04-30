from typing import Optional, TypedDict, List
import pulumi
import pulumi_aws as aws


class RouteConfig(TypedDict):
    method: str
    path: str
    lambda_fn: aws.lambda_.Function
    caching_ttl: Optional[int]


def make_api(
    name: str,
    routes: List[RouteConfig],
    validate_user_fn: Optional[aws.lambda_.Function] = None,
) -> aws.apigatewayv2.Api:

    api = aws.apigatewayv2.Api(
        name,
        protocol_type="HTTP",
        cors_configuration=aws.apigatewayv2.ApiCorsConfigurationArgs(
            allow_origins=["*"],
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["content-type", "x-user-id"],
            max_age=3000,
        ),
    )

    log_group = aws.cloudwatch.LogGroup(f"{name}-api-logs")

    api_gw_logs_role = aws.iam.Role(
        f"{name}-apigw-cw-role",
        assume_role_policy="""{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "apigateway.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }"""
    )

    aws.iam.RolePolicyAttachment(
        f"{name}-apigw-cw-attach",
        role=api_gw_logs_role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs",
    )

    apigw_account = aws.apigateway.Account(
        f"{name}-apigw-account",
        cloudwatch_role_arn=api_gw_logs_role.arn,
    )

    stage_info = [
        ("dev", 50, 25),
        ("prod", 20, 10),
    ]

    for stage_name, burst, rate in stage_info:
        aws.apigatewayv2.Stage(
            f"{name}-{stage_name}",
            api_id=api.id,
            name=stage_name,
            auto_deploy=True,
            default_route_settings=aws.apigatewayv2.StageDefaultRouteSettingsArgs(
                throttling_burst_limit=burst,
                throttling_rate_limit=rate,
            ),
            access_log_settings=aws.apigatewayv2.StageAccessLogSettingsArgs(
                destination_arn=log_group.arn,
                format='{"requestId":"$context.requestId","status":"$context.status"}',
            ),
            opts=pulumi.ResourceOptions(depends_on=[apigw_account]),
        )


    authorizer = None

    if validate_user_fn:
        authorizer = aws.apigatewayv2.Authorizer(
            f"{name}-user-authorizer",
            api_id=api.id,
            authorizer_type="REQUEST",
            authorizer_uri=validate_user_fn.invoke_arn,
            identity_sources=["$request.header.x-user-id"],
            name="validate-user",
            authorizer_payload_format_version="2.0",
            enable_simple_responses=True,
            authorizer_result_ttl_in_seconds=0,
        )

        aws.lambda_.Permission(
            f"{name}-user-auth-perm",
            action="lambda:InvokeFunction",
            function=validate_user_fn.name,
            principal="apigateway.amazonaws.com",
            source_arn=api.execution_arn.apply(lambda arn: f"{arn}/*/*"),
        )

    for route in routes:
        method = route["method"]
        path = route["path"]
        lambda_fn = route["lambda_fn"]

        safe_path = path.replace("/", "-").replace("{", "").replace("}", "").strip("-")
        base_name = f"{name}-{method.lower()}-{safe_path}"

        integration = aws.apigatewayv2.Integration(
            f"{base_name}-integration",
            api_id=api.id,
            integration_type="AWS_PROXY",
            integration_uri=lambda_fn.invoke_arn,
            payload_format_version="2.0",
        )

        aws.apigatewayv2.Route(
            f"{base_name}-route",
            api_id=api.id,
            route_key=f"{method} {path}",
            target=integration.id.apply(lambda id: f"integrations/{id}"),
            authorizer_id=authorizer.id if authorizer else None,
            authorization_type="CUSTOM" if authorizer else "NONE",
        )

        aws.lambda_.Permission(
            f"{base_name}-permission",
            action="lambda:InvokeFunction",
            function=lambda_fn.name,
            principal="apigateway.amazonaws.com",
            source_arn=api.execution_arn.apply(lambda arn: f"{arn}/*/*"),
        )

    return api