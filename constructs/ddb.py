from aws_cdk import (
    RemovalPolicy,
    aws_dynamodb as dynamodb,
)
from constructs import Construct


class DynamoTable(dynamodb.TableV2):
    """
    Reusable DynamoDB TableV2 construct with optional sort key and flexible key types.

    Features:
    - On-demand billing (PAY_PER_REQUEST)
    - Configurable removal policy (default: DESTROY)
    - Partition and sort key types can be STRING, NUMBER, or BINARY
    - Can be used directly in stacks without extra configuration
    """
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        table_name: str,
        partition_key: str,
        partition_key_type: dynamodb.AttributeType = dynamodb.AttributeType.STRING,
        sort_key: str = None,
        sort_key_type: dynamodb.AttributeType = dynamodb.AttributeType.STRING,
        removal_policy: RemovalPolicy = RemovalPolicy.DESTROY,
        **kwargs,
    ):
        partition_key_attr = dynamodb.Attribute(
            name=partition_key,
            type=partition_key_type
        )

        sort_key_attr = None
        if sort_key:
            sort_key_attr = dynamodb.Attribute(
                name=sort_key,
                type=sort_key_type
            )

        super().__init__(
            scope,
            id,
            table_name=table_name,
            partition_key=partition_key_attr,
            sort_key=sort_key_attr,
            billing=dynamodb.Billing.on_demand(),
            removal_policy=removal_policy,
            **kwargs
        )
