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
        
        
        create_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/meta.llama3-2-1b-instruct-v1:0*"
                ]
            )
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

        # Add resource and method (no API key for testing)
        task_resource = api_gateway.api.root.add_resource("create_blog")
        post_method = api_gateway.add_method_with_auth_suppression(
            resource=task_resource,
            method="POST",
            integration=apigw.LambdaIntegration(create_lambda),
            api_key_required=False,
            suppress_cognito_warning=True
        )
        
        # Additional suppression for no auth (testing only)
        NagSuppressions.add_resource_suppressions(
            post_method,
            suppressions=[
                {
                    "id": "AwsSolutions-APIG4",
                    "reason": "No authorization for testing purposes. This is a personal project for Postman testing."
                }
            ]
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
        CfnOutput(
            self, "ApiUrl", 
            value=f"{api_gateway.api.url}create_blog",
            description="API Gateway endpoint for blog generation (no API key required for testing)"
        )
        CfnOutput(
            self, "BucketName", 
            value=self.static_site_bucket.bucket_name,
            description="S3 bucket where generated blogs are stored"
        )
