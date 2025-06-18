from aws_cdk import (
    Stack,
    aws_dynamodb as ddb,
    aws_apigateway as apigw,
    RemovalPolicy,
    aws_lambda as lmbda,
    aws_logs as logs,
    aws_ssm as ssm,
    aws_ses as ses,
    aws_iam as iam,
)
from constructs import Construct


class NotifyMyTurnStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # appointment_table
        dynamo = ddb.TableV2(
            self,
            "TaskSchedulerDb",
            table_name="dynamo",
            partition_key=ddb.Attribute(
                name="appointment_id", type=ddb.AttributeType.STRING
            ),
            sort_key=ddb.Attribute(name="time_stamp", type=ddb.AttributeType.STRING),
            billing=ddb.Billing.provisioned(
                read_capacity=ddb.Capacity.fixed(2),
                write_capacity=ddb.Capacity.autoscaled(max_capacity=3),
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )
        # gsi
        dynamo.add_global_secondary_index(
            index_name="time_stamp_index",
            partition_key=ddb.Attribute(
                name="time_stamp", type=ddb.AttributeType.STRING
            ),
        )
        # user_tabel
        member_table = ddb.TableV2(
            self,
            "Members",
            table_name="member_table",
            partition_key=ddb.Attribute(name="bsn", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="f_name", type=ddb.AttributeType.STRING),
            billing=ddb.Billing.provisioned(
                read_capacity=ddb.Capacity.fixed(2),
                write_capacity=ddb.Capacity.autoscaled(max_capacity=3),
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )

        # SSM parameters for emails
        sender = ssm.StringParameter.from_string_parameter_name(
            self,
            "SesSenderIdentityParam",
            string_parameter_name="/ses/parameter/email/sender",
        ).string_value

        receiver = ssm.StringParameter.from_string_parameter_name(
            self,
            "SesReceiverIdentityParam",
            string_parameter_name="/ses/parameter/email/receiver",
        ).string_value

        # ses
        ses_service = ses.EmailIdentity.from_email_identity_name(
            self, "ExistingEmailNotification", sender
        )
        ses_receiver_service = ses.EmailIdentity.from_email_identity_name(
            self, "ExistingEmailReceiver", receiver
        )

        # powertool
        powertool_layer = lmbda.LayerVersion.from_layer_version_arn(
            self,
            "Layer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79",
        )

        # event_notifier_lambda
        notifier = lmbda.Function(
            self,
            "NotifierLambda",
            function_name="event_notifier",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="event_notifier.lambda_handler",
            code=lmbda.Code.from_asset("notify_my_turn/assets"),
            layers=[powertool_layer],
            environment={
                "sender_email": sender,
                "receiver_email": receiver,
                "TABLE_NAME": dynamo.table_name,
                "USER_TABLE_NAME": member_table.table_name,
            },
        )

        dynamo.grant_read_write_data(notifier)
        member_table.grant_read_write_data(notifier)

        notifier.add_to_role_policy(
            iam.PolicyStatement(
                actions=["dynamodb:Query"],
                resources=[
                    dynamo.table_arn,
                    member_table.table_arn,
                    f"{dynamo.table_arn}/index/*",
                    f"{member_table.table_arn}/index/*",
                ],
            )
        )

        ses_service.grant_send_email(notifier)
        ses_receiver_service.grant_send_email(notifier)

        event_scheduler_role = iam.Role(
            self,
            "SchedulerInvocationRole",
            assumed_by=iam.ServicePrincipal("scheduler.amazonaws.com"),
            inline_policies={
                "InvokeLambdaPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["lambda:InvokeFunction"],
                            resources=[notifier.function_arn],
                        )
                    ]
                )
            },
        )

        # event_scheduler_lambda
        schedule_creator = lmbda.Function(
            self,
            "ScheduleCreatorLambda",
            function_name="event_scheduler",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="event_scheduler.lambda_handler",
            code=lmbda.Code.from_asset("notify_my_turn/assets"),
            layers=[powertool_layer],
            environment={
                "NOTIFIER_LAMBDA_ARN": notifier.function_arn,
                "TABLE_NAME": dynamo.table_name,
                "USER_TABLE_NAME": member_table.table_name,
                "sender_email": sender,
                "receiver_email": receiver,
                "SCHEDULER_ROLE_ARN": event_scheduler_role.role_arn,
            },
        )

        schedule_creator.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "scheduler:CreateSchedule",
                    "scheduler:DeleteSchedule",
                    "scheduler:GetSchedule",
                    "scheduler:UpdateSchedule",
                ],
                resources=[
                    f"arn:aws:scheduler:{self.region}:{self.account}:schedule/default/*"
                ],
            )
        )

        schedule_creator.add_to_role_policy(
            iam.PolicyStatement(
                actions=["iam:PassRole"], resources=[event_scheduler_role.role_arn]
            )
        )

        notifier.grant_invoke(schedule_creator)
        dynamo.grant_read_data(schedule_creator)
        member_table.grant_read_write_data(schedule_creator)

        notifier.add_permission(
            "AllowSchedulerInvoke",
            principal=iam.ServicePrincipal("scheduler.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_account=self.account,
            source_arn=f"arn:aws:scheduler:{self.region}:{self.account}:schedule/default/*",
        )

        # intake_appointment_lambda
        task_handler = lmbda.Function(
            self,
            "TaskHandler",
            function_name="intake_appointment_invoke_scheduler",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="intake_appointment_invoke_scheduler.lambda_handler",
            layers=[powertool_layer],
            code=lmbda.Code.from_asset("notify_my_turn/assets"),
            environment={
                "TABLE_NAME": dynamo.table_name,
                "SCHEDULE_CREATOR_LAMBDA_ARN": schedule_creator.function_arn,
                "sender_email": sender,
                "receiver_email": receiver,
            },
        )
        # create_user_lambda
        create_user = lmbda.Function(
            self,
            "CreateUser",
            function_name="create_user",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="create_user.lambda_handler",
            layers=[powertool_layer],
            code=lmbda.Code.from_asset("notify_my_turn/assets"),
            environment={
                "USER_TABLE_NAME": member_table.table_name,
                "sender_email": sender,
                "receiver_email": receiver,
            },
        )

        task_handler.add_to_role_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[schedule_creator.function_arn],
            )
        )
        member_table.grant_read_write_data(create_user)

        schedule_creator.grant_invoke(task_handler)
        dynamo.grant_read_write_data(task_handler)

        # Api
        api = apigw.RestApi(
            self, "TaskSchedulerApi", rest_api_name="MyTaskScheduler", deploy=False
        )

        task_resource = api.root.add_resource("create_appointment")
        post_method_1 = task_resource.add_method(
            "POST", apigw.LambdaIntegration(task_handler), api_key_required=True
        )

        user_resource = api.root.add_resource("create_user")
        post_method_2 = user_resource.add_method(
            "POST", apigw.LambdaIntegration(create_user), api_key_required=True
        )

        log_group = logs.LogGroup(self, "DevLogs", retention=logs.RetentionDays.ONE_DAY)

        deployment = apigw.Deployment(self, "Deployment", api=api)

        stage = apigw.Stage(
            self,
            "DevStage",
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

        # API Key & Usage Plan
        key = api.add_api_key("ApiKey")

        plan = api.add_usage_plan(
            "UsagePlan",
            name="Easy",
            throttle=apigw.ThrottleSettings(rate_limit=10, burst_limit=2),
        )

        plan.add_api_key(key)

        plan.add_api_stage(
            stage=stage,
            throttle=[
                apigw.ThrottlingPerMethod(
                    method=post_method_1,
                    throttle=apigw.ThrottleSettings(rate_limit=10, burst_limit=2),
                ),
                apigw.ThrottlingPerMethod(
                    method=post_method_2,
                    throttle=apigw.ThrottleSettings(rate_limit=5, burst_limit=1),
                ),
            ],
        )
