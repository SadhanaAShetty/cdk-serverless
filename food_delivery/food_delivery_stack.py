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
    aws_cloudwatch_actions as cloudwatch_actions
)
from constructs import Construct
from constructs.ddb import DynamoTable


class FoodDeliveryStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


        #constructs
        table = DynamoTable(
            self,
            "UserOrdersTable",
            table_name="UserOrdersTable",
            partition_key="userId",
            sort_key="orderId"
        )

        #dynamoDB Table
        # table = dynamodb.Table(
        #     self, "UserOrdersTable",
        #     table_name="UserOrdersTable",
        #     partition_key=dynamodb.Attribute(
        #         name="userId",
        #         type=dynamodb.AttributeType.STRING
        #     ),
        #     sort_key=dynamodb.Attribute(
        #         name="orderId",
        #         type=dynamodb.AttributeType.STRING
        #     ),
        #     billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        #     removal_policy=RemovalPolicy.DESTROY 
        # )

        powertools_layer = lmbda.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79",
        )

        #cognito user pool
        user_pool = cognito.UserPool(self, "UserPool",
            user_pool_name="food-order-userpool",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            standard_attributes=cognito.StandardAttributes(
                fullname=cognito.StandardAttribute(required=True, mutable=True),
                email=cognito.StandardAttribute(required=True, mutable=True),
            ),
        )

        user_pool_client = cognito.UserPoolClient(self, "UserPoolClient",
            user_pool=user_pool,
            generate_secret=False,
            prevent_user_existence_errors=True,
            auth_flows=cognito.AuthFlow(
                user_password=True, user_srp=True
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[cognito.OAuthScope.EMAIL, cognito.OAuthScope.OPENID],
                callback_urls=["http://localhost"],
            ),
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.COGNITO
            ],
        )

        domain = cognito.UserPoolDomain(self, "UserPoolDomain",
            user_pool=user_pool,
            cognito_domain=cognito.CognitoDomainOptions(domain_prefix="food-delivery-domain")
        )

        group = cognito.CfnUserPoolGroup(self, "AdminGroup",
            user_pool_id=user_pool.user_pool_id,
            group_name="admin"
        )

        #authorizer lambda 
        authorizer_lambda = lmbda.Function(self, "AuthorizerLambda",
            function_name="AuthorizerLambda", 
            runtime=lmbda.Runtime.PYTHON_3_11,
            handler="autherize.lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/assets"),
            environment={
                "USER_POOL_ID": user_pool.user_pool_id,
                "APPLICATION_CLIENT_ID": user_pool_client.user_pool_client_id,
                "ADMIN_GROUP_NAME": "admin"
            },
            timeout=Duration.seconds(10)
        )

        authorizer = apigw.TokenAuthorizer(self, "UserAuthorizer",
            handler=authorizer_lambda,
            results_cache_ttl=Duration.seconds(100)
        )

    
        #create_order Lambda
        create_order_lambda = lmbda.Function(
            self, "CreateOrderFunction",
            function_name="create_order",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="create_order.lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/assets"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": table.table_name
            },
            timeout=Duration.seconds(10)
        )
        table.grant_read_write_data(create_order_lambda)


        #edit_order Lambda
        edit_order_lambda = lmbda.Function(
            self, "EditOrderFunction",
            function_name="edit_order",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="edit_order.lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/assets"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": table.table_name
            },
            timeout=Duration.seconds(10)
        )
        table.grant_read_write_data(edit_order_lambda)

        #list_order Lambda
        list_order_lambda = lmbda.Function(
            self, "ListOrderFunction",
            function_name="list_order",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="list_order.lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/assets"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": table.table_name
            },
            timeout=Duration.seconds(10)
        )
        table.grant_read_data(list_order_lambda)

        #get_order Lambda
        get_order_lambda = lmbda.Function(
            self, "GetOrderFunction",
            function_name="get_order",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="get_order.lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/assets"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": table.table_name
            },
            timeout=Duration.seconds(10)
        )
        table.grant_read_data(get_order_lambda)

        #cancel_order Lambda
        cancel_order_lambda = lmbda.Function(
            self, "CancelOrderFunction",
            function_name="cancel_order",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="cancel_order.lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/assets"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": table.table_name
            },
            timeout=Duration.seconds(10)
        )
        table.grant_read_write_data(cancel_order_lambda)


        #API Gateway
        api = apigw.RestApi(
            self, "FoodDeliveryAPI",
            rest_api_name="FoodDeliveryAPI",
            description="API for food delivery app",
            deploy=False
        )

        
        log_group = logs.LogGroup(
            self, "FoodDeliveryLogs",
            log_group_name="apigw/FoodDeliveryLogs",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY
        )

  
        orders = api.root.add_resource("orders")

       
        orders.add_method(
            "POST",
            apigw.LambdaIntegration(create_order_lambda),
            authorization_type=apigw.AuthorizationType.CUSTOM,
            authorizer=authorizer,
        )

        
        orders.add_method(
            "GET",
            apigw.LambdaIntegration(list_order_lambda),
            authorization_type=apigw.AuthorizationType.CUSTOM,
            authorizer=authorizer,
        )

       
        order_id = orders.add_resource("{orderId}")

     
        order_id.add_method(
            "GET",
            apigw.LambdaIntegration(get_order_lambda),
            authorization_type=apigw.AuthorizationType.CUSTOM,
            authorizer=authorizer,
        )

        
        order_id.add_method(
            "PUT",
            apigw.LambdaIntegration(edit_order_lambda),
            authorization_type=apigw.AuthorizationType.CUSTOM,
            authorizer=authorizer,
        )

        
        order_id.add_method(
            "DELETE",
            apigw.LambdaIntegration(cancel_order_lambda),
            authorization_type=apigw.AuthorizationType.CUSTOM,
            authorizer=authorizer,
        )

        
        deployment = apigw.Deployment(self, "Deployment", api=api)
        stage = apigw.Stage(
            self, "DevStage",
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
        api.deployment_stage = stage


        #sns topic for alarms
        receiver = ssm.StringParameter.from_string_parameter_name(
            self, "SesReceiverIdentityParam",
            string_parameter_name="/ses/parameter/email/receiver"
        ).string_value

        alarms_topic = sns.Topic(self, "FoodDeliveryAlarms",
            topic_name="food-delivery-alarms",
            display_name="Food Delivery Monitoring Alarms"
        )

        alarms_topic.add_subscription(
            sns_subscriptions.EmailSubscription(receiver)
        )
        
        #cloudWatch alarm for API gateway 5XX errors
        api_metric = api.metric_server_error(statistic="Sum", period=Duration.seconds(60))
        api_5xx_alarm = cloudwatch.Alarm(
            self, "ApiGateway5XXAlarm",
            metric=api_metric,
            threshold=0,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )
        api_5xx_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarms_topic))

        #cloudWatch alarm for API gateway 4XX errors
        api_4xx_metric = api.metric_client_error(statistic="Sum", period=Duration.seconds(60))
        api_4xx_alarm = cloudwatch.Alarm(
            self, "ApiGateway4XXAlarm",
            metric=api_4xx_metric,
            threshold=10, 
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )
        api_4xx_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarms_topic))

        #lambda functions error alarms
        lambda_functions = [
            ("CreateOrder", create_order_lambda),
            ("EditOrder", edit_order_lambda),
            ("ListOrder", list_order_lambda),
            ("GetOrder", get_order_lambda),
            ("CancelOrder", cancel_order_lambda),
            ("Authorizer", authorizer_lambda)
        ]

        for name, lambda_func in lambda_functions:
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

            
            duration_alarm = cloudwatch.Alarm(
                self, f"{name}LambdaDurationAlarm",
                alarm_name=f"{name}Lambda-Duration",
                metric=lambda_func.metric_duration(
                    statistic="Average", 
                    period=Duration.seconds(60)
                ),
                threshold=8000, 
                evaluation_periods=2,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            )
            duration_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarms_topic))

            #Throttle Alarm for each Lambda
            throttle_alarm = cloudwatch.Alarm(
                self, f"{name}LambdaThrottleAlarm",
                alarm_name=f"{name}Lambda-Throttles",
                metric=lambda_func.metric_throttles(
                    statistic="Sum", 
                    period=Duration.seconds(60)
                ),
                threshold=1,
                evaluation_periods=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            )
            throttle_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarms_topic))

        #DynamoDB Errors Alarm
        dynamodb_error_alarm = cloudwatch.Alarm(
            self, "DynamoDBErrorsAlarm",
            alarm_name="DynamoDB-Errors",
            metric=cloudwatch.Metric(
                namespace="AWS/DynamoDB",
                metric_name="SystemErrors",
                dimensions_map={"TableName": table.table_name},
                period=Duration.seconds(60),
                statistic="Sum"
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )
        dynamodb_error_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarms_topic))

        #DynamoDB Throttling Alarm
        dynamodb_throttle_alarm = cloudwatch.Alarm(
            self, "DynamoDBThrottleAlarm",
            alarm_name="DynamoDB-Throttling",
            metric=cloudwatch.Metric(
                namespace="AWS/DynamoDB",
                metric_name="ThrottledRequests",
                dimensions_map={"TableName": table.table_name},
                period=Duration.seconds(60),
                statistic="Sum"
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )
        dynamodb_throttle_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alarms_topic))


        CfnOutput(self, "UsersTableOutput",
                description="DynamoDB Users table",
                value=table.table_name,
                export_name="FoodDelivery-UsersTable"
            )

        CfnOutput(self, "UsersFunctionOutput",
                description="Lambda function used to perform actions on the users data",
                value=create_order_lambda.function_name,
                export_name="FoodDelivery-UsersFunction"
            )

        CfnOutput(self, "APIEndpointOutput",
                description="API Gateway endpoint URL",
                value=f"https://{api.rest_api_id}.execute-api.{self.region}.amazonaws.com/dev",
                export_name="FoodDelivery-APIEndpoint"
            )

        CfnOutput(self, "UserPoolIdOutput",
                description="Cognito User Pool ID",
                value=user_pool.user_pool_id,
                export_name="FoodDelivery-UserPool"
            )

        CfnOutput(self, "UserPoolClientIdOutput",
                description="Cognito User Pool Application Client ID",
                value=user_pool_client.user_pool_client_id,
                export_name="FoodDelivery-UserPoolClient"
            )

        CfnOutput(self, "UserPoolAdminGroupOutput",
                description="User Pool group name for API administrators",
                value=group.group_name,
                export_name="FoodDelivery-UserPoolAdminGroup"
            )

        CfnOutput(self, "CognitoLoginURLOutput",
                description="Cognito User Pool Application Client Hosted Login UI URL",
                value=f"https://{domain.domain_name}.auth.{self.region}.amazoncognito.com/login?client_id={user_pool_client.user_pool_client_id}&response_type=code&redirect_uri=http://localhost",
                export_name="FoodDelivery-CognitoLoginURL"
            )

        CfnOutput(self, "CognitoAuthCommandOutput",
                description="AWS CLI command for Amazon Cognito User Pool authentication",
                value=f"aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --client-id {user_pool_client.user_pool_client_id} --auth-parameters USERNAME=<username>,PASSWORD=<password> --query 'AuthenticationResult.IdToken' --output text",
                export_name="FoodDelivery-CognitoAuthCommand"
        )