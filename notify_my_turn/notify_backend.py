from aws_cdk import (
    Stack,
    App,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_lambda as lmbd,
    aws_lambda_event_sources as event_sources,
    aws_iam as iam,
    aws_ssm as ssm,
    aws_sns_subscriptions as subscriptions,
    aws_ses as ses,
    aws_events as events,
    aws_events_targets as targets,
    aws_dynamodb as ddb
)
from constructs import Construct

class NotifyMyTurnBackendStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #ssm param for sender and receiver email
        sender = ssm.StringParameter.from_string_parameter_name(
            self, "SesSenderIdentityParam",
            string_parameter_name="/ses/parameter/email/sender"
        ).string_value
        
        receiver= ssm.StringParameter.from_string_parameter_name(
            self, "SesReceiverIdentityParam",
            string_parameter_name="/ses/parameter/email/receiver"
        ).string_value
        

        ses_service = ses.EmailIdentity.from_email_identity_name(self, "ExistingEmailNotification", sender)
        ses_receiver_service = ses.EmailIdentity.from_email_identity_name(self, "ExistingEmailReceiver", receiver)

        sqs_hour_queue = sqs.Queue(self, "HourlyQueue")
        sqs_day_queue = sqs.Queue(self,"DailyQueue")
                                     
        dynamo = ddb.TableV2.from_table_name(self, "MyTable", "dynamo") 
        powertool_layer= lmbd.LayerVersion.from_layer_version_arn(self,"Layer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79"
        )                                          
        #lambda
        hourly_notifier = lmbd.Function(self, 
                                         "HourlyLambda",
                                         runtime=lmbd.Runtime.PYTHON_3_12,
                                         handler="hourly_notifier.lambda_handler",
                                         code=lmbd.Code.from_asset("notify_my_turn/assets"),
                                         layers = [powertool_layer],
                                         environment={
                                            "QUEUE_URL": sqs_hour_queue.queue_url,
                                            "sender_email" : sender,
                                            "receiver_email" : receiver,
                                            "TABLE_NAME" : dynamo.table_name
                                        }
                                        )

        daily_notifier = lmbd.Function(self, 
                                            "DailyLambda",
                                            runtime=lmbd.Runtime.PYTHON_3_12,
                                            handler="daily_notifier.lambda_handler",
                                            code=lmbd.Code.from_asset("notify_my_turn/assets"),
                                            layers = [powertool_layer],
                                            environment={
                                                "QUEUE_URL": sqs_day_queue.queue_url,
                                                "sender_email" : sender,
                                                "receiver_email" : receiver,
                                                "TABLE_NAME" : dynamo.table_name
                                            }   
                                           )
        

        

        dynamo.grant_read_write_data(hourly_notifier)
        dynamo.grant_read_write_data(daily_notifier)


        hourly_notifier.add_to_role_policy(
            iam.PolicyStatement(
                actions=["dynamodb:Query"],
                resources=[
                    dynamo.table_arn, 
                    f"{dynamo.table_arn}/index/LocationTimeIndex"  
                ]
            )
        )
        
        ses_service.grant_send_email(hourly_notifier)
        ses_service.grant_send_email(daily_notifier)
       

        ses_receiver_service.grant_send_email(hourly_notifier)
        ses_receiver_service.grant_send_email(daily_notifier)
        
        

        #sqs
        sqs_hour_queue.grant_send_messages(hourly_notifier)
        sqs_day_queue.grant_send_messages(daily_notifier)
        

        #eventsource
        hourly_notifier.add_event_source(event_sources.SqsEventSource(sqs_hour_queue))
        daily_notifier.add_event_source(event_sources.SqsEventSource(sqs_day_queue))

        #3 hours
        every_3_hours_rule = events.Rule(
            self, "Every3HoursRule",
            schedule=events.Schedule.cron(
                minute="*",
                hour="*/3",
                day="*", 
                month="*",
                year="*"     
            )
        )

        every_3_hours_rule.add_target(targets.LambdaFunction(hourly_notifier))

        

        #24 hours
        every_24_hours_rule = events.Rule(
            self, "DailyRule",
            schedule=events.Schedule.cron(
                minute="0",
                hour="0",  
                month="*",
                year="*"
            )
        )
        

        every_24_hours_rule.add_target(targets.LambdaFunction(daily_notifier))
     