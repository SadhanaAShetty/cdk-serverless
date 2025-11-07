from aws_cdk import RemovalPolicy
from aws_cdk.aws_dynamodb import TableV2, AttributeType
from constructs import Construct

class DynamoTable(TableV2):
    """
    A reusable CDK construct for creating a DynamoDB table with an optional sort key.

    Defaults:
    - Billing mode: PAY_PER_REQUEST
    - Removal policy: DESTROY
    - Partition key required, sort key optional

    Inherits from TableV2
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        table_name: str,
        partition_key: str,
        partition_key_type: AttributeType = AttributeType.STRING,
        sort_key: str = None,
        sort_key_type: AttributeType = AttributeType.STRING,
        removal_policy: RemovalPolicy = RemovalPolicy.DESTROY,
        billing_mode=None, 
        **kwargs,
    ):
        partition_attr = {"name": partition_key, "type": partition_key_type}
        sort_attr = {"name": sort_key, "type": sort_key_type} if sort_key else None

        super().__init__(
            scope,
            id,
            table_name=table_name,
            partition_key=partition_attr,
            sort_key=sort_attr,
            billing_mode=billing_mode,
            removal_policy=removal_policy,
            **kwargs
        )
