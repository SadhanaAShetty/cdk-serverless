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
    aws_cloudwatch as cloudwatch
)
from constructs import Construct


class FoodDeliveryStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #dynamoDB Table
        table = dynamodb.Table(self, "UserTable",
            table_name="UserTable",
            partition_key=dynamodb.Attribute(name="user_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        powertools_layer = lmbda.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79",
        )

       
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


        #authorizer Lambda
        authorizer_lambda = lmbda.Function(self, "AuthorizerLambda",
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
            results_cache_ttl=Duration.seconds(0)
        )

        #lambda for API methods
        user_lambda = lmbda.Function(self, "UserFunction",
            function_name="user_lambda",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="user.lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/assets"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": table.table_name
                },
            timeout=Duration.seconds(10)

        )


        table.grant_read_write_data(user_lambda)

        #API Gateway
        api = apigw.RestApi(self, "FoodDeliveryAPI",
            rest_api_name="FoodDeliveryAPI",
            description="API for food delivery app",
            deploy=False 
        )

        #logs
        log_group = logs.LogGroup(self, "FoodDeliveryLogs",
            log_group_name="apigw/FoodDeliveryLogs",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY
        )

        
        users = api.root.add_resource("users")

        users.add_method(
            "POST",
            apigw.LambdaIntegration(user_lambda),
            authorization_type=apigw.AuthorizationType.CUSTOM,
            authorizer=authorizer,
        )

        users.add_method(
            "GET",
            apigw.LambdaIntegration(user_lambda),
            authorization_type=apigw.AuthorizationType.CUSTOM,
            authorizer=authorizer,
        )

        user_id = users.add_resource("{userid}")

        user_id.add_method(
            "GET",
            apigw.LambdaIntegration(user_lambda),
            authorization_type=apigw.AuthorizationType.CUSTOM,
            authorizer=authorizer,
        )

        user_id.add_method(
            "PUT",
            apigw.LambdaIntegration(user_lambda),
            authorization_type=apigw.AuthorizationType.CUSTOM,
            authorizer=authorizer,
        )

        user_id.add_method(
            "DELETE",
            apigw.LambdaIntegration(user_lambda),
            authorization_type=apigw.AuthorizationType.CUSTOM,
            authorizer=authorizer,
        )

        
        deployment = apigw.Deployment(self, "Deployment", api=api)

        
        stage = apigw.Stage(self, "DevStage",
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

        receiver = ssm.StringParameter.from_string_parameter_name(
            self, "SesReceiverIdentityParam",
            string_parameter_name="/ses/parameter/email/receiver"
        ).string_value


        alarms_topic = sns.Topic(self, "AlarmsTopicSNS",
            topic_name="FoodDeliveryAlarms",
            display_name="Food Delivery Application Alarms"
        )

  
        sns.CfnSubscription(
            self, "AlarmsTopicEmailSubscription",
            protocol="email",
            topic_arn=alarms_topic.topic_arn,
            endpoint=receiver
        )

        api_5xx_alarm = cloudwatch.Alarm(self, "ApiGateway5XXAlarm",
            alarm_name="FoodDelivery-APIGateway-5XX-Errors",
            alarm_description="Alarm for API Gateway 5XX errors",
            metric=cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="5XXError",
                dimensions_map={
                    "ApiName": api.rest_api_name,
                    "Stage": stage.stage_name
                },
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )

        #user lambda function errors alarm
        user_lambda_error_alarm = cloudwatch.Alarm(self, "UserLambdaErrorAlarm",
            alarm_name="FoodDelivery-UserLambda-Errors",
            alarm_description="Alarm for User Lambda function errors",
            metric=cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Errors",
                dimensions_map={
                    "FunctionName": user_lambda.function_name
                },
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )

        #user lambda function throttles alarm
        user_lambda_throttle_alarm = cloudwatch.Alarm(self, "UserLambdaThrottleAlarm",
            alarm_name="FoodDelivery-UserLambda-Throttles",
            alarm_description="Alarm for User Lambda function throttles",
            metric=cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Throttles",
                dimensions_map={
                    "FunctionName": user_lambda.function_name
                },
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )

        #authorizer Lambda Function Errors Alarm
        authorizer_lambda_error_alarm = cloudwatch.Alarm(self, "AuthorizerLambdaErrorAlarm",
            alarm_name="FoodDelivery-AuthorizerLambda-Errors",
            alarm_description="Alarm for Authorizer Lambda function errors",
            metric=cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Errors",
                dimensions_map={
                    "FunctionName": authorizer_lambda.function_name
                },
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )

        #authorizer lambda function throttles alarm
        authorizer_lambda_throttle_alarm = cloudwatch.Alarm(self, "AuthorizerLambdaThrottleAlarm",
            alarm_name="FoodDelivery-AuthorizerLambda-Throttles",
            alarm_description="Alarm for Authorizer Lambda function throttles",
            metric=cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Throttles",
                dimensions_map={
                    "FunctionName": authorizer_lambda.function_name
                },
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )

        #SNS actions to all alarms
        alarms_topic_action = cloudwatch.SnsAction(alarms_topic)
        
        api_5xx_alarm.add_alarm_action(alarms_topic_action)
        api_5xx_alarm.add_ok_action(alarms_topic_action)
        
        user_lambda_error_alarm.add_alarm_action(alarms_topic_action)
        user_lambda_error_alarm.add_ok_action(alarms_topic_action)
        
        user_lambda_throttle_alarm.add_alarm_action(alarms_topic_action)
        user_lambda_throttle_alarm.add_ok_action(alarms_topic_action)
        
        authorizer_lambda_error_alarm.add_alarm_action(alarms_topic_action)
        authorizer_lambda_error_alarm.add_ok_action(alarms_topic_action)
        
        authorizer_lambda_throttle_alarm.add_alarm_action(alarms_topic_action)
        authorizer_lambda_throttle_alarm.add_ok_action(alarms_topic_action)

        approval_topic = sns.Topic(self, "FoodDeliveryAlarm")
        sns.CfnSubscription(
            self, "FoodDeliveryAlarmSubscription",
            protocol="email",
            topic_arn=approval_topic.topic_arn,
            endpoint=receiver
        )

        publish_role = iam.Role(
            self, "FoodDeliveryAlarm",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com")
        )
        approval_topic.grant_publish(publish_role)

        # Outputs
        CfnOutput(self, "UserPoolOutput", value=user_pool.user_pool_id, export_name="UserPool")
        CfnOutput(self, "UserPoolClientOutput", value=user_pool_client.user_pool_client_id, export_name="UserPoolClient")
        CfnOutput(self, "UserPoolAdminGroupOutput", value=group.group_name, export_name="UserPoolAdminGroup")
        CfnOutput(self, "UsersTableOutput", value=table.table_name, export_name="UsersTable")
        CfnOutput(self, "ApiUrlOutput", value=api.url, export_name="ApiUrl")
        CfnOutput(self, "FoodDeliveryAlarmOutput", value=approval_topic.topic_arn, export_name="FoodDeliveryAlarmTopic")
        CfnOutput(self, "AlarmsTopicOutput", value=alarms_topic.topic_arn, export_name="AlarmsTopicArn",description="SNS Topic ARN for CloudWatch Alarms notifications")