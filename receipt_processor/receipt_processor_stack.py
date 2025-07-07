from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_lambda as lmbda,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_iam as iam,
    aws_logs as logs
)
from constructs import Construct


class ReceiptProcessorStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        
        upload_bucket = s3.Bucket(
            self, "UploadBucket",
            removal_policy=RemovalPolicy.DESTROY
        )

        parsed_bucket = s3.Bucket(
            self, "ParsedBucket",
            removal_policy=RemovalPolicy.DESTROY
        )

       
        powertools_layer = lmbda.LayerVersion.from_layer_version_arn(
            self, "PowertoolsLayer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79"
        )

    
        process_lambda = lmbda.Function(
            self, "ReceiptProcessor",
            function_name="receipt_processor",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="receipt_processor.lambda_handler",
            code=lmbda.Code.from_asset("receipt_processor/assets/functions"),
            layers=[powertools_layer],
            environment={
                "UPLOAD_BUCKET": upload_bucket.bucket_name,
                "PARSED_BUCKET": parsed_bucket.bucket_name
            },
            timeout=Duration.seconds(60)
        )

        
        upload_bucket.grant_read_write(process_lambda)
        parsed_bucket.grant_read_write(process_lambda)

       
        process_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "comprehend:DetectEntities",
                    "comprehend:DetectSentiment",
                    "comprehend:DetectSyntax"
                ],
                resources=["*"]
            )
        )

        process_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "textract:AnalyzeDocument",
                    "textract:DetectDocumentText"
                ],
                resources=["*"]
            )
        )

        process_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                resources=["arn:aws:logs:*:*:log-group:/aws/lambda/*"]
            )
        )

        
        upload_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(process_lambda)
        )

       
