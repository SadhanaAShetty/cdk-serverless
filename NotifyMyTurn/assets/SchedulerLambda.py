import boto3
import json
import os
import random
import string
from datetime import datetime
from aws_lambda_powertools import Logger,Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.api_gateway import Response
from aws_lambda_powertools.utilities.typing import LambdaContext

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('dynamo')

tracer = Tracer()
logger = Logger()
app = APIGatewayRestResolver()


@tracer.capture_method
@app.post("/agenda")
def order_call():
    logger.info("Inside agenda handler")
    data: dict = app.current_event.json_body

    required_keys = ["user_name", "time_stamp", "location","branch"]
    for key in required_keys:
        if key not in data:
            return Response(
                status_code=400,
                content_type="application/json",
                body=json.dumps({"error": f"Missing key: {key}"})
            )

   
    item_to_store = {
        "user_name": data["user_name"],  
        "time_stamp": data["time_stamp"],  
        "location": data["location"],
        "address": data["address"],
        "branch": data["branch"]
    }

    table.put_item(Item=item_to_store)

    confirmation = {
        "message": "Your appointment has been scheduled  and will be notified 24 hours and 3 hours in advance .",
        "user_name": data["user_name"],  
        "time_stamp": data["time_stamp"],  
        "location": data["location"],
        "address" :data["address"],
        "branch" : data["branch"]
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