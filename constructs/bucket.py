from constructs import Construct
from aws_cdk import (
    RemovalPolicy,
    aws_s3 as s3,
)

class S3BucketConstruct(Construct):
    """
    Creates a secure S3 bucket with public access fully blocked.

    - Public access block enabled
    - Versioning enabled
    - S3-managed encryption
    - SSL enforced
    """

    def __init__(self, scope: Construct, id: str, *, bucket_name: str) -> None:
        super().__init__(scope, id)

        self.bucket = s3.Bucket(
            self,
            "Bucket",
            bucket_name=bucket_name,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
