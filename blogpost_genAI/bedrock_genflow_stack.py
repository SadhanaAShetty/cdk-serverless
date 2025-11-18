from aws_cdk import (
    Stack, Duration, RemovalPolicy, CfnOutput,
    aws_apigateway as apigw,
    aws_lambda as lmbda,
    aws_logs as logs,
    aws_cloudwatch as cloudwatch,
    aws_bedrock as bedrock
)
from constructs import Construct
from constructs.bucket import S3BucketConstruct
from constructs.lmbda_construct import Lambda


class BlogPostGenAI(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.static_site_bucket = S3BucketConstruct(
            self,
            "BlogBucket",
            bucket_name="blog-bucket-genai"
        ).bucket


       

        #Lambda 
        blog_lambda = Lambda(
            self, "BlogFunction",
            function_name="blog_post",
            handler="blog_post.lambda_handler",
            code_path="blogpost_genAI/assets",
            env={
                "STATIC_BUCKET_NAME": self.static_site_bucket.bucket_name
            },
        )
        create_lambda = blog_lambda.lambda_fn
        self.static_site_bucket.grant_read_write(create_lambda)

        #bedrock
        bedrock.FoundationModel.from_foundation_model_id(
            self, "Model", 
            bedrock.FoundationModelIdentifier.ANTHROPIC_CLAUDE_V2
            )
        

        #api
        api = apigw.RestApi(
            self, "BlogPostGenAI", rest_api_name="BlogPostGenAI", deploy=False
        )

        task_resource = api.root.add_resource("create_blog")
        post_method = task_resource.add_method(
            "POST", apigw.LambdaIntegration(), api_key_required=True
        )

        log_group = logs.LogGroup(self, "DevLogs", retention=logs.RetentionDays.ONE_DAY)

        deployment = apigw.Deployment(self, "Deployment", api=api)

        stage = apigw.Stage(
            self,
            "DevStage",
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
                user=True,
            ),
        )

        api.deployment_stage = stage

        # API Key & Usage Plan
        key = api.add_api_key("ApiKey")

        plan = api.add_usage_plan(
            "UsagePlan",
            name="Easy",
            throttle=apigw.ThrottleSettings(rate_limit=10, burst_limit=2),
        )

        plan.add_api_key(key)

        plan.add_api_stage(
            stage=stage,
            throttle=[
                apigw.ThrottlingPerMethod(
                    method=post_method,
                    throttle=apigw.ThrottleSettings(rate_limit=10, burst_limit=2),
                )
            ],
        )


   

