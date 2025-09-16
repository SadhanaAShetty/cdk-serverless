from aws_cdk import (
    Stack, Duration, RemovalPolicy, CfnOutput,
    aws_cognito as cognito,
    aws_apigateway as apigw,
    aws_lambda as lmbda,
    aws_dynamodb as dynamodb,
    aws_logs as logs
)
from constructs import Construct


class FoodDeliveryStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # DynamoDB Table
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


        # Authorizer Lambda
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

        # Single Lambda Function for all API Methods
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

        # API Gateway
        api = apigw.RestApi(self, "FoodDeliveryAPI",
            rest_api_name="FoodDeliveryAPI",
            description="API for food delivery app",
            deploy=False 
        )

        # Create logs
        log_group = logs.LogGroup(self, "FoodDeliveryLogs",
            retention=logs.RetentionDays.ONE_DAY
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
        )

       
        api.deployment_stage = stage


        CfnOutput(self, "UserPoolOutput", value=user_pool.user_pool_id, export_name="UserPool")
        CfnOutput(self, "UserPoolClientOutput", value=user_pool_client.user_pool_client_id, export_name="UserPoolClient")
        CfnOutput(self, "UserPoolAdminGroupOutput", value=group.group_name, export_name="UserPoolAdminGroup")
        CfnOutput(self, "UsersTableOutput", value=table.table_name, export_name="UsersTable")
        CfnOutput(self, "ApiUrlOutput", value=api.url, export_name="ApiUrl")


  