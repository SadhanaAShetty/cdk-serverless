from aws_cdk import (
    Stack, Duration, RemovalPolicy,
    aws_apigateway as apigw,
    aws_lambda as lmbda,
    aws_dynamodb as dynamodb,
    aws_logs as logs,
    aws_cognito as cognito,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
)
from constructs import Construct


class AddressStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #DynamoDB Table
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

        # Cognito user pool 
        user_pool = cognito.UserPool.from_user_pool_id(
            self, "ImportedUserPool",
            user_pool_id="your-user-pool-id"
        )

        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self, "AddressApiAuthorizer",
            cognito_user_pools=[user_pool]
        )

        #Lambda Powertools layer
        powertools_layer = lmbda.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79",
        )

        #EventBridge Bus
        address_bus = events.EventBus(
            self, "AddressBus",
            event_bus_name="AddressBus"
        )

        #IAM Role for API Gateway to put events to EventBridge
        api_gw_eventbridge_role = iam.Role(
            self, "ApiGatewayEventBridgeRole",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
            path=f"/{self.stack_name}/",
        )

        api_gw_eventbridge_role.add_to_policy(
            iam.PolicyStatement(
                actions=["events:PutEvents"],
                resources=[address_bus.event_bus_arn],
            )
        )


        #Add Address Lambda
        add_address_lambda = lmbda.Function(
            self, "AddAddressLambda",
            function_name="add_address",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="add_user_address.lambda_handler",
            code=lmbda.Code.from_asset("address_assets/address"),
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
            function_name="edit_user_address",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="edit_user_address.lambda_handler",
            code=lmbda.Code.from_asset("address_assets/address"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": address_table.table_name
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
            code=lmbda.Code.from_asset("address_assets/address"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": address_table.table_name
            },
            timeout=Duration.seconds(10)
        )
        address_table.grant_read_write_data(delete_address_lambda)

        # List User Addresses Lambda
        list_user_addresses_lambda = lmbda.Function(
            self, "ListUserAddressesLambda",
            function_name="list_user_addresses",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="list_user_addresses.lambda_handler",
            code=lmbda.Code.from_asset("address_assets/address"),
            environment={
                "TABLE_NAME": address_table.table_name
            },
            timeout=Duration.seconds(10)
        )
        address_table.grant_read_data(list_user_addresses_lambda)

        #EventBridge Rules
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

        #API Gateway
        address_api = apigw.RestApi(
            self, "AddressApiGateway",
            rest_api_name="ProfileAddressApi",
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                metrics_enabled=True,
                logging_level=apigw.MethodLoggingLevel.INFO,
                data_trace_enabled=True
            ),
            endpoint_configuration=apigw.EndpointConfiguration(types=[apigw.EndpointType.REGIONAL]),
            cloud_watch_role=True
        )

        address_resource = address_api.root.add_resource("address")

        # POST /address -> EventBridge
        address_resource.add_method(
            "POST",
            apigw.AwsIntegration(
                service="events",
                action="PutEvents",
                integration_http_method="POST",
                options=apigw.IntegrationOptions(
                    credentials_role=api_gw_eventbridge_role,
                    request_templates={
                        "application/json": f"""
                        {{
                            "Entries": [{{
                                "Source": "customer-profile",
                                "DetailType": "address.added",
                                "Detail": "$util.escapeJavaScript($input.body)",
                                "EventBusName": "{address_bus.event_bus_name}"
                            }}]
                        }}
                        """
                    },
                    integration_responses=[apigw.IntegrationResponse(status_code="200")]
                )
            ),
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer,
            method_responses=[apigw.MethodResponse(status_code="200")]
        )

        # GET /address 
        get_integration = apigw.LambdaIntegration(
            handler=list_user_addresses_lambda,
            proxy=True
        )

        address_resource.add_method(
            "GET",
            get_integration,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer
        )

        # Permission for API Gateway to invoke list_user_addresses
        list_user_addresses_lambda.add_permission(
            "ApiGatewayInvokePermission",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:execute-api:{self.region}:{self.account}:{address_api.rest_api_id}/*/GET/address"
        )
