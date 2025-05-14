import boto3
import json
import os
from datetime import datetime, timedelta, timezone
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

tracer = Tracer()
logger = Logger()

sender_email = os.environ['sender_email']  
receiver_email = os.environ['receiver_email'] 
TABLE_NAME = os.environ["TABLE_NAME"]
table = dynamodb.Table(TABLE_NAME)


@tracer.capture_method
def send_email(to_email, subject, body):
    try:
        response = ses.send_email(
            Source=sender_email,
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}}
            }
        )
        logger.info(f"Email sent successfully: {response}")
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")


@tracer.capture_method
def handle_event(event, context):
    logger.info("Scheduler Lambda started")


    appointment_id = event.get('detail', {}).get('appointment_id')
    if not appointment_id:
        logger.error("Missing appointment_id in event detail.")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing appointment_id"})
        }

    try:
        response = table.get_item(Key={'appointment_id': appointment_id})
    except Exception as e:
        logger.error(f"Error fetching data from DynamoDB: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to fetch appointment"})
        }

    appointment = response.get('Item')
    if not appointment:
        logger.error(f"Appointment not found for ID: {appointment_id}")
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Appointment not found"})
        }

    
    time_stamp = datetime.strptime(appointment['time_stamp'], '%Y-%m-%dT%H:%M:%S')
    user_email = appointment.get('email', receiver_email)
    user_name = appointment.get('name', 'User')
    location = appointment.get('location', 'the appointment center')

    
    event_info = (
        f"Hello {user_name},\n\n"
        f"This is a reminder that you have an appointment at {location} "
        f"scheduled at {time_stamp.strftime('%Y-%m-%d %H:%M')}.\n"
        f"This is your 3-hour reminder. Please arrive 10 minutes early.\n"
    )

    now = datetime.now(timezone.utc)
    reminder_24hr = time_stamp - timedelta(hours=24)
    reminder_3hr = time_stamp - timedelta(hours=3)

    
    if reminder_24hr <= now < reminder_24hr + timedelta(minutes=5):
        send_email(user_email, "24-Hour Appointment Reminder", event_info)

    if reminder_3hr <= now < reminder_3hr + timedelta(minutes=5):
        send_email(user_email, "3-Hour Appointment Reminder", event_info)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Reminders processed successfully"})
    }


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    return handle_event(event, context)
