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


QUEUE_URL = os.getenv("QUEUE_URL")

@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext) -> None:
    logger.info("Shipment Lambda triggered")

    for record in event.get("Records", []):
        try:
            message_body = record["body"]
            print("Hey! Message recieved for the shipmentg process")
            logger.info(f"Received message: {message_body}")

            message = json.loads(message_body)
            logger.info(f"Received SNS notification  and shipment data: {message}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise
