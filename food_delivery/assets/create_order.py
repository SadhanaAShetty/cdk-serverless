import os
import uuid
import json
from datetime import datetime
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext


logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


@tracer.capture_method
@app.post("/orders/{user_id}")
def create_order(user_id: str):
    data: dict = app.current_event.json_body
    
    if "user_id" not in data:
        data["user_id"] = str(uuid.uuid1())
   
    required_keys = ["restaurantId", "totalAmount", "orderItems"]
    for key in required_keys:
        if key not in data:
            return {
                "statusCode": 400, 
                "body": json.dumps({"error": f"Missing key: {key}"})
            }


    order_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    item_to_store = {
        "userId": user_id,
        "orderId": str(uuid.uuid1()),
        "restaurantId": data["restaurantId"],
        "totalAmount": data["totalAmount"],
        "orderItems": data["orderItems"],
        "status": "PLACED",
        "orderTime": order_time,
    }

    try:
        table.put_item(
            Item=item_to_store,
            ConditionExpression="attribute_not_exists(orderId) AND attribute_not_exists(userId)"
        )
        print("Your order is successfully placed!")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "user_id": item_to_store["user_id"],
                "order_id": item_to_store["order_id"],
                "timestamp": item_to_store["time_stamp"]
            })
        }

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return {
                "statusCode": 409,
                "body": json.dumps({"error": "Order already exists"})
            }
        raise

    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }
def lambda_handler(event: dict, context):
    print("DEBUG incoming event:", json.dumps(event))
    return app.resolve(event, context)