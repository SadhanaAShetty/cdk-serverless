import os
import json
from decimal import Decimal
import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


@tracer.capture_method
@app.put("/orders/{orderId}")
def edit_order_handler():
    try:
        authorizer = getattr(app.current_event.request_context, 'authorizer', None)
        claims = getattr(authorizer, 'claims', {}) if authorizer else {}
        userId = claims.get("sub")
        
        if not userId:
            return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}
            
        orderId = app.current_event.path_parameters["orderId"]
        data = app.current_event.json_body
        
        existing_item = table.get_item(Key={"userId": userId, "orderId": orderId})
        
        if "Item" not in existing_item:
            return {"statusCode": 404, "body": json.dumps({"error": "Order not found"})}


        response = table.update_item(
            Key={"userId": userId, "orderId": orderId},
            UpdateExpression="SET restaurantId = :rid, totalAmount = :amount, orderItems = :items",
            ExpressionAttributeValues={
                ":rid": data.get("restaurantId"),
                ":amount": Decimal(str(data.get("totalAmount"))),
                ":items": data.get("orderItems"),
            },
            ReturnValues="ALL_NEW",
        )
        
        return {"statusCode": 200, "body": json.dumps(response["Attributes"], default=str)}
        
    except Exception as e:
        logger.exception(f"Error updating order: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}


def lambda_handler(event, context):
    try:
        return app.resolve(event, context)
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error"})}