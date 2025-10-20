from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    aws_sqs as sqs,
    aws_dynamodb as dynamodb,
    aws_lambda as lmbda,
    aws_iam as iam,
    aws_lambda_event_sources as lambda_event_sources,
)
from constructs import Construct


class FavoritesStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #DynamoDB Table
        favorites_table = dynamodb.Table(
            self, "FavoritesTable",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="restaurant_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        #SQS Queue - FavoriteRestaurantsQueue
        favorite_restaurants_queue = sqs.Queue(
            self, "FavoriteRestaurantsQueue",
            queue_name=f"FavoriteRestaurants-{self.stack_name}"
        )

        # IAM Role for API Gateway to send messages to SQS
        api_gateway_queue_command_role = iam.Role(
            self, "APIGatewayQueueCommandRole",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
            path="/",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonAPIGatewayPushToCloudWatchLogs"
                )
            ],
            inline_policies={
                "PolicySQS": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["sqs:SendMessage"],
                            resources=[favorite_restaurants_queue.queue_arn]
                        )
                    ]
                )
            }
        )

        # SQS Queue Policy - FavoriteRestaurantsQueuePolicySQS
        favorite_restaurants_queue.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.AccountPrincipal(self.account)],
                actions=["SQS:*"],
                resources=[favorite_restaurants_queue.queue_arn]
            )
        )

        favorite_restaurants_queue.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.ArnPrincipal(api_gateway_queue_command_role.role_arn)],
                actions=["SQS:SendMessage"],
                resources=[favorite_restaurants_queue.queue_arn]
            )
        )

        #Lambda Layer for Powertools 
        powertools_layer = lmbda.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79"
        )

        # Lambda Function - ListUserFavoritesFunction
        list_user_favorites_function = lmbda.Function(
            self, "ListUserFavoritesFunction",
            runtime=lmbda.Runtime.PYTHON_3_10,
            handler="list_user_favorites.lambda_handler",
            code=lmbda.Code.from_asset("address_assets/address/favorites"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": favorites_table.table_name,
                "POWERTOOLS_SERVICE_NAME": "serverless-workshop"
            }
        )

     
        favorites_table.grant_read_data(list_user_favorites_function)

        process_favorites_queue_function = lmbda.Function(
            self, "ProcessFavoriteRestaurantsQueueFunction",
            runtime=lmbda.Runtime.PYTHON_3_10,
            handler="process_favorites_queue.lambda_handler",
            code=lmbda.Code.from_asset("address_assets/address/favorites"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": favorites_table.table_name,
                "POWERTOOLS_SERVICE_NAME": "serverless-workshop"
            }
        )

       
        favorites_table.grant_read_write_data(process_favorites_queue_function)

        #Add SQS trigger to Lambda
        process_favorites_queue_function.add_event_source(
            lambda_event_sources.SqsEventSource(favorite_restaurants_queue)
        )

        # Outputs
        CfnOutput(
            self, "QueueUrl",
            value=favorite_restaurants_queue.queue_url,
            description="Favorite Restaurants Queue URL"
        )

        CfnOutput(
            self, "QueueArn",
            value=favorite_restaurants_queue.queue_arn,
            description="Favorite Restaurants Queue ARN"
        )

        CfnOutput(
            self, "TableName",
            value=favorites_table.table_name,
            description="Favorites DynamoDB Table Name"
        )

        CfnOutput(
            self, "ApiGatewayRoleArn",
            value=api_gateway_queue_command_role.role_arn,
            description="API Gateway SQS Role ARN",
            export_name="ApiGatewayQueueCommandRoleArn"
        )

        CfnOutput(
            self, "ListFavoritesLambdaArn",
            value=list_user_favorites_function.function_arn,
            description="List User Favorites Lambda ARN"
        )

        # Store references as properties for use in API Gateway integration
        self.queue = favorite_restaurants_queue
        self.api_gateway_role = api_gateway_queue_command_role
        self.list_favorites_function = list_user_favorites_function
        self.favorites_table = favorites_table