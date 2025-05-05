import boto3
import json
import random
import os
import string
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.api_gateway import Response
from aws_lambda_powertools.utilities.typing import LambdaContext


logger = Logger()

ses = boto3.client("ses")
sqs = boto3.client("sqs")
QUEUE_URL = os.getenv("QUEUE_URL")
sender_email= os.getenv("sender_email")  
receiver_email = os.getenv("receiver_email")


@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext) -> None:
    logger.info("Shipment Lambda triggered")

    for record in event.get("Records", []):
        try:
            message_body = record["body"]
            print("Hey! Message recieved for the inventory process")
            logger.info(f"Received message: {message_body}")

            message = json.loads(message_body)
            logger.info(f"Received SNS notification  and inventory data: {message}")
            recipient_list = [receiver_email] if isinstance(receiver_email, str) else receiver_email


            body = json.dumps(message)
            response = ses.send_email(
                Source=sender_email,
                Destination={"ToAddresses": [receiver_email]},
                Message={
                    "Subject": {"Data": "Inventory Notification"},
                    "Body": {"Text": {"Data": json.dumps(message)}},
                },
            )

            logger.info(f"Email sent successfully: {response['MessageId']}")


        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise
