from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_lambda as lmbda,
    aws_dynamodb as ddb,
    aws_apigateway as apigw,
    aws_logs as logs,
    aws_ssm as ssm,
    aws_ses as ses,
    aws_iam as iam,
    aws_stepfunctions_tasks as tasks,
    aws_stepfunctions as sfn
)
from aws_cdk.custom_resources import AwsCustomResource, AwsCustomResourcePolicy, PhysicalResourceId
from constructs import Construct

class LoanProcessingStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #dynamodb
        loan_table = ddb.TableV2(
            self, "LoanApplication",
            table_name="loan_table",
            partition_key=ddb.Attribute(
                name="appointment_id",
                type=ddb.AttributeType.STRING
            ),
            billing=ddb.Billing.provisioned(
                read_capacity=ddb.Capacity.fixed(2),
                write_capacity=ddb.Capacity.autoscaled(
                    min_capacity=1,
                    max_capacity=3
                )
            ),
            removal_policy=RemovalPolicy.DESTROY
        )

        #ssm for email
        sender = ssm.StringParameter.from_string_parameter_name(
            self, "SesSenderIdentityParam",
            string_parameter_name="/ses/parameter/email/sender"
        ).string_value

        receiver = ssm.StringParameter.from_string_parameter_name(
            self, "SesReceiverIdentityParam",
            string_parameter_name="/ses/parameter/email/receiver"
        ).string_value

        ses_service = ses.EmailIdentity.from_email_identity_name(self, "ExistingEmailNotification", sender)
        ses_receiver_service = ses.EmailIdentity.from_email_identity_name(self, "ExistingEmailReceiver", receiver)

        #powertools
        powertool_layer = lmbda.LayerVersion.from_layer_version_arn(
            self, "Layer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79"
        )

        #application lambda
        submit_lambda = lmbda.Function(
            self, "SubmitLoanHandler",
            function_name="submit_loan_application",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="submit_loan_application.lambda_handler",
            code=lmbda.Code.from_asset("loan_processing/assets/functions"),
            layers=[powertool_layer],
            environment={
                "STATE_MACHINE_ARN": "placeholder",  
                "TABLE_NAME": loan_table.table_name,
                "sender_email": sender,
                "receiver_email": receiver,
            }
        )
        loan_table.grant_read_write_data(submit_lambda)

        #auto approve
        auto_approve_lambda = lmbda.Function(
            self, "AutoApproveHandler",
            function_name="auto_approve",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="auto_approve.lambda_handler",
            code=lmbda.Code.from_asset("loan_processing/assets/functions"),
            layers=[powertool_layer],
            environment={
                "TABLE_NAME": loan_table.table_name,
                "sender_email": sender,
                "receiver_email": receiver,
            }
        )
        loan_table.grant_read_write_data(auto_approve_lambda)
        ses_service.grant_send_email(auto_approve_lambda)
        ses_receiver_service.grant_send_email(auto_approve_lambda)

        #manager request email
        request_approval_lambda = lmbda.Function(
            self, "RequestApprovalHandler",
            function_name="approval_request",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="approval_request.lambda_handler",
            code=lmbda.Code.from_asset("loan_processing/assets/functions"),
            layers=[powertool_layer],
            environment={
                "TABLE_NAME": loan_table.table_name,
                "sender_email": sender,
                "receiver_email": receiver,
                "API_BASE_URL_PARAM": "/loan/api_base_url"
            }
        )
        loan_table.grant_read_write_data(request_approval_lambda)
        ses_service.grant_send_email(request_approval_lambda)
        ses_receiver_service.grant_send_email(request_approval_lambda)
        request_approval_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["states:SendTaskSuccess", "states:SendTaskFailure"],
                resources=["*"]
            )
        )

        
        request_approval_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[f"arn:aws:ssm:{self.region}:{self.account}:parameter/loan/api_base_url"]
            )
        )

        #step function
        is_small_amount = sfn.Choice(self, "Amount <= 3000")
        auto_approve = tasks.LambdaInvoke(self, "Auto Approve",
            lambda_function=auto_approve_lambda,
            output_path="$.Payload"
        )
        request_approval = tasks.LambdaInvoke(self, "Request Manager Approval",
            lambda_function=request_approval_lambda,
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            payload=sfn.TaskInput.from_object({
                "taskToken": sfn.JsonPath.task_token,
                "input": sfn.JsonPath.entire_payload
            }),
            timeout=Duration.hours(1)
        )

        definition = is_small_amount \
            .when(sfn.Condition.number_less_than_equals("$.amount", 3000), auto_approve) \
            .otherwise(request_approval)

        state_machine = sfn.StateMachine(self, "LoanProcessingStateMachine",
            definition=definition
        )

        submit_lambda.add_environment("STATE_MACHINE_ARN", state_machine.state_machine_arn)
        state_machine.grant_start_execution(submit_lambda)
        

        #manager_decission
        manager_decision_lambda = lmbda.Function(
            self, "ManagerDecisionHandler",
            function_name="manager_decision",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="manager_decision.lambda_handler",
            code=lmbda.Code.from_asset("loan_processing/assets/functions"),
            layers=[powertool_layer],
            environment={
                "TABLE_NAME": loan_table.table_name,
                "sender_email": sender,
                "receiver_email": receiver,
            }
        )
        loan_table.grant_read_write_data(manager_decision_lambda)
        ses_service.grant_send_email(manager_decision_lambda)
        ses_receiver_service.grant_send_email(manager_decision_lambda)
        state_machine.grant_task_response(manager_decision_lambda)
        

        #api
        api = apigw.RestApi(
            self, "LoanProcessorApi",
            rest_api_name="LoanProcessorApi",
            deploy=False
        )

        #/loan_application POST
        loan_resource = api.root.add_resource("loan_application")
        post_method_1 = loan_resource.add_method(
            "POST",
            apigw.LambdaIntegration(submit_lambda),
            api_key_required=True
        )

        #/approve GET
        approve_resource = api.root.add_resource("approve")
        approve_method = approve_resource.add_method(
            "GET",
            apigw.LambdaIntegration(manager_decision_lambda),
            api_key_required=False
        )

        # /deny GET
        deny_resource = api.root.add_resource("deny")
        deny_method = deny_resource.add_method(
            "GET",
            apigw.LambdaIntegration(manager_decision_lambda),
            api_key_required=False
        )

      
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

       
        api_base_url = f"https://{api.rest_api_id}.execute-api.{self.region}.amazonaws.com/{stage.stage_name}"

       
        ssm_put_parameter = AwsCustomResource(
            self, "PutApiBaseUrlParam",
            on_create={
                "service": "SSM",
                "action": "putParameter",
                "parameters": {
                    "Name": "/loan/api_base_url",
                    "Value": api_base_url,
                    "Type": "String",
                    "Overwrite": True
                },
                "physical_resource_id": PhysicalResourceId.of(f"ApiBaseUrl-{api_base_url}")
            },
            policy=AwsCustomResourcePolicy.from_sdk_calls(
                resources=[f"arn:aws:ssm:{self.region}:{self.account}:parameter/loan/api_base_url"]
            )
        )

       
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
                    method=post_method_1,
                    throttle=apigw.ThrottleSettings(
                        rate_limit=10,
                        burst_limit=2
                    )
                ),
                apigw.ThrottlingPerMethod(
                    method=approve_method,
                    throttle=apigw.ThrottleSettings(
                        rate_limit=5,
                        burst_limit=1
                    )
                ),
                apigw.ThrottlingPerMethod(
                    method=deny_method,
                    throttle=apigw.ThrottleSettings(
                        rate_limit=5,
                        burst_limit=1
                    )
                )
            ]
        )
