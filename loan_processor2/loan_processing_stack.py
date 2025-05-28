from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_lambda as lmbda,
    aws_dynamodb as ddb,
    aws_apigateway as apigw,
    aws_logs as logs,
    aws_ssm as ssm,
    aws_iam as iam,
    aws_sns as sns,
    aws_stepfunctions_tasks as tasks,
    aws_stepfunctions as sfn
)
from aws_cdk.custom_resources import AwsCustomResource, AwsCustomResourcePolicy, PhysicalResourceId
from constructs import Construct

class LoanProcessingStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        loan_table = ddb.TableV2(
            self, "LoanTable",
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

        receiver = ssm.StringParameter.from_string_parameter_name(
            self, "SesReceiverIdentityParam",
            string_parameter_name="/ses/parameter/email/receiver"
        ).string_value

        approval_topic = sns.Topic(self, "ApprovalTopic")
        sns.CfnSubscription(
            self, "ApprovalEmailSubscription",
            protocol="email",
            topic_arn=approval_topic.topic_arn,
            endpoint=receiver
        )

        publish_role = iam.Role(
            self, "SnsPublishRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com")
        )
        approval_topic.grant_publish(publish_role)

        auto_approved = sfn.Succeed(self, "Auto-Approved")
        approved = sfn.Succeed(self, "Approved")
        declined = sfn.Fail(self, "Declined")

        
        approval_choice = sfn.Choice(self, "Approval/Decline")
        approval_choice.when(sfn.Condition.string_equals("$.status", "approved"), approved)
        approval_choice.when(sfn.Condition.string_equals("$.status", "denied"), declined)

        powertools_layer = lmbda.LayerVersion.from_layer_version_arn(
            self, "PowertoolsLayer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79"
        )

        submit_lambda = lmbda.Function(
            self, "SubmitLoanRequestHandler",
            function_name="submit_loan_application",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="submit_loan_application.lambda_handler",
            code=lmbda.Code.from_asset("loan_processor2/assets/functions"),
            layers=[powertools_layer],
            environment={
                "STATE_MACHINE_ARN": "placeholder",
                "TABLE_NAME": loan_table.table_name
            }
        )
        loan_table.grant_read_write_data(submit_lambda)

        auto_approve_lambda = lmbda.Function(
            self, "AutoApproveHandler",
            function_name="auto_approve",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="auto_approve.lambda_handler",
            code=lmbda.Code.from_asset("loan_processor2/assets/functions"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": loan_table.table_name,
                "APPROVAL_TOPIC_ARN": approval_topic.topic_arn,
                "receiver_email": receiver,

            }
        )

        auto_approve_task = tasks.LambdaInvoke(
            self, "Auto-Approve Lambda Task",
            lambda_function=auto_approve_lambda,
            output_path="$.Payload"
        )
        loan_table.grant_read_write_data(auto_approve_lambda)
        

        request_approval_lambda = lmbda.Function(
            self, "RequestApprovalHandler",
            function_name="approval_request",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="approval_request.lambda_handler",
            code=lmbda.Code.from_asset("loan_processor2/assets/functions"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": loan_table.table_name,
                "API_BASE_URL_PARAM": "/loan/api_base_url",
                "APPROVAL_TOPIC_ARN": approval_topic.topic_arn
            }
        )
        approval_topic.grant_publish(request_approval_lambda)
        loan_table.grant_read_write_data(request_approval_lambda)
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

        manager_decision_lambda = lmbda.Function(
            self, "ManagerDecisionHandler",
            function_name="manager_decision",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="manager_decision.lambda_handler",
            code=lmbda.Code.from_asset("loan_processor2/assets/functions"),
            layers=[powertools_layer],
            environment={
                "TABLE_NAME": loan_table.table_name,
                "APPROVAL_TOPIC_ARN": approval_topic.topic_arn
            }
        )
        manager_decision_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["states:SendTaskSuccess", "states:SendTaskFailure"],
                resources=["*"]
            )
        )
        loan_table.grant_read_write_data(manager_decision_lambda)
        approval_topic.grant_publish(manager_decision_lambda)

        request_approval = tasks.LambdaInvoke(self, "Request Manager Approval",
            lambda_function=request_approval_lambda,
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            payload=sfn.TaskInput.from_object({
                "taskToken": sfn.JsonPath.task_token,
                "input": sfn.JsonPath.entire_payload
            }),
            timeout=Duration.hours(1)
        )


        loan_check = sfn.Choice(self, "Loan >= $3000")
        loan_check.when(sfn.Condition.number_less_than("$.amount", 3000), auto_approve_task)
        loan_check.otherwise(request_approval.next(approval_choice))

        definition = loan_check

        state_machine = sfn.StateMachine(self, "LoanRequestStateMachine",
                                         definition=definition,
                                         state_machine_type=sfn.StateMachineType.STANDARD)

        state_machine.grant_start_execution(submit_lambda)
        submit_lambda.add_environment("STATE_MACHINE_ARN", state_machine.state_machine_arn)

        api = apigw.RestApi(self, "LoanRequestApi", rest_api_name="LoanRequestApi", deploy=False)

        loan_resource = api.root.add_resource("loan_application")
        post_method = loan_resource.add_method("POST", apigw.LambdaIntegration(submit_lambda), api_key_required=True)

        approve_resource = api.root.add_resource("approve")
        approve_method = approve_resource.add_method("GET", apigw.LambdaIntegration(manager_decision_lambda))

        deny_resource = api.root.add_resource("deny")
        deny_method = deny_resource.add_method("GET", apigw.LambdaIntegration(manager_decision_lambda))

        log_group = logs.LogGroup(
            self, "LoanRequestLogs", 
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

        AwsCustomResource(self, "PutApiBaseUrlParam",
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
            name="StandardPlan",
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
                        burst_limit=2)),
                apigw.ThrottlingPerMethod(
                    method=approve_method, 
                    throttle=apigw.ThrottleSettings(
                        rate_limit=5, 
                        burst_limit=1)),
                apigw.ThrottlingPerMethod(
                    method=deny_method, 
                    throttle=apigw.ThrottleSettings(
                        rate_limit=5, 
                        burst_limit=1))
            ]
        )
