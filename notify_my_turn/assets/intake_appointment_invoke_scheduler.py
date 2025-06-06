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
scheduler_lambda_arn = os.environ["SCHEDULE_CREATOR_LAMBDA_ARN"]
sender_email = os.environ['sender_email']   
receiver_email = os.environ['receiver_email']
lambda_client = boto3.client("lambda")

tracer = Tracer()
logger = Logger()
app = APIGatewayRestResolver()


@tracer.capture_method
@app.post("/create_appointment")
def order_call():
    logger.info("Inside create_appointment handler")
    data: dict = app.current_event.json_body

    required_keys = ["bsn", "time_stamp","location"]
    for key in required_keys:
        if key not in data:
            return Response(
                status_code=400,
                content_type="application/json",
                body=json.dumps({"error": f"Missing key: {key}"})
            )

   
    try:
        datetime.fromisoformat(data["time_stamp"].replace("Z", "+00:00"))  
    except ValueError:
        return Response(
            status_code=400,
            content_type="application/json",
            body=json.dumps({"error": "Invalid timestamp format. Use ISO 8601."})
        )

    appointment_id = ''.join(random.choices(string.digits, k=8))
    item_to_store = {
        "appointment_id": appointment_id,
        "bsn": data["bsn"],
        "time_stamp": data["time_stamp"],
        "location": data["location"]
    }

    try:
        response = table.query(
            IndexName="time_stamp_index",
            KeyConditionExpression=Key("time_stamp").eq(data["time_stamp"])
        )
        if response["Items"]:
            return Response(
                status_code=409,
                content_type="application/json",
                body=json.dumps({
                    "error": "This time slot is unavailabe. Please choose a different time."
                })
            )
    except Exception as e:
        logger.error(f"Error checking for existing appointment: {str(e)}")
        return Response(
            status_code=500,
            content_type="application/json",
            body=json.dumps({"error": "Failed to check appointment availability"})
        )



    try:
        table.put_item(Item=item_to_store)
        logger.info(f"Appointment successfully inserted: {item_to_store}")
    except Exception as e:
        logger.error(f"Error inserting appointment: {str(e)}")
        return Response(
            status_code=500,
            content_type="application/json",
            body=json.dumps({"error": "Internal server error"})
        )

    
    user_email = data.get("email", receiver_email)

    
    lambda_client.invoke(
            FunctionName=scheduler_lambda_arn,
            InvocationType='Event',
            Payload=json.dumps({
                "appointment_id": appointment_id,
                "time_stamp": data["time_stamp"],
                "email": user_email
            }).encode('utf-8')
    )
   

    confirmation = {
        "message": "Your appointment has been scheduled and you will be notified 24 hours and 3 hours in advance.",
        "appointment_id": appointment_id,
        "bsn": data["bsn"],
        "time_stamp": data["time_stamp"],
        "location": data["location"]
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
