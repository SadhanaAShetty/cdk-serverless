import json
import os
from datetime import datetime, timezone

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext



ses = boto3.client('ses')

tracer = Tracer()
logger = Logger()

dynamodb = boto3.resource('dynamodb')
USER_TABLE_NAME = os.environ['USER_TABLE_NAME']
user_table = dynamodb.Table(USER_TABLE_NAME)
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
    logger.info("Notifier Lambda started")

    detail = event.get('detail', {})
    appointment_id = detail.get('appointment_id')
    appointment_time_str = detail.get('appointment_time')  
    reminder_type = detail.get('reminder_type')  

    if not appointment_id or not appointment_time_str or not reminder_type:
        logger.error("Missing appointment_id, appointment_time or reminder_type in event detail.")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing appointment_id, appointment_time or reminder_type"})
        }

    if not appointment_time_str.endswith("Z"):
        appointment_time_str += "Z"

    try:
        response = table.get_item(Key={
            'appointment_id': appointment_id,
            'time_stamp': appointment_time_str
        })
    except Exception as e:
        logger.error(f"Error fetching appointment from DynamoDB: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to fetch appointment"})
        }


    appointment = response.get('Item')
    if not appointment:
        logger.error(f"Appointment not found for ID: {appointment_id} and time_stamp: {appointment_time_str}")
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Appointment not found"})
        }
    
    bsn_number = appointment.get('bsn')
    if not bsn_number:
        logger.error("Missing BSN in appointment data")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing BSN in appointment data"})
        }

    try:
        member_response = user_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('bsn').eq(bsn_number)
        )
        members = member_response.get('Items', [])
        if not members:
            logger.error(f"No member found for BSN: {bsn_number}")
            f_name = "User"
        else:
            f_name = members[0].get('f_name', 'User')
    except Exception as e:
        logger.error(f"Error fetching member details: {str(e)}")
        f_name = "User"

    try:
        time_stamp = datetime.fromisoformat(appointment_time_str.replace("Z", "+00:00"))
    except Exception as e:
        logger.error(f"Error parsing appointment_time: {str(e)}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid appointment_time format"})
        }

    user_email = appointment.get('email', receiver_email)
    location = appointment.get('location', 'the appointment center')

    if reminder_type == '24h':
        subject = "24-Hour Appointment Reminder"
        body = (
            f"Hello {f_name},\n\n"
            f"This is a reminder that you have an appointment at {location} "
            f"scheduled at {time_stamp.strftime('%Y-%m-%d %H:%M %Z')}.\n"
            f"This is your 24-hour reminder.\n"
        )
    elif reminder_type == '3h':
        subject = "3-Hour Appointment Reminder"
        body = (
            f"Hello {f_name},\n\n"
            f"This is a reminder that you have an appointment at {location} "
            f"scheduled at {time_stamp.strftime('%Y-%m-%d %H:%M %Z')}.\n"
            f"This is your 3-hour reminder. Please arrive 10 minutes early.\n"
        )
    else:
        logger.error(f"Unknown reminder_type: {reminder_type}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Unknown reminder_type"})
        }

    send_email(user_email, subject, body)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": f"{reminder_type} reminder email sent successfully"})
    }

@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    logger.info(f"Received event: {json.dumps(event)}")
    return handle_event(event, context)
