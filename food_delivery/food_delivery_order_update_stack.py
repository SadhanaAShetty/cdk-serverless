from aws_cdk import (
    Stack, Duration,
    CfnOutput, Fn,
    aws_events as events,
    aws_lambda as lmbda,
    aws_events_targets as targets,
    aws_dynamodb as dynamodb,
    aws_sqs as sqs
)
from constructs import Construct
from cdk_nag import NagSuppressions
from constructs.ddb import DynamoTable
from constructs.lmbda_construct import LambdaConstruct

class FoodDeliveryOrderUpdate(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

    
        orders_table_name = "UserOrdersTable" 
        stage = "dev"

        # Import the DynamoDB table from the main stack
        orders_ddb_table = dynamodb.Table.from_table_name(
            self, "ImportedOrdersTable",
            table_name=orders_table_name
        )

        restaurant_bus = events.EventBus(
            self, "RestaurantBus",
            event_bus_name=f"Orders-{stage}"
        )

        powertools_layer = lmbda.LayerVersion.from_layer_version_arn(
            self, "PowertoolsLayer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79"
        )

        update_lambda_construct = LambdaConstruct(
            self, "UpdateOrderLambda",
            function_name="update_order",
            handler="update_order.lambda_handler",
            code_path="food_delivery/update_assets",
            layers=[powertools_layer],
            env={
                "TABLE_NAME": orders_table_name
            }
        )
        update_lambda = update_lambda_construct.lambda_fn

        #Nag Suppression
        NagSuppressions.add_resource_suppressions(
            update_lambda.role,
            suppressions=[{
                "id": "AwsSolutions-IAM4",
                "reason": "Lambda uses AWSLambdaBasicExecutionRole, which only grants CloudWatch Logs access and is equivalent to a minimal custom policy."
            }]
        )


  
        orders_ddb_table.grant_read_write_data(update_lambda)

        # DLQ for EventBridge target failures
        eventbridge_dlq = sqs.Queue(
            self, "OrderUpdateEventDLQ",
            queue_name="order-update-event-dlq",
            retention_period=Duration.days(14),
            enforce_ssl=True
        )

        # Suppress DLQ warnings for this queue since it IS a DLQ
        NagSuppressions.add_resource_suppressions(
            eventbridge_dlq,
            suppressions=[
                {
                    "id": "AwsSolutions-SQS3",
                    "reason": "This queue IS a dead letter queue for EventBridge target failures. It doesn't need its own DLQ."
                },
                {
                    "id": "Serverless-SQSRedrivePolicy",
                    "reason": "This is a DLQ itself. Adding another DLQ would create unnecessary complexity."
                }
            ]
        )

        rule = events.Rule(
            self, "OrderUpdateRule",
            event_bus=restaurant_bus,
            event_pattern=events.EventPattern(
                source=["restaurant"],
                detail_type=["order.updated"]
            )
        )

        rule.add_target(
            targets.LambdaFunction(
                update_lambda,
                dead_letter_queue=eventbridge_dlq
            )
        )

        CfnOutput(self, "RestaurantBusName", value=restaurant_bus.event_bus_name)
        CfnOutput(self, "OrdersTablenameOutput", value=orders_table_name)
