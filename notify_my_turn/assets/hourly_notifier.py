import os
import boto3
from datetime import datetime, timedelta, timezone
from boto3.dynamodb.conditions import Key  
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext


logger = Logger()
tracer = Tracer()
metrics = Metrics(namespace="AppointmentService")


dynamodb = boto3.resource("dynamodb")
ses = boto3.client("ses")


TABLE_NAME = os.environ["TABLE_NAME"]
table = dynamodb.Table(TABLE_NAME)
sender_email = os.environ["sender_email"]
receiver_email = os.environ["receiver_email"]

@tracer.capture_method
def process_appointments():
    current_time = datetime.now(timezone.utc)
    three_hours_later = current_time + timedelta(minutes=5)

   
    current_timestamp = current_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    future_timestamp = three_hours_later.strftime("%Y-%m-%dT%H:%M:%SZ")

    response = table.query(
    IndexName='LocationTimeIndex',
    KeyConditionExpression=Key('branch').eq('rotterdam') & Key('time_stamp').between(current_timestamp, future_timestamp)
    )

    items = response.get("Items", [])
    metrics.add_metric(name="EventsProcessed", unit=MetricUnit.Count, value=len(items))
    logger.info(f"Found {len(items)} upcoming events.")

    for item in items:
        user_name = item.get("user_name", "Unknown User")
        time_stamp = item.get("time_stamp")
        location = item.get("location", "Not Provided")
        address = item.get("address", "Not Provided")
        branch =item.get("branch")

        event_info = (
            f"Appointment for {user_name} at {location}, {address}, scheduled at {time_stamp}.\n"
            f"This is your 3-hour reminder.\n"
            f"Please arrive 10 minutes early."
        )

        tracer.put_annotation("user", user_name)
        tracer.put_metadata("event_details", item)

        sent = ses.send_email(
            Source=sender_email,
            Destination={"ToAddresses": [receiver_email]},
            Message={
                "Subject": {"Data": "Upcoming Appointment Reminder"},
                "Body": {"Text": {"Data": event_info}},
            }
        )
        logger.info(f"Email sent to {receiver_email} for event: {event_info}")

        logger.info(f"SES response: {sent}")

        message_id = sent.get("MessageId")
        if message_id:
            table.put_item(Item={
                "user_name": f"{user_name}",
                "time_stamp": time_stamp, 
                "status": "sent",
                "message_id": message_id,
                "address": address,
                "branch" : branch, 
                "location" :location
        })

    return len(items)

@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    logger.info("Lambda handler invoked")
    try:
        count = process_appointments()
        return {"statusCode": 200, "body": f"Processed {count} events."}
    except Exception as e:
        logger.exception("Error processing events")
        metrics.add_metric(name="ProcessingFailures", unit=MetricUnit.Count, value=1)
        return {"statusCode": 500, "body": str(e)}
