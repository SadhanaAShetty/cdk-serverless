from aws_cdk import (
    Stack,
    App,
    aws_dynamodb as ddb,
    aws_apigateway as apigw,
    RemovalPolicy,
    aws_lambda as lmbda,
    aws_logs as logs,
    aws_sns as sns,
    aws_ssm as ssm,
    aws_events as events
)
from constructs import Construct

class NotifyMyTurnFrontendStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


        dynamo = ddb.TableV2(
            self, "TaskSchedulerDb",
            table_name="dynamo",
            partition_key=ddb.Attribute(
                name="user_name",
                type=ddb.AttributeType.STRING
            ),
            sort_key=ddb.Attribute(
                name="time_stamp",
                type=ddb.AttributeType.STRING
            ),
            billing=ddb.Billing.provisioned(
                read_capacity=ddb.Capacity.fixed(2),
                write_capacity=ddb.Capacity.autoscaled(max_capacity=3)
            ),
            removal_policy=RemovalPolicy.DESTROY
        )

        dynamo.add_global_secondary_index(
            index_name="LocationTimeIndex",
            partition_key=ddb.Attribute(
                name="branch",
                type=ddb.AttributeType.STRING
            ),
            sort_key=ddb.Attribute(
                name="time_stamp",
                type=ddb.AttributeType.STRING
            )
        )       
        
        powertool_layer= lmbda.LayerVersion.from_layer_version_arn(self,"Layer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79"
        )

        #lambda
        task_handler = lmbda.Function(
            self, "TaskSchedulerLambda",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="scheduler_lambda.lambda_handler",
            layers = [powertool_layer],
            code=lmbda.Code.from_asset("notify_my_turn/assets")
            
        )

        # Grant permissions
        dynamo.grant_read_write_data(task_handler)

        api = apigw.RestApi(
            self, "TaskScheduleraApi",
            rest_api_name="MyTaskScheduler",
            deploy=False
        )

        task_resource = api.root.add_resource("agenda")
        post_method = task_resource.add_method(
            "POST",
            apigw.LambdaIntegration(task_handler),
            api_key_required=True
        )
        

        # Logging
        log_group = logs.LogGroup(
            self, "DevLogs",
            retention=logs.RetentionDays.ONE_DAY
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
                user=True
            )
        )

        
        api.deployment_stage = stage

        # API Key & Usage Plan
        key = api.add_api_key("ApiKey")

        plan = api.add_usage_plan(
            "UsagePlan",
            name="Easy",
            throttle=apigw.ThrottleSettings(
                rate_limit=10,
                burst_limit=2
            )
        )

        plan.add_api_key(key)

        plan.add_api_stage(
            stage=stage,
            throttle=[
                apigw.ThrottlingPerMethod(
                    method=post_method,
                    throttle=apigw.ThrottleSettings(
                        rate_limit=10,
                        burst_limit=2
                    )
                )
            ]
        )

        



        