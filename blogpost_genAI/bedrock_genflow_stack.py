from aws_cdk import (
    Stack, CfnOutput,
    aws_apigateway as apigw,
    aws_iam as iam,
    aws_bedrock as bedrock
)
from constructs import Construct
from constructs.bucket import S3BucketConstruct
from constructs.lmbda_construct import Lambda
from constructs.api_gateway_construct import ApiGatewayConstruct
from cdk_nag import NagSuppressions



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
            handler="bedrock_handler.lambda_handler",
            code_path="blogpost_genAI/assets",
            env={
                "STATIC_BUCKET_NAME": self.static_site_bucket.bucket_name
            },
        )
        create_lambda = blog_lambda.lambda_fn
        self.static_site_bucket.grant_read_write(create_lambda)
        
        # Grant Bedrock permissions to Lambda
        create_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/meta.llama3-2-1b-instruct-v1:0"
                ]
            )
        )

        # Bedrock Llama 3.2 model reference
        bedrock.FoundationModel.from_foundation_model_id(
            self, "Model", 
            bedrock.FoundationModelIdentifier.META_LLAMA_3_2_1B_INSTRUCT_V1_0
        )
        
        # API Gateway with construct
        api_gateway = ApiGatewayConstruct(
            self,
            "BlogApi",
            api_name="BlogPostGenAI",
            description="API for AI-powered blog post generation",
            throttling_rate_limit=10,
            throttling_burst_limit=2
        )

        # Add resource and method
        task_resource = api_gateway.api.root.add_resource("create_blog")
        post_method = api_gateway.add_method_with_auth_suppression(
            resource=task_resource,
            method="POST",
            integration=apigw.LambdaIntegration(create_lambda),
            api_key_required=True
        )

        # API Key & Usage Plan
        key = api_gateway.api.add_api_key("ApiKey")

        plan = api_gateway.api.add_usage_plan(
            "UsagePlan",
            name="Easy",
            throttle=apigw.ThrottleSettings(rate_limit=10, burst_limit=2),
        )

        plan.add_api_key(key)
        plan.add_api_stage(
            stage=api_gateway.stage,
            throttle=[
                apigw.ThrottlingPerMethod(
                    method=post_method,
                    throttle=apigw.ThrottleSettings(rate_limit=10, burst_limit=2),
                )
            ],
        )


   


        # CDK-nag Suppressions for S3 Bucket
        NagSuppressions.add_resource_suppressions(
            self.static_site_bucket,
            suppressions=[
                {
                    "id": "AwsSolutions-S1",
                    "reason": (
                        "S3 access logs are not required for this personal blog storage bucket. "
                        "The bucket only stores generated blog posts and doesn't need audit logging."
                    )
                }
            ]
        )

        # CDK-nag Suppressions for Lambda IAM Role
        if create_lambda.role:
            NagSuppressions.add_resource_suppressions(
                create_lambda.role,
                suppressions=[
                    {
                        "id": "AwsSolutions-IAM5",
                        "reason": (
                            "Wildcard S3 permissions are CDK-generated for read/write access "
                            "to the blog bucket only."
                        )
                    }
                ],
                apply_to_children=True
            )

        # Outputs
        CfnOutput(self, "ApiUrl", value=api_gateway.api.url, description="API Gateway URL")
        CfnOutput(self, "ApiKeyId", value=key.key_id, description="API Key ID")
        CfnOutput(self, "BucketName", value=self.static_site_bucket.bucket_name, description="Blog Storage Bucket")
