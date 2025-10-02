import os
import json
import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


@tracer.capture_method
@app.get("/orders/{orderId}")
def get_order_handler():
    try:

        authorizer = getattr(app.current_event.request_context, 'authorizer', {})
        userId = None
        

        if hasattr(authorizer, 'claims') and authorizer.claims:
            userId = authorizer.claims.get("sub")
        elif hasattr(authorizer, 'userId'):
            userId = authorizer.userId
        elif isinstance(authorizer, dict):
            userId = authorizer.get('userId')
        
        logger.info(f"Get order - Authorizer context: {authorizer}")
        logger.info(f"Get order - Extracted userId: {userId}")
        
        if not userId:
            return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}
            
        orderId = app.current_event.path_parameters["orderId"]
        
        response = table.get_item(Key={"userId": userId, "orderId": orderId})
        
        if "Item" not in response:
            return {"statusCode": 404, "body": json.dumps({"error": "Order not found"})}
            
        order = response["Item"]
        return {"statusCode": 200, "body": json.dumps(order, default=str)}
        
    except Exception as e:
        logger.exception(f"Error retrieving order: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}


def lambda_handler(event, context):
    try:
        return app.resolve(event, context)
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}
