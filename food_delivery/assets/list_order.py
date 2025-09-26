import os
import json
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


@tracer.capture_method
@app.get("/orders")
def list_orders():
    try:
        authorizer = getattr(app.current_event.request_context, 'authorizer', None)
        claims = getattr(authorizer, 'claims', {}) if authorizer else {}
        userId = claims.get("sub") if claims else None
        
        if not userId:
            return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}

        response = table.query(
            KeyConditionExpression=Key("userId").eq(userId)
        )
        orders = response.get("Items", [])
        logger.info(f"Retrieved {len(orders)} orders for user {userId}")
        return {
            "statusCode": 200,
            "body": json.dumps({"orders": orders}, cls=DecimalEncoder)
        }

    except Exception as e:
        logger.exception(f"Error listing orders for user {userId}: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }

def lambda_handler(event, context):
    if (event.get("httpMethod") == "GET" and event.get("path") == "/orders" and 
        "requestContext" in event and "authorizer" in event["requestContext"]):
        return handle_list_orders_direct(event, context)
    
    try:
        return app.resolve(event, context)
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }

def handle_list_orders_direct(event, context):
    try:
        request_context = event.get("requestContext", {})
        authorizer = request_context.get("authorizer", {})
        claims = authorizer.get("claims", {})
        userId = claims.get("sub")
        
        if not userId:
            return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}


        dynamodb = boto3.resource("dynamodb", region_name='us-east-1')
        test_table = dynamodb.Table(os.environ["TABLE_NAME"])
        
        response = test_table.query(
            KeyConditionExpression=Key("userId").eq(userId)
        )
        orders = response.get("Items", [])
        logger.info(f"Retrieved {len(orders)} orders for user {userId}")
        return {
            "statusCode": 200,
            "body": json.dumps({"orders": orders}, cls=DecimalEncoder)
        }

    except Exception as e:
        logger.exception(f"Error listing orders for user {userId}: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }
