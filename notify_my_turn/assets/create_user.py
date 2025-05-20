import boto3
import json
import os
import random
import string

from datetime import datetime
from boto3.dynamodb.conditions import Key
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.api_gateway import Response
from aws_lambda_powertools.utilities.typing import LambdaContext


dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('dynamo')
user_table =dynamodb.Table('member_table')
sender_email = os.environ['sender_email']   
receiver_email = os.environ['receiver_email']
lambda_client = boto3.client("lambda")

tracer = Tracer()
logger = Logger()
app = APIGatewayRestResolver()

@tracer.capture_method
@app.post("/create_user")
def new_user():
    logger.info("Inside create user handler")
    data: dict = app.current_event.json_body

    required_keys = [
        "bsn", "f_name", "l_name", "dob", "email", "phone",
        "house_number", "city", "street", "pincode", "subscribe"
    ]

    for key in required_keys:
        if key not in data:
            return Response(
                status_code=400,
                content_type="application/json",
                body=json.dumps({"error": f"Missing key: {key}"})
            )

    if not isinstance(data["subscribe"], bool):
        return Response(
            status_code=400,
            content_type="application/json",
            body=json.dumps({"error": "subscribe must be a boolean true or false"})
        )

   
    try:
        response = user_table.get_item(Key={"bsn": data["bsn"]})
        if "Item" in response:
            return Response(
                status_code=409,
                content_type="application/json",
                body=json.dumps({"error": "User with this BSN already exists"})
            )
    except Exception as e:
        logger.error(f"Error checking for existing user: {str(e)}")

    item_to_store = {
        "bsn": data["bsn"],
        "f_name": data["f_name"],
        "l_name": data["l_name"],
        "dob": data["dob"],
        "email": data["email"],
        "phone": data["phone"],
        "house_number": data["house_number"],
        "city": data["city"],
        "street": data["street"],
        "pincode": data["pincode"],
        "subscribe": data["subscribe"]
    }

    try:
        user_table.put_item(Item=item_to_store)
        logger.info(f"Item successfully inserted: {item_to_store}")
    except Exception as e:
        logger.error(f"Error inserting item into DynamoDB: {str(e)}")
        return Response(
            status_code=500,
            content_type="application/json",
            body=json.dumps({"error": "Internal server error"})
        )

    confirmation = {
        "message": "Your User account is successfully created.Now you can directly enter your BSN and book your appointment. We look forward to meeting you :)"
    }

    return Response(
        status_code=200,
        content_type="application/json",
        body=json.dumps(confirmation)
    )


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    logger.info(f"Received event: {json.dumps(event)}")
    return app.resolve(event, context)


