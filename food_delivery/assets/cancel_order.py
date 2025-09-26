import os
import json
import time
from datetime import datetime
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


@tracer.capture_method
@app.delete("/orders/{orderId}")
def cancel_order_handler():
    try:
        authorizer = getattr(app.current_event.request_context, 'authorizer', None)
        claims = getattr(authorizer, 'claims', {}) if authorizer else {}
        userId = claims.get("sub")
        
        if not userId:
            return {"statusCode": 401, "body": json.dumps({"error": "User not authenticated"})}
            
        orderId = app.current_event.path_parameters["orderId"]
        current_time = time.time()

        response = table.update_item(
            Key={"userId": userId, "orderId": orderId},
            UpdateExpression="SET #status = :new_status, canceledAt = :canceled_time",
            ConditionExpression="(#status = :current_status) AND (orderTime > :minOrderTime)",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":current_status": "PLACED",
                ":new_status": "CANCELED",
                ":minOrderTime": Decimal(str(current_time - 600)), 
                ":canceled_time": datetime.utcnow().isoformat()
            },
            ReturnValues="ALL_NEW"
        )
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Order {orderId} successfully canceled",
                "order": response["Attributes"]
            }, default=str) 
        }

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"Order {orderId} cannot be canceled. Status must be PLACED and within 10 minutes of creation."
                })
            }
        logger.exception(f"DynamoDB ClientError: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}


def lambda_handler(event, context):
    try:
        return app.resolve(event, context)
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}