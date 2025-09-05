import boto3
import json
from datetime import datetime, timedelta
import os
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext


tracer = Tracer()
logger = Logger()


scheduler = boto3.client("scheduler")
dynamodb = boto3.resource("dynamodb")
user_table = dynamodb.Table("member_table")
notifier_arn = os.environ["NOTIFIER_LAMBDA_ARN"]
scheduler_role_arn = os.environ["SCHEDULER_ROLE_ARN"]
sender_email = os.environ["sender_email"]
receiver_email = os.environ["receiver_email"]


@tracer.capture_method
def schedule_event(event, context):
    appointment_time = datetime.strptime(event["time_stamp"], "%Y-%m-%dT%H:%M:%SZ")
    appointment_id = event["appointment_id"]
    user_email = receiver_email

    reminders = {
        "24h": appointment_time - timedelta(hours=24),
        "3h": appointment_time - timedelta(hours=3),
    }

    for key, reminder_time in reminders.items():
        schedule_name = f"Scheduler-{appointment_id}-{key}"
        try:
            scheduler.create_schedule(
                Name=schedule_name,
                ScheduleExpression=f"at({reminder_time.isoformat()})",
                FlexibleTimeWindow={"Mode": "OFF"},
                Target={
                    "Arn": notifier_arn,
                    "RoleArn": scheduler_role_arn,
                    "Input": json.dumps(
                        {
                            "detail": {
                                "user_email": user_email,
                                "appointment_time": appointment_time.strftime(
                                    "%Y-%m-%dT%H:%M:%SZ"
                                ),
                                "reminder_type": key,
                                "appointment_id": appointment_id,
                            }
                        }
                    ),
                },
            )
            logger.info(f"Created schedule: {schedule_name}")
        except scheduler.exceptions.ConflictException:
            logger.warning(f"Schedule {schedule_name} already exists. Skipping.")
        except Exception as e:
            logger.error(f"Failed to create schedule {schedule_name}: {str(e)}")

    return {"message": "Reminder schedules processed"}


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    logger.info(f"Received event: {json.dumps(event)}")
    return schedule_event(event, context)
