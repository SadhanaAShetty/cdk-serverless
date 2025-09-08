import os
import uuid
import json
from datetime import datetime

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


@tracer.capture_method
@app.get("/users")
def get_list_of_users():
    try:
        response = table.scan()
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        user = [
            {
                "userid": item.get("user_id"),
                "name": item.get("name"),
                "timestamp": item.get("time_stamp")
            }
            for item in items
        ]

        return {"statusCode": 200, "body": json.dumps(user)}
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}


@tracer.capture_method
@app.get("/users/{userid}")
def get_single_user(userid: str):
    print("DEBUG: get_single_user called with userid ->", userid)
    try:
        response = table.get_item(Key={"user_id": userid})
        if "Item" not in response:
            return {"statusCode": 404, "body": json.dumps({"error": "User ID not found"})}

        item = response["Item"]

        result = {
            "userid": item["user_id"],
            "name": item["name"],
            "timestamp": item["time_stamp"]
        }

        return {"statusCode": 200, "body": json.dumps(result)}
    except Exception as e:
        logger.error(f"Error retrieving user: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}



@tracer.capture_method
@app.post("/users")
def post_handler():
    data: dict = app.current_event.json_body
    required_keys = ["user_id", "item", "address", "phone", "email"]
    for key in required_keys:
        if key not in data:
            return {"statusCode": 400, "body": json.dumps({"error": f"Missing key: {key}"})}

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
            "body": json.dumps({
                "message": "Order received successfully!",
                "order_id": order_id,
                "user_id": data["user_id"],
                "item": data["item"],
                "address": data["address"]
            })
        }
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}


@tracer.capture_method
@app.put("/users/{userid}")
def put_handler(userid: str):
    data: dict = app.current_event.json_body
    if not data:
        return {"statusCode": 400, "body": json.dumps({"error": "Request body is empty"})}

    data["user_id"] = userid
    data["time_stamp"] = datetime.utcnow().isoformat()

    try:
        table.put_item(Item=data)
        return {"statusCode": 200, "body": json.dumps(data)}
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}


@tracer.capture_method
@app.delete("/users/{userid}")
def delete_handler(userid: str):
    try:
        table.delete_item(Key={"user_id": userid})
        return {"statusCode": 200, "body": json.dumps({"message": f"User {userid} deleted"})}
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}



# @logger.inject_lambda_context
# @tracer.capture_lambda_handler
def lambda_handler(event: dict, context):
    print("DEBUG incoming event:", json.dumps(event))
    return app.resolve(event, context)


