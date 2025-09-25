import os
import json
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver

from utils import get_order

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


@tracer.capture_method
@app.post("/orders/edit/{orderId}")
def edit_order():
    event = app.current_event.request
    user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
    order_id = event["pathParameters"]["orderId"]
    new_data = json.loads(event["body"], parse_float=Decimal)

    new_data["userId"] = user_id
    new_data["orderId"] = order_id

    ddb_item = {
        "userId": user_id,
        "orderId": order_id,
        "data": new_data
    }

    ddb_item = json.loads(json.dumps(ddb_item), parse_float=Decimal)

    try:
        table.put_item(
            Item=ddb_item,
            ConditionExpression="attribute_exists(orderId) AND attribute_exists(userId) AND #data.#status = :status",
            ExpressionAttributeNames={"#data": "data", "#status": "status"},
            ExpressionAttributeValues={":status": "PLACED"},
            ReturnValuesOnConditionCheckFailure="ALL_OLD"
        )

        logger.info(f"Order {order_id} successfully edited for user {user_id}.")
        print(f"Order {order_id} successfully edited!")

        updated_order = get_order(user_id, order_id)
        return {
            "statusCode": 200,
            "body": json.dumps(updated_order, default=str)
        }

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"Cannot edit Order {order_id}. Make sure it exists and status is PLACED."
                })
            }
        logger.exception(f"DynamoDB ClientError: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}

    except Exception as e:
        logger.exception(f"Unexpected error editing order: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}


def lambda_handler(event, context):
    return app.resolve(event, context)
