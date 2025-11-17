from aws_cdk import (
    Stack, Duration, RemovalPolicy, CfnOutput,
    aws_apigateway as apigw,
    aws_lambda as lmbda,
    aws_dynamodb as dynamodb,
    aws_logs as logs,
    aws_events as events,
)
from constructs import Construct
from constructs.ddb import DynamoTable
from constructs.lmbda_construct import LambdaConstruct
from cdk_nag import NagSuppressions


class AddressStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


        # DynamoDB Table for Addresses
        address_table = DynamoTable(
            self,
            "UserAddressesTable",
            table_name="UserAddressesTable",
            partition_key="userId",
            sort_key="addressId"
        )
        

        #importing authorizer lambda from main stack
        authorizer_lambda = lmbda.Function.from_function_name(
            self, "ImportedAuthorizerLambda",
            function_name="AuthorizerLambda"  
        )

        authorizer = apigw.TokenAuthorizer(
            self, "AddressAuthorizer",
            handler=authorizer_lambda,
            results_cache_ttl=Duration.seconds(0)
        )

        #Lambda Powertools layer
        powertools_layer = lmbda.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79",
        )

        #EventBridge Custom Bus for Address Events
        address_bus = events.EventBus(
            self, "FoodDeliveryAddressBus",
            event_bus_name="food-delivery-address-bus"
        )
        
        #Add Address Lambda
        add_address_construct = LambdaConstruct(
            self, "AddAddressLambda",
            function_name="add_user_address",
            handler="add_user_address.lambda_handler",
            code_path="food_delivery/address_assets/address",
            layers=[powertools_layer],
            env={
                "ADDRESS_TABLE_NAME": address_table.table_name,
                "EVENT_BUS_NAME": address_bus.event_bus_name
            },
            timeout=10
        )
        add_address_lambda = add_address_construct.lambda_fn
        address_table.grant_read_write_data(add_address_lambda)
        address_bus.grant_put_events_to(add_address_lambda)

        # Edit Address Lambda
        edit_address_construct = LambdaConstruct(
            self, "EditAddressLambda",
            function_name="edit_user_address",
            handler="edit_user_address.lambda_handler",
            code_path="food_delivery/address_assets/address",
            layers=[powertools_layer],
            env={
                "ADDRESS_TABLE_NAME": address_table.table_name,
                "EVENT_BUS_NAME": address_bus.event_bus_name
            },
            timeout=10
        )
        edit_address_lambda = edit_address_construct.lambda_fn
        address_table.grant_read_write_data(edit_address_lambda)
        address_bus.grant_put_events_to(edit_address_lambda)

        #Delete Address Lambda
        delete_address_construct = LambdaConstruct(
            self, "DeleteAddressLambda",
            function_name="delete_user_address",
            handler="delete_user_address.lambda_handler",
            code_path="food_delivery/address_assets/address",
            layers=[powertools_layer],
            env={
                "ADDRESS_TABLE_NAME": address_table.table_name,
                "EVENT_BUS_NAME": address_bus.event_bus_name
            },
            timeout=10
        )
        delete_address_lambda = delete_address_construct.lambda_fn
        address_table.grant_read_write_data(delete_address_lambda)
        address_bus.grant_put_events_to(delete_address_lambda)

        # List User Addresses Lambda
        list_user_addresses_construct = LambdaConstruct(
            self, "ListUserAddressesLambda",
            function_name="list_user_addresses",
            handler="list_user_addresses.lambda_handler",
            code_path="food_delivery/address_assets/address",
            layers=[powertools_layer],
            env={
                "ADDRESS_TABLE_NAME": address_table.table_name
            },
            timeout=10
        )
        list_user_addresses_lambda = list_user_addresses_construct.lambda_fn
        address_table.grant_read_data(list_user_addresses_lambda)
        

        #API Gateway for Address Management
        address_api = apigw.RestApi(
            self, "AddressApiGateway",
            rest_api_name="FoodDeliveryAddressApi",
            description="API for address management in food delivery app",
            deploy=False
        )

        #CloudWatch Log Group for API Gateway
        log_group = logs.LogGroup(
            self, "AddressApiLogs",
            log_group_name="apigw/AddressApiLogs",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY
        )

        #Address resource: /addresses
        addresses_resource = address_api.root.add_resource("addresses")

        #POST /addresses - Add address
        addresses_resource.add_method(
            "POST",
            apigw.LambdaIntegration(add_address_lambda),
            authorization_type=apigw.AuthorizationType.CUSTOM,
            authorizer=authorizer,
        )

        #GET /addresses - List addresses
        addresses_resource.add_method(
            "GET",
            apigw.LambdaIntegration(list_user_addresses_lambda),
            authorization_type=apigw.AuthorizationType.CUSTOM,
            authorizer=authorizer,
        )

        #Address ID resource: /addresses/{addressId}
        address_id_resource = addresses_resource.add_resource("{addressId}")

        # PUT /addresses/{addressId} - Edit address
        address_id_resource.add_method(
            "PUT",
            apigw.LambdaIntegration(edit_address_lambda),
            authorization_type=apigw.AuthorizationType.CUSTOM,
            authorizer=authorizer,
        )

        #DELETE /addresses/{addressId} - Delete address
        address_id_resource.add_method(
            "DELETE",
            apigw.LambdaIntegration(delete_address_lambda),
            authorization_type=apigw.AuthorizationType.CUSTOM,
            authorizer=authorizer,
        )
        

        #API Gateway Deployment and Stage
        deployment = apigw.Deployment(self, "AddressApiDeployment", api=address_api)
        stage = apigw.Stage(
            self, "AddressApiStage",
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
            metrics_enabled=True,
            throttling_rate_limit=1000,
            throttling_burst_limit=2000
        )
        address_api.deployment_stage = stage

        #Nag Suppression for API Gateway
        NagSuppressions.add_resource_suppressions(
            address_api,
            suppressions=[
                {
                    "id": "AwsSolutions-APIG2",
                    "reason": "Request validation is handled inside Lambda functions; API Gateway request validation is redundant."
                },
                {
                    "id": "CdkNagValidationFailure",
                    "reason": "Known CDK-nag limitation with intrinsic functions in API Gateway logging configuration."
                }
            ]
        )

        #Nag Suppression for API Gateway Stage
        NagSuppressions.add_resource_suppressions(
            stage,
            suppressions=[
                {
                    "id": "AwsSolutions-APIG3",
                    "reason": "WAF is not required for this development/learning project. It adds significant cost without proportional benefit."
                },
                {
                    "id": "AwsSolutions-APIG1",
                    "reason": "Access logging is already enabled via CloudWatch Logs."
                },
                {
                    "id": "Serverless-APIGWXrayEnabled",
                    "reason": "X-Ray tracing is disabled to reduce costs. CloudWatch Logs and metrics provide sufficient observability."
                }
            ]
        )
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            path="/AddressStack/AddressApiGateway",
            suppressions=[{
                "id": "AwsSolutions-COG4",
                "reason": (
                    "A custom Lambda authorizer validates Cognito JWT tokens, including signature, audience, and group membership. "
                    "It provides stronger security than a direct Cognito authorizer."
                )
            }],
            apply_to_children=True
        )

        NagSuppressions.add_resource_suppressions(
            stage,
            suppressions=[{
                "id": "AwsSolutions-APIG3",
                "reason": (
                    "API stage is protected by Cognito and a custom Lambda authorizer, "
                    "with no public endpoints. Input validation is handled in Lambdas, making WAF unnecessary."
                )
            }]
        )

       
       

        # Stack Outputs
        CfnOutput(self, "AddressTableOutput", value=address_table.table_name, export_name="AddressTable")
        CfnOutput(self, "AddressApiUrlOutput", value=address_api.url, export_name="AddressApiUrl")
        CfnOutput(self, "AddressBusOutput", value=address_bus.event_bus_name, export_name="AddressBus")
