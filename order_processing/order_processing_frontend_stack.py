from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_lambda as lmbda,
    aws_dynamodb as ddb,
    aws_apigateway as apigw,
    aws_logs as logs,
    aws_sns as sns,
    aws_ssm as ssm
)
from constructs import Construct

class OrderProcessingFrontendStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # DynamoDB 
        dynamo = ddb.Table(
            self, "OrderTable",
            table_name="dynamo",
            partition_key=ddb.Attribute(
                name="order_id",
                type=ddb.AttributeType.STRING
            ),
            sort_key=ddb.Attribute(
                name="customer_id",
                type=ddb.AttributeType.STRING
            ),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # SNS Topic
        topic = sns.Topic(self, "OrderNotification")

        # Lambda Function
        order_processing = lmbda.Function(
            self, "OrderProcessing",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="order_processing.lambda_handler",
            code=lmbda.Code.from_asset("assets/functions"),
            environment={
                "TOPIC_ARN": topic.topic_arn
            }
        )

        # Grant permissions
        topic.grant_publish(order_processing)
        dynamo.grant_read_write_data(order_processing)

        # API
        api = apigw.RestApi(
            self, "OrderProcessingApi",
            rest_api_name="OrderProcessingApi",
            deploy=False
        )

        order_resource = api.root.add_resource("orders")
        post_method = order_resource.add_method(
            "POST",
            apigw.LambdaIntegration(order_processing),
            api_key_required=True
        )

        # Logging
        log_group = logs.LogGroup(
            self, "DevLogs",
            retention=logs.RetentionDays.ONE_DAY
        )

        # Stage
        deployment = apigw.Deployment(self, "Deployment", api=api)

        stage = apigw.Stage(
            self, "DevStage",
            deployment=deployment,
            stage_name="dev",
            access_log_destination=apigw.LogGroupLogDestination(log_group),
            access_log_format=apigw.AccessLogFormat.json_with_standard_fields(
                caller=False,
                http_method=True,
                ip=True,
                protocol=True,
                request_time=True,
                resource_path=True,
                response_length=True,
                status=True,
                user=True
            )
        )

        
        api.deployment_stage = stage

        # API Key & Usage Plan
        key = api.add_api_key("ApiKey")

        plan = api.add_usage_plan(
            "UsagePlan",
            name="Easy",
            throttle=apigw.ThrottleSettings(
                rate_limit=10,
                burst_limit=2
            )
        )

        plan.add_api_key(key)

        plan.add_api_stage(
            stage=stage,
            throttle=[
                apigw.ThrottlingPerMethod(
                    method=post_method,
                    throttle=apigw.ThrottleSettings(
                        rate_limit=10,
                        burst_limit=2
                    )
                )
            ]
        )

        # SSM Parameter
        ssm.StringParameter(
            self, "TopicArn",
            allowed_pattern=".*",
            description="SNS Topic ARN",
            parameter_name="/orderprocessing/backend/sns",
            string_value=topic.topic_arn,
            tier=ssm.ParameterTier.STANDARD
        )
