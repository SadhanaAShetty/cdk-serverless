from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    RemovalPolicy,
    aws_sqs as sqs,
    aws_dynamodb as dynamodb,
    aws_lambda as lmbda,
    aws_lambda_event_sources as lambda_event_sources,
    aws_apigateway as apigw,
    aws_logs as logs,
    aws_sns as sns,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
)
from constructs import Construct
from constructs.ddb import DynamoTable


class FavoritesStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #import authorizer Lambda from main stack
        authorizer_lambda = lmbda.Function.from_function_name(
            self, "ImportedAuthorizerLambda",
            function_name="AuthorizerLambda"  
        )

        authorizer = apigw.TokenAuthorizer(
            self, "FavoritesAuthorizer",
            handler=authorizer_lambda,
            results_cache_ttl=Duration.seconds(0)
        )

        # DynamoDB Table for Favorites
        favorites_table = DynamoTable(
            self,
            "UserFavoritesTable",
            table_name="UserOrdersTable",
            partition_key="userId",
            sort_key="favoriteId"
        )
        

        #Dead Letter Queue for failed favorites processing
        favorites_dlq = sqs.Queue(
            self, "FavoritesDLQ",
            queue_name="food-delivery-favorites-dlq",
            retention_period=Duration.days(14)
        )

        # SQS Queue - FavoritesQueue with DLQ
        favorites_queue = sqs.Queue(
            self, "FavoritesQueue",
            queue_name="food-delivery-favorites-queue",
            visibility_timeout=Duration.seconds(300),
            retention_period=Duration.days(14),
            receive_message_wait_time=Duration.seconds(20),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=favorites_dlq
            )
        )

        # Lambda Layer for Powertools 
        powertools_layer = lmbda.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79"
        )

        # List User Favorites Lambda
        list_user_favorites_lambda = lmbda.Function(
            self, "ListUserFavoritesLambda",
            function_name="list_user_favorites",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="list_user_favorites.lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/address_assets/favorites"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": favorites_table.table_name,
                "POWERTOOLS_SERVICE_NAME": "favorites-service"
            },
            timeout=Duration.seconds(10)
        )
        favorites_table.grant_read_data(list_user_favorites_lambda)

        # Process Favorites Queue Lambda (processes SQS messages)
        process_favorites_queue_lambda = lmbda.Function(
            self, "ProcessFavoritesQueueLambda",
            function_name="process_favorites_queue",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="process_favorites_queue.lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/address_assets/favorites"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": favorites_table.table_name,
                "POWERTOOLS_SERVICE_NAME": "favorites-service"
            },
            timeout=Duration.seconds(30)
        )
        favorites_table.grant_read_write_data(process_favorites_queue_lambda)

        # Add SQS event source mapping to process_favorites_queue_lambda
        process_favorites_queue_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(
                favorites_queue,
                batch_size=10,
                max_batching_window=Duration.seconds(5)
            )
        )

        # API Gateway for Favorites Management
        favorites_api = apigw.RestApi(
            self, "FavoritesApiGateway",
            rest_api_name="FoodDeliveryFavoritesApi",
            description="API for favorites management in food delivery app",
            deploy=False
        )

        # CloudWatch Log Group for API Gateway
        log_group = logs.LogGroup(
            self, "FavoritesApiLogs",
            log_group_name="apigw/FavoritesApiLogs",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Favorites resource: /favorites
        favorites_resource = favorites_api.root.add_resource("favorites")

        # GET /favorites - List favorites
        favorites_resource.add_method(
            "GET",
            apigw.LambdaIntegration(list_user_favorites_lambda),
            authorization_type=apigw.AuthorizationType.CUSTOM,
            authorizer=authorizer,
        )

        # API Gateway Deployment and Stage
        deployment = apigw.Deployment(self, "FavoritesApiDeployment", api=favorites_api)
        stage = apigw.Stage(
            self, "FavoritesApiStage",
            deployment=deployment,
            stage_name="dev",
            access_log_destination=apigw.LogGroupLogDestination(log_group),
            access_log_format=apigw.AccessLogFormat.json_with_standard_fields(
                caller=False,
                http_method=True,
                ip=True,
                protocol=True,
                request_time=True,
                resource_path=True,
                response_length=True,
                status=True,
                user=True,
            ),
            logging_level=apigw.MethodLoggingLevel.INFO,
            data_trace_enabled=True,
            metrics_enabled=True
        )
        favorites_api.deployment_stage = stage

        # CloudWatch Alarms for monitoring
        alarms_topic = sns.Topic.from_topic_arn(
            self, "ImportedAlarmsTopic",
            topic_arn=f"arn:aws:sns:{self.region}:{self.account}:food-delivery-alarms"
        )

        # SQS Queue Depth Alarm
        queue_depth_alarm = cloudwatch.Alarm(
            self, "FavoritesQueueDepthAlarm",
            alarm_name="FavoritesQueue-Depth",
            metric=cloudwatch.Metric(
                namespace="AWS/SQS",
                metric_name="ApproximateNumberOfVisibleMessages",
                dimensions_map={"QueueName": favorites_queue.queue_name},
                period=Duration.seconds(300),
                statistic="Average"
            ),
            threshold=100,
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )
        queue_depth_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarms_topic))

        # Lambda function alarms
        favorites_lambda_functions = [
            ("ListUserFavorites", list_user_favorites_lambda),
            ("ProcessFavoritesQueue", process_favorites_queue_lambda)
        ]

        for name, lambda_func in favorites_lambda_functions:
            error_alarm = cloudwatch.Alarm(
                self, f"{name}LambdaErrorsAlarm",
                alarm_name=f"{name}Lambda-Errors",
                metric=lambda_func.metric_errors(
                    statistic="Sum", 
                    period=Duration.seconds(60)
                ),
                threshold=1,
                evaluation_periods=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            )
            error_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarms_topic))

        # Stack Outputs
        CfnOutput(
            self, "FavoritesTableOutput",
            value=favorites_table.table_name,
            export_name="FavoritesTable"
        )
        
        CfnOutput(
            self, "FavoritesApiUrlOutput",
            value=favorites_api.url,
            export_name="FavoritesApiUrl"
        )
        
        CfnOutput(
            self, "FavoritesQueueUrlOutput",
            value=favorites_queue.queue_url,
            export_name="FavoritesQueueUrl"
        )

        # Store references as properties for potential cross-stack usage
        self.favorites_table = favorites_table
        self.favorites_queue = favorites_queue
        self.favorites_api = favorites_api