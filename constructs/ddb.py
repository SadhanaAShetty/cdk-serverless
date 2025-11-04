from aws_cdk import (
    RemovalPolicy,
    aws_dynamodb as dynamodb,
)
from constructs import Construct


class DynamoTable(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        table_name: str,
        partition_key: str,
        sort_key: str = None,
        removal_policy: RemovalPolicy = RemovalPolicy.DESTROY,
        billing_mode: dynamodb.BillingMode = dynamodb.BillingMode.PAY_PER_REQUEST,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        self.table = dynamodb.Table(
            self,
            "Table",
            table_name=table_name,
            partition_key=dynamodb.Attribute(
                name=partition_key,
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name=sort_key,
                type=dynamodb.AttributeType.STRING
            ) if sort_key else None,
            billing_mode=billing_mode,
            removal_policy=removal_policy,
        )

        self.table_name = self.table.table_name

    def grant_read_write_data(self, grantee):
        return self.table.grant_read_write_data(grantee)

    def grant_read_data(self, grantee):
        return self.table.grant_read_data(grantee)
