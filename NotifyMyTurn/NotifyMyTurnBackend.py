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

        #lambda
        HourlyNotifier = lmbd.Function(self, 
                                         "HourlyLambda",
                                         runtime=lmbd.Runtime.PYTHON_3_12,
                                         handler="HourlyNotifier.lambda_handler",
                                         code=lmbd.Code.from_asset("NotifyMyTurn/assets"),
                                         environment={
                                            "QUEUE_URL": sqs_hour_queue.queue_url,
                                            "sender_email" : sender,
                                            "receiver_email" : receiver,
                                            "TABLE_NAME" : dynamo.table_name
                                        }
                                        )

        DailyNotifier = lmbd.Function(self, 
                                            "DailyLambda",
                                            runtime=lmbd.Runtime.PYTHON_3_12,
                                            handler="DailyNotifier.lambda_handler",
                                            code=lmbd.Code.from_asset("NotifyMyTurn/assets"),
                                            environment={
                                                "QUEUE_URL": sqs_day_queue.queue_url,
                                                "sender_email" : sender,
                                                "receiver_email" : receiver,
                                                "TABLE_NAME" : dynamo.table_name
                                            }   
                                           )
        

        

        dynamo.grant_read_write_data(HourlyNotifier)
        dynamo.grant_read_write_data(DailyNotifier)


        HourlyNotifier.add_to_role_policy(
            iam.PolicyStatement(
                actions=["dynamodb:Query"],
                resources=[
                    dynamo.table_arn, 
                    f"{dynamo.table_arn}/index/LocationTimeIndex"  
                ]
            )
        )
        
        ses_service.grant_send_email(HourlyNotifier)
        ses_service.grant_send_email(DailyNotifier)
       

        ses_receiver_service.grant_send_email(HourlyNotifier)
        ses_receiver_service.grant_send_email(DailyNotifier)
        
        

        #sqs
        sqs_hour_queue.grant_send_messages(HourlyNotifier)
        sqs_day_queue.grant_send_messages(DailyNotifier)
        

        #eventsource
        HourlyNotifier.add_event_source(event_sources.SqsEventSource(sqs_hour_queue))
        DailyNotifier.add_event_source(event_sources.SqsEventSource(sqs_day_queue))

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

        every_3_hours_rule.add_target(targets.LambdaFunction(HourlyNotifier))

        

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
        

        every_24_hours_rule.add_target(targets.LambdaFunction(DailyNotifier))
     