import boto3
import json
import os
import random
import string
from datetime import datetime
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.api_gateway import Response
from aws_lambda_powertools.utilities.typing import LambdaContext

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('dynamo')
scheduler_lambda_arn = os.environ["SCHEDULER_LAMBDA_ARN"]
sender_email = os.environ['sender_email']   
receiver_email = os.environ['receiver_email']
lambda_client = boto3.client("lambda")

tracer = Tracer()
logger = Logger()
app = APIGatewayRestResolver()


@tracer.capture_method
@app.post("/agenda")
def order_call():
    logger.info("Inside agenda handler")
    data: dict = app.current_event.json_body

    required_keys = ["user_name", "time_stamp", "location"]
    for key in required_keys:
        if key not in data:
            return Response(
                status_code=400,
                content_type="application/json",
                body=json.dumps({"error": f"Missing key: {key}"})
            )

    
    appointment_id = ''.join(random.choices(string.digits, k=8))

    item_to_store = {
        "appointment_id": appointment_id,  
        "user_name": data["user_name"],
        "time_stamp": data["time_stamp"],
        "location": data["location"]
    }

    try:
        table.put_item(Item=item_to_store)
        logger.info(f"Item successfully inserted: {item_to_store}")
    except Exception as e:
        logger.error(f"Error inserting item into DynamoDB: {str(e)}")
        return Response(
            status_code=500,
            content_type="application/json",
            body=json.dumps({"error": "Internal server error"})
        )

    confirmation = {
        "message": "Your appointment has been scheduled and will be notified 24 hours and 3 hours in advance.",
        "your_appointment_id" : appointment_id,
        "user_name": data["user_name"],
        "time_stamp": data["time_stamp"],
        "location": data["location"],
    }

    lambda_client.invoke(
        FunctionName=scheduler_lambda_arn,
        InvocationType='Event',  
        Payload=json.dumps({
            "appointment_id": appointment_id,
            "time_stamp": data["time_stamp"],
            "email": receiver_email 
        }).encode('utf-8')
    )

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
