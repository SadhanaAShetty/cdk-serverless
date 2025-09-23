import os
import uuid
import json
from datetime import datetime
from typing import List, Dict, Any
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
@app.put("/orders/{user_id}/{order_id}")
def update_order(user_id: str, order_id: str):
    data = app.current_event.json_body


    data["userId"] = user_id
    data["orderId"] = order_id

    ddb_item = {
        "orderId": order_id,
        "userId": user_id,
        "data": data
    }
    ddb_item = json.loads(json.dumps(ddb_item), parse_float=Decimal)

    try:
        table.put_item(
            Item=ddb_item,
            ConditionExpression="attribute_exists(order_id) AND attribute_exists(user_id) AND #data.#status = :status",
            ExpressionAttributeNames={
                "data": "data",
                "status": "status"
            },
            ExpressionAttributeValues={
                ":status": "PLACED"
            },
            ReturnValuesOnConditionCheckFailure="ALL_OLD"
        )

        logger.info(f"Order {order_id} updated successfully for user {user_id}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Order updated successfully",
                "order": data
            })
        }

    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"Cannot edit Order {order_id}. Please check if it exists and status is PLACED."
                })
            }
        else:
            logger.error(f"DynamoDB error: {exc}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Internal Server Error"})
            }

    except Exception as e:
        logger.error(f"Unexpected error updating order {order_id}: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }
    

def lambda_handler(event: dict, context):
    logger.info("Processing order management request", extra={"event": event})
    return app.resolve(event, context)