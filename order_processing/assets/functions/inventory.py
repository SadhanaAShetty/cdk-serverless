import boto3
import json
import os
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes.sqs_event import SQSRecord
from aws_lambda_powertools.utilities.batch import (
    BatchProcessor,
    EventType,
    process_partial_response,
)

processor = BatchProcessor(event_type=EventType.SQS)

logger = Logger()
tracer = Tracer()

ses = boto3.client("ses")
QUEUE_URL = os.getenv("QUEUE_URL")
sender_email = os.getenv("sender_email")
receiver_email = os.getenv("receiver_email")


@tracer.capture_method
def record_handler(record: SQSRecord):
    sns_body = record.json_body
    message_str = sns_body.get("Message", "{}")
    message = json.loads(message_str)

    logger.info(
        "Processing SQS message for Inventory  Notification", extra={"body": message}
    )

    recipients = [receiver_email] if isinstance(receiver_email, str) else receiver_email

    email_body = (
        f"Order ID: {message['order_id']}\n"
        f"Customer ID: {message['customer_id']}\n"
        f"Item: {message['item']}\n"
        f"Quantity: {message['quantity']}\n"
        f"Address: {message['address']}"
    )

    response = ses.send_email(
        Source=sender_email,
        Destination={"ToAddresses": recipients},
        Message={
            "Subject": {"Data": "Shipment Notification"},
            "Body": {"Text": {"Data": email_body}},
        },
    )

    logger.info("Email sent successfully", extra={"message_id": response["MessageId"]})


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext):
    return process_partial_response(
        event=event, record_handler=record_handler, processor=processor, context=context
    )
