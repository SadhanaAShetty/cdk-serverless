from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_sns as sns,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct



class HomeSwapStack(Stack):
    """Simple CDK Stack for Holiday Home Swap Application"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 Bucket for home images
        self.images_bucket = s3.Bucket(
            self, "HomeImagesBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # SNS Topic for notifications
        self.notification_topic = sns.Topic(
            self, "HomeSwapNotifications",
            topic_name="home-swap-matches"
        )

        
        
        CfnOutput(
            self, "BucketName",
            value=self.images_bucket.bucket_name,
            description="S3 bucket name for home images"
        )
        
        CfnOutput(
            self, "TopicArn",
            value=self.notification_topic.topic_arn,
            description="SNS topic ARN for notifications"
        )