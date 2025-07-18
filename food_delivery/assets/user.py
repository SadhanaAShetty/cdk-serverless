
import os
import uuid
from datetime import datetime

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.getenv("TABLE_NAME", "UserTable"))


@tracer.capture_method
@app.get("/users")
def get_all_handler():
    try:
        response = table.scan()
        data = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            data.extend(response.get("Items", []))
        return {"statusCode": 200, "body": data}
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        return {"statusCode": 500, "body": {"error": "Internal Server Error"}}


@tracer.capture_method
@app.get("/users/{userid}")
def get_handler(userid: str):
    try:
        response = table.get_item(Key={"user_id": userid})
        if "Item" not in response:
            return {"statusCode": 404, "body": {"error": "User ID not found"}}
        return {"statusCode": 200, "body": response["Item"]}
    except Exception as e:
        logger.error(f"Error retrieving user: {str(e)}")
        return {"statusCode": 500, "body": {"error": "Internal Server Error"}}


@tracer.capture_method
@app.post("/users")
def post_handler():
    data: dict = app.current_event.json_body
    required_keys = ["user_id", "item", "address", "phone", "email"]
    for key in required_keys:
        if key not in data:
            return {"statusCode": 400, "body": {"error": f"Missing key: {key}"}}

    order_id = str(uuid.uuid4())
    item_to_store = {
        "order_id": order_id,
        "user_id": data["user_id"],
        "item": data["item"],
        "address": data["address"],
        "phone": data["phone"],
        "email": data["email"],
        "time_stamp": datetime.utcnow().isoformat()
    }

    try:
        table.put_item(Item=item_to_store)
        return {
            "statusCode": 200,
            "body": {
                "message": "Order received successfully!",
                "order_id": order_id,
                "user_id": data["user_id"],
                "item": data["item"],
                "address": data["address"]
            }
        }
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        return {"statusCode": 500, "body": {"error": "Internal Server Error"}}


@tracer.capture_method
@app.put("/users/{userid}")
def put_handler(userid: str):
    data: dict = app.current_event.json_body
    if not data:
        return {"statusCode": 400, "body": {"error": "Request body is empty"}}

    data["user_id"] = userid
    data["time_stamp"] = datetime.utcnow().isoformat()

    try:
        table.put_item(Item=data)
        return {"statusCode": 200, "body": data}
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        return {"statusCode": 500, "body": {"error": "Internal Server Error"}}


@tracer.capture_method
@app.delete("/users/{userid}")
def delete_handler(userid: str):
    try:
        table.delete_item(Key={"user_id": userid})
        return {"statusCode": 200, "body": {"message": f"User {userid} deleted"}}
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return {"statusCode": 500, "body": {"error": "Internal Server Error"}}


@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    return app.resolve(event, context)
