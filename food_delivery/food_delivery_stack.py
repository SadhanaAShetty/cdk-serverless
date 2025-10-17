from aws_cdk import (
    Stack, Duration, RemovalPolicy,
    aws_apigateway as apigw,
    aws_lambda as lmbda,
    aws_dynamodb as dynamodb,
    aws_logs as logs,
)
from constructs import Construct

class AddressStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # address_table
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

        #Lambda Powertools layer
        powertools_layer = lmbda.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79",
        )

        #add_address Lambda
        add_address_lambda = lmbda.Function(
            self, "AddAddressLambda",
            function_name="add_address",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="add_address.lambda_handler",
            code=lmbda.Code.from_asset("assets"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": address_table.table_name
            },
            timeout=Duration.seconds(10)
        )
        address_table.grant_read_write_data(add_address_lambda)

        #update_address Lambda
        update_address_lambda = lmbda.Function(
            self, "UpdateAddressLambda",
            function_name="update_address",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="update_address.lambda_handler",
            code=lmbda.Code.from_asset("assets"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": address_table.table_name
            },
            timeout=Duration.seconds(10)
        )
        address_table.grant_read_write_data(update_address_lambda)

        #delete_address Lambda
        delete_address_lambda = lmbda.Function(
            self, "DeleteAddressLambda",
            function_name="delete_address",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="delete_address.lambda_handler",
            code=lmbda.Code.from_asset("assets"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": address_table.table_name
            },
            timeout=Duration.seconds(10)
        )
        address_table.grant_read_write_data(delete_address_lambda)

        #API Gateway
        api = apigw.RestApi(
            self, "AddressAPI",
            rest_api_name="AddressAPI",
            description="API for managing user addresses",
            deploy=True
        )

        log_group = logs.LogGroup(
            self, "AddressApiLogs",
            log_group_name="apigw/AddressApiLogs",
            retention=logs.RetentionDays.ONE_DAY,
            removal_policy=RemovalPolicy.DESTROY
        )

        addresses = api.root.add_resource("address")

        
        addresses.add_method(
            "POST",
            apigw.LambdaIntegration(add_address_lambda),
            authorization_type=apigw.AuthorizationType.NONE 
        )

        
        address_id = addresses.add_resource("{addressId}")

        address_id.add_method(
            "PUT",
            apigw.LambdaIntegration(update_address_lambda),
            authorization_type=apigw.AuthorizationType.NONE
        )

        address_id.add_method(
            "DELETE",
            apigw.LambdaIntegration(delete_address_lambda),
            authorization_type=apigw.AuthorizationType.NONE
        )
