from aws_cdk import (
    Stack, Duration, RemovalPolicy,
    aws_apigateway as apigw,
    aws_lambda as lmbda,
    aws_dynamodb as dynamodb,
    aws_logs as logs,
    aws_cognito as cognito,
    aws_events as events,
    aws_events_targets as targets
)
from constructs import Construct

class AddressStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # DynamoDB Table
        address_table = dynamodb.Table(
            self, "AddressTable",
            table_name="AddressTable",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="address_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Cognito user pool (imported)
        user_pool = cognito.UserPool.from_user_pool_id(
            self, "ImportedUserPool",
            user_pool_id="your-user-pool-id"
        )

        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self, "AddressApiAuthorizer",
            cognito_user_pools=[user_pool]
        )

        # Lambda Powertools layer
        powertools_layer = lmbda.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79",
        )

        # EventBridge Bus
        address_bus = events.EventBus(
            self, "AddressBus",
            event_bus_name=f"Address-{self.stack_name}"
        )

        # Add Address Lambda
        add_address_lambda = lmbda.Function(
            self, "AddAddressLambda",
            function_name="add_address",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="add_address.lambda_handler",
            code=lmbda.Code.from_asset("assets"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": address_table.table_name
            },
            timeout=Duration.seconds(10)
        )
        address_table.grant_read_write_data(add_address_lambda)

        # Edit Address Lambda
        edit_address_lambda = lmbda.Function(
            self, "EditAddressLambda",
            function_name="edit_address",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="edit_user_address.lambda_handler",
            code=lmbda.Code.from_asset("assets"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": address_table.table_name,
                "POWERTOOLS_SERVICE_NAME": "serverless-workshop"
            },
            timeout=Duration.seconds(10)
        )
        address_table.grant_read_write_data(edit_address_lambda)

        # Delete Address Lambda
        delete_address_lambda = lmbda.Function(
            self, "DeleteAddressLambda",
            function_name="delete_address",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="delete_user_address.lambda_handler",
            code=lmbda.Code.from_asset("assets"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": address_table.table_name,
                "POWERTOOLS_SERVICE_NAME": "serverless-workshop"
            },
            timeout=Duration.seconds(10)
        )
        address_table.grant_read_write_data(delete_address_lambda)

        # EventBridge rules
        add_rule = events.Rule(
            self, "AddUserAddressRule",
            event_bus=address_bus,
            event_pattern=events.EventPattern(
                source=["customer-profile"],
                detail_type=["address.added"]
            )
        )
        add_rule.add_target(targets.LambdaFunction(add_address_lambda))

        edit_rule = events.Rule(
            self, "EditUserAddressRule",
            event_bus=address_bus,
            event_pattern=events.EventPattern(
                source=["customer-profile"],
                detail_type=["address.updated"]
            )
        )
        edit_rule.add_target(targets.LambdaFunction(edit_address_lambda))

        delete_rule = events.Rule(
            self, "DeleteUserAddressRule",
            event_bus=address_bus,
            event_pattern=events.EventPattern(
                source=["customer-profile"],
                detail_type=["address.deleted"]
            )
        )
        delete_rule.add_target(targets.LambdaFunction(delete_address_lambda))
