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
from cdk_nag import NagSuppressions


class AddressStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


        # DynamoDB Table for Addresses
        address_table = DynamoTable(
            self,
            "UserAddressesTable",
            table_name="UserOrdersTable",
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
        add_address_lambda = lmbda.Function(
            self, "AddAddressLambda",
            function_name="add_user_address",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="add_user_address.lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/address_assets/address"),
            layers=[powertools_layer],
            environment={
                "ADDRESS_TABLE_NAME": address_table.table_name,
                "EVENT_BUS_NAME": address_bus.event_bus_name
            },
            timeout=Duration.seconds(10)
        )
        address_table.grant_read_write_data(add_address_lambda)
        address_bus.grant_put_events_to(add_address_lambda)

        # Edit Address Lambda
        edit_address_lambda = lmbda.Function(
            self, "EditAddressLambda",
            function_name="edit_user_address",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="edit_user_address.lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/address_assets/address"),
            layers=[powertools_layer],
            environment={
                "ADDRESS_TABLE_NAME": address_table.table_name,
                "EVENT_BUS_NAME": address_bus.event_bus_name
            },
            timeout=Duration.seconds(10)
        )
        address_table.grant_read_write_data(edit_address_lambda)
        address_bus.grant_put_events_to(edit_address_lambda)

        #Delete Address Lambda
        delete_address_lambda = lmbda.Function(
            self, "DeleteAddressLambda",
            function_name="delete_user_address",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="delete_user_address.lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/address_assets/address"),
            layers=[powertools_layer],
            environment={
                "ADDRESS_TABLE_NAME": address_table.table_name,
                "EVENT_BUS_NAME": address_bus.event_bus_name
            },
            timeout=Duration.seconds(10)
        )
        address_table.grant_read_write_data(delete_address_lambda)
        address_bus.grant_put_events_to(delete_address_lambda)

        # List User Addresses Lambda
        list_user_addresses_lambda = lmbda.Function(
            self, "ListUserAddressesLambda",
            function_name="list_user_addresses",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="list_user_addresses.lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/address_assets/address"),
            layers=[powertools_layer],
            environment={
                "ADDRESS_TABLE_NAME": address_table.table_name
            },
            timeout=Duration.seconds(10)
        )
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
            metrics_enabled=True
        )
        address_api.deployment_stage = stage

       
       

        # Stack Outputs
        CfnOutput(self, "AddressTableOutput", value=address_table.table_name, export_name="AddressTable")
        CfnOutput(self, "AddressApiUrlOutput", value=address_api.url, export_name="AddressApiUrl")
        CfnOutput(self, "AddressBusOutput", value=address_bus.event_bus_name, export_name="AddressBus")
