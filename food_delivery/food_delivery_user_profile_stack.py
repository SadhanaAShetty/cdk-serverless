from aws_cdk import (
    Stack, Duration, RemovalPolicy, CfnOutput,
    aws_cognito as cognito,
    aws_apigateway as apigw,
    aws_lambda as lmbda,
    aws_dynamodb as dynamodb,
    aws_logs as logs,
    aws_sns as sns,
    aws_iam as iam,
    aws_ssm as ssm,
    aws_sns_subscriptions as sns_subscriptions,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_events as events,
    aws_events_targets as targets
)
from constructs import Construct


class FoodDeliveryStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #dynamoDB Table
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

        bus = events.EventBus.from_event_bus_name(self, "EventBus", "default")

        powertools_layer = lmbda.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79",
        )

        #add_user_address
        add_user_address = lmbda.Function(
                self, "CreateOrderFunction",
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
        address_table.grant_read_write_data(add_user_address)

        rule = events.Rule(
            self,
            "AddUserAddressRule",
            event_bus=bus,
            event_pattern=events.EventPattern(
                source=["customer-profile"],
                detail_type=["address.added"],
            ),
            
        )

        
        rule.add_target(targets.LambdaFunction(add_user_address))

        #update_user_address
        update_user_address = lmbda.Function(
                self, "UpdateUserAddressFunction",
                function_name="update_address",
                runtime=lmbda.Runtime.PYTHON_3_12,
                handler="update_address.lambda_handler",
                code=lmbda.Code.from_asset("assets"),
                layers=[powertools_layer],
                environment={
                    "TABLE_NAME": address_table.table_name
                },
                timeout=Duration.seconds(10)
            )
        address_table.grant_read_write_data(update_user_address)

        update_rule = events.Rule(
            self,
            "UpdateUserAddressRule",
            event_bus=bus,
            event_pattern=events.EventPattern(
                source=["customer-profile"],
                detail_type=["address.added"],
            ),
            
        )

        
        update_rule.add_target(targets.LambdaFunction(update_user_address))


        #delete_user_address
        delete_user_address = lmbda.Function(
                self, "DeleteUserAddressFunction",
                function_name="delete_address",
                runtime=lmbda.Runtime.PYTHON_3_12,
                handler="delete_address.lambda_handler",
                code=lmbda.Code.from_asset("assets"),
                layers=[powertools_layer],
                environment={
                    "TABLE_NAME": address_table.table_name
                },
                timeout=Duration.seconds(10)
            )
        address_table.grant_read_write_data(delete_user_address)

        delete_rule = events.Rule(
            self,
            "DeleteUserAddressRule",
            event_bus=bus,
            event_pattern=events.EventPattern(
                source=["customer-profile"],
                detail_type=["address.added"],
            ),
            
        )

        
        delete_rule.add_target(targets.LambdaFunction(delete_user_address))


        #api

       