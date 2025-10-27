from aws_cdk import (
    Stack, Duration,
    CfnOutput, Fn,
    aws_events as events,
    aws_lambda as lmbda,
    aws_events_targets as targets,
    aws_dynamodb as dynamodb
)
from constructs import Construct

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

        update_lambda = lmbda.Function(
            self, "UpdateOrderLambda",
            function_name="update_order",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="update_order.lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/update_assets"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": orders_table_name
            },
            timeout=Duration.seconds(10)
        )

  
        orders_ddb_table.grant_read_write_data(update_lambda)

        rule = events.Rule(
            self, "OrderUpdateRule",
            event_bus=restaurant_bus,
            event_pattern=events.EventPattern(
                source=["restaurant"],
                detail_type=["order.updated"]
            )
        )

        rule.add_target(targets.LambdaFunction(update_lambda))

        CfnOutput(self, "RestaurantBusName", value=restaurant_bus.event_bus_name)
        CfnOutput(self, "OrdersTablenameOutput", value=orders_table_name)
