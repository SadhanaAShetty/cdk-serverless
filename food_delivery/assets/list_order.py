import os
import json
from decimal import Decimal
import boto3
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
def list_orders_handler():
    try:
        # Extract userId from authorizer claims
        authorizer = getattr(app.current_event.request_context, 'authorizer', None)
        claims = getattr(authorizer, 'claims', {}) if authorizer else {}
        userId = claims.get("sub")
        
        if not userId:
            return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}

        response = table.query(KeyConditionExpression=Key("userId").eq(userId))
        orders = response.get("Items", [])
        
        return {
            "statusCode": 200,
            "body": json.dumps({"orders": orders}, cls=DecimalEncoder)
        }

    except Exception as e:
        logger.exception(f"Error listing orders: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}


def lambda_handler(event, context):
    try:
        return app.resolve(event, context)
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}