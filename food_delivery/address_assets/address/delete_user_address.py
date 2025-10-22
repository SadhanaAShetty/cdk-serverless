import os
import json
from datetime import datetime
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()

dynamodb = boto3.resource("dynamodb")
eventbridge = boto3.client("events")
table = dynamodb.Table(os.environ["ADDRESS_TABLE_NAME"])
event_bus_name = os.environ.get("EVENT_BUS_NAME")

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

@tracer.capture_method
def publish_address_event(event_type, user_id, address_id, address_data):
    """Publish address event to EventBridge"""
    if not event_bus_name:
        logger.warning("EVENT_BUS_NAME not configured, skipping event publishing")
        return None
        
    try:
        event_detail = {
            "userId": user_id,
            "addressId": address_id,
            "eventType": event_type,
            "address": address_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = eventbridge.put_events(
            Entries=[
                {
                    'Source': 'food-delivery.address',
                    'DetailType': f'Address {event_type}',
                    'Detail': json.dumps(event_detail),
                    'EventBusName': event_bus_name
                }
            ]
        )
        logger.info(f"Published {event_type} event for address {address_id}", extra={"response": response})
        return response
    except Exception as e:
        logger.error(f"Failed to publish {event_type} event: {str(e)}")
        return None

@tracer.capture_method
def delete_user_address(event, addressId):
    try:
        # Get user ID from authorizer
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        claims = authorizer.get('claims', {})
        userId = claims.get("sub")
        
        if not userId:
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Unauthorized"}),
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                }
            }

        # Get the address before deleting for event publishing
        existing_response = table.get_item(
            Key={
                "userId": userId,
                "addressId": addressId
            }
        )
        
        if "Item" not in existing_response:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Address not found"}),
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                }
            }
        
        address_to_delete = existing_response["Item"]
        
        # Delete the address
        table.delete_item(
            Key={
                "userId": userId,
                "addressId": addressId
            }
        )
        
        # Publish event to EventBridge
        publish_address_event("Deleted", userId, addressId, address_to_delete)
        
        return {
            "statusCode": 204,
            "body": "",
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        }

    except ClientError as e:
        logger.error(f"DynamoDB error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Database error"}),
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        }
    except Exception as e:
        logger.error(f"Error deleting address: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"}),
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        }

@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    logger.debug(f"Incoming event: {json.dumps(event)}")
    
    try:
        # Route based on HTTP method and path
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        path_parameters = event.get('pathParameters') or {}
        
        if http_method == 'DELETE' and path.startswith('/addresses/'):
            address_id = path_parameters.get('addressId')
            if address_id:
                return delete_user_address(event, address_id)
        
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Not Found"}),
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        }
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"}),
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        }