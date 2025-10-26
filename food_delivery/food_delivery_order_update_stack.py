from aws_cdk import (
    Stack,Duration,
    CfnParameter,
    CfnOutput,
    aws_events as events,
    aws_lambda as lmbda,
    aws_events_targets as targets
)
from constructs import Construct

class FoodDeliveryOrderUpdate(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Parameters
        orders_table = CfnParameter(
            self, "UserOrdersTable",
            type="String",
            description="OrdersTable name for Orders module"
        )

        user_pool = CfnParameter(
            self, "UserPool",
            type="String",
            description="User Pool Id from users module"
        )

        stage = CfnParameter(
            self, "Stage",
            type="String",
            default="dev"
        )

        # EventBridge Bus
        restaurant_bus = events.EventBus(
            self, "RestaurantBus",
            event_bus_name=f"Orders-{stage.value_as_string}"
        )

        powertools_layer = lmbda.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79"
        )

        # List User Favorites Lambda
        update_lambda = lmbda.Function(
            self, "ListUserFavoritesLambda",
            function_name="update_order",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="update_order.lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/update_assets"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": orders_table.table_name
            },
            timeout=Duration.seconds(10)
        )
        orders_table.grant_read_write_data(update_lambda)

        rule = events.Rule(
            self, "OrderUpdateRule",
            event_bus=restaurant_bus,
            event_pattern=events.EventPattern(
                source=["restaurant"],
                detail_type=["order.updated"]
            )
        )

        rule.add_target(targets.LambdaFunction(self.update_order))
        

        

        # Outputs
        CfnOutput(
            self, "RestaurantBusName",
            description="Name of Restaurant EventBridge Bus",
            value=restaurant_bus.event_bus_name
        )

        CfnOutput(
            self, "OrdersTablenameOutput",
            value=orders_table.value_as_string
        )

        CfnOutput(
            self, "UserPoolOutput",
            value=user_pool.value_as_string
        )

