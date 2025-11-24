from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_apigateway as apigw,
    aws_logs as logs,
)
from constructs import Construct
from cdk_nag import NagSuppressions


class ApiGatewayConstruct(Construct):
    """
    A reusable API Gateway construct with sensible defaults and CDK-nag suppressions.
    
    Defaults:
    - CloudWatch logging enabled
    - Throttling configured (1000 req/s, 2000 burst)
    - Metrics and data tracing enabled
    - Common CDK-nag suppressions applied
    - 1-day log retention
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        api_name: str,
        description: str = None,
        throttling_rate_limit: int = 1000,
        throttling_burst_limit: int = 2000,
        log_retention: logs.RetentionDays = logs.RetentionDays.ONE_DAY,
        **kwargs,
    ):
        super().__init__(scope, id)

        # Create API Gateway
        self.api = apigw.RestApi(
            self,
            "Api",
            rest_api_name=api_name,
            description=description or f"{api_name} REST API",
            deploy=False
        )

        # CloudWatch Log Group
        self.log_group = logs.LogGroup(
            self,
            "ApiLogs",
            log_group_name=f"apigw/{api_name}Logs",
            retention=log_retention,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create deployment
        self.deployment = apigw.Deployment(
            self,
            "Deployment",
            api=self.api
        )

        # Create stage with logging and throttling
        self.stage = apigw.Stage(
            self,
            "Stage",
            deployment=self.deployment,
            stage_name="dev",
            access_log_destination=apigw.LogGroupLogDestination(self.log_group),
            access_log_format=apigw.AccessLogFormat.json_with_standard_fields(
                caller=False,
                http_method=True,
                ip=True,
                protocol=True,
                request_time=True,
                resource_path=True,
                response_length=True,
                status=True,
                user=True,
            ),
            logging_level=apigw.MethodLoggingLevel.INFO,
            data_trace_enabled=True,
            metrics_enabled=True,
            throttling_rate_limit=throttling_rate_limit,
            throttling_burst_limit=throttling_burst_limit
        )

        self.api.deployment_stage = self.stage

        # CDK-nag Suppressions for API Gateway
        NagSuppressions.add_resource_suppressions(
            self.api,
            suppressions=[
                {
                    "id": "AwsSolutions-APIG2",
                    "reason": (
                        "Request validation is handled in Lambda functions. "
                        "API Gateway request validation is redundant for this use case."
                    )
                },
                {
                    "id": "CdkNagValidationFailure",
                    "reason": "Known CDK-nag limitation with intrinsic functions in API Gateway logging configuration."
                }
            ]
        )

        # CDK-nag Suppressions for API Gateway Stage
        NagSuppressions.add_resource_suppressions(
            self.stage,
            suppressions=[
                {
                    "id": "AwsSolutions-APIG3",
                    "reason": (
                        "WAF is not required for development/learning projects. "
                        "It adds significant cost without proportional benefit for the use case."
                    )
                },
                {
                    "id": "AwsSolutions-APIG1",
                    "reason": "Access logging is already enabled via CloudWatch Logs."
                },
                {
                    "id": "Serverless-APIGWXrayEnabled",
                    "reason": (
                        "X-Ray tracing is disabled to reduce costs. "
                        "CloudWatch Logs and metrics provide sufficient observability."
                    )
                }
            ]
        )

    def add_method_with_auth_suppression(
        self,
        resource: apigw.Resource,
        method: str,
        integration: apigw.Integration,
        authorization_type: apigw.AuthorizationType = apigw.AuthorizationType.NONE,
        authorizer: apigw.IAuthorizer = None,
        api_key_required: bool = False,
        suppress_cognito_warning: bool = True,
        **kwargs
    ) -> apigw.Method:
        """
        Helper method to add API method with automatic CDK-nag suppressions.
        
        Args:
            resource: API Gateway resource
            method: HTTP method (GET, POST, etc.)
            integration: Lambda integration
            authorization_type: Authorization type
            authorizer: Custom authorizer if needed
            api_key_required: Whether API key is required
            suppress_cognito_warning: Suppress Cognito authorizer warning
        """
        api_method = resource.add_method(
            method,
            integration,
            authorization_type=authorization_type,
            authorizer=authorizer,
            api_key_required=api_key_required,
            **kwargs
        )

        # Suppress common authorization warnings
        suppressions = []
        
        if api_key_required and authorization_type == apigw.AuthorizationType.NONE:
            suppressions.append({
                "id": "AwsSolutions-APIG4",
                "reason": "API Key authorization is implemented via api_key_required=True."
            })
        
        if suppress_cognito_warning:
            suppressions.append({
                "id": "AwsSolutions-COG4",
                "reason": (
                    "Custom authorization (API Key or Lambda authorizer) is sufficient for this use case. "
                    "Cognito adds unnecessary complexity."
                )
            })

        if suppressions:
            NagSuppressions.add_resource_suppressions(
                api_method,
                suppressions=suppressions
            )

        return api_method
