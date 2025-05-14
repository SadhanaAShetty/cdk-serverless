from aws_cdk import (
    Stack,
    aws_lambda as lmbd,
    aws_iam as iam,
    aws_ssm as ssm,
    aws_ses as ses,
    aws_dynamodb as ddb
)
from constructs import Construct

class NotifyMyTurnBackendStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # SSM parameters for emails
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

       
        dynamo = ddb.TableV2.from_table_name(self, "MyTable", "dynamo")

      
        powertool_layer = lmbd.LayerVersion.from_layer_version_arn(self, "Layer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79"
        )

        

       
        notifier = lmbd.Function(self, 
            "NotifierLambda",
            runtime=lmbd.Runtime.PYTHON_3_12,
            handler="hourly_notifier.lambda_handler", 
            code=lmbd.Code.from_asset("notify_my_turn/assets"),
            layers=[powertool_layer],
            environment={
                "sender_email": sender,
                "receiver_email": receiver,
                "TABLE_NAME": dynamo.table_name
            }
        )

        
        dynamo.grant_read_write_data(notifier)

        notifier.add_to_role_policy(
            iam.PolicyStatement(
                actions=["dynamodb:Query"],
                resources=[
                    dynamo.table_arn,
                    f"{dynamo.table_arn}/index/LocationTimeIndex"
                ]
            )
        )

        
        ses_service.grant_send_email(notifier)
        ses_receiver_service.grant_send_email(notifier)
        task_handler= lmbd.Function.from_function_name(self, "task_handler", function_name= "task_handler" )

        schedule_creator = lmbd.Function(self,
            "ScheduleCreatorLambda",
            runtime=lmbd.Runtime.PYTHON_3_12,
            handler="schedule_creator.lambda_handler",  
            code=lmbd.Code.from_asset("notify_my_turn/assets"),
            layers=[powertool_layer],
            environment={
                "NOTIFIER_LAMBDA_ARN": notifier.function_arn,
                "TABLE_NAME": dynamo.table_name,
                "sender_email": sender,
                "receiver_email": receiver
            }
        )

        schedule_creator.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "scheduler:CreateSchedule",
                    "scheduler:DeleteSchedule",
                    "scheduler:GetSchedule",
                    "scheduler:UpdateSchedule"
                ],
                resources=["*"]
            )
        )

        notifier.grant_invoke(schedule_creator)
        dynamo.grant_read_data(schedule_creator)


    

       
        

        

        
        

                 