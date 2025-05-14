import boto3, uuid, json
from datetime import datetime, timedelta
import os
from datetime import datetime, timedelta, timezone
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext


tracer = Tracer()
logger =  Logger()


scheduler = boto3.client("scheduler")
notifier_arn = os.environ["NOTIFIER_LAMBDA_ARN"]
sender_email = os.environ['sender_email']   
receiver_email = os.environ['receiver_email'] 

@tracer.capture_method
def schedule_event(event, context):
    appointment_time = datetime.strptime(event['time_stamp'])
    appointment_id = event["appointment_id"]
    user_email = receiver_email

    reminders = {
        "24h": appointment_time - timedelta(hours=24),
        "3h": appointment_time - timedelta(hours=3)
    }

    for key, reminder_time in reminders.items():
        scheduler.create_schedule(
            Name="Scheduler",
            ScheduleExpression=f"at({reminder_time.isoformat()})",
            FlexibleTimeWindow={"Mode": "OFF"},
            Target={
                "Arn": notifier_arn,
                "RoleArn": context.invoked_function_arn.replace(":function:", ":role/"), 
                "Input": json.dumps({
                    "appointment_id": appointment_id,
                    "reminder_type": key,
                    "email": user_email
                })
            }
        )
    return {"message": "Reminder schedule created"}


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    logger.info(f"Received event: {json.dumps(event)}")
    return schedule_event(event, context)
