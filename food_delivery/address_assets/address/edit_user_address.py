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

def extract_user_id_from_event(event):
    """Helper function to extract userId from various event formats"""
    try:
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        

        if isinstance(authorizer, dict):
            if 'userId' in authorizer:
                return authorizer['userId']
            
  
            claims = authorizer.get('claims', {})
            if isinstance(claims, str):
                try:
                    claims = json.loads(claims)
                except:
                    pass
            
            if isinstance(claims, dict) and 'sub' in claims:
                return claims['sub']
        
        return None
    except Exception as e:
        logger.error(f"Error extracting userId: {e}")
        return None

@tracer.capture_method
def edit_user_address(event, addressId):
    try:
        userId = extract_user_id_from_event(event)
        
        if not userId:
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Unauthorized"}),
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                }
            }

        body_str = event.get('body', '{}')
        if not body_str:
            body_str = '{}'
        data = json.loads(body_str)
        

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
        
    
        update_expression = "SET updatedAt = :updatedAt"
        expression_values = {
            ":updatedAt": datetime.utcnow().isoformat()
        }
        expression_names = {}
        
    
        updatable_fields = [
            "addressLine1", "addressLine2", "city", "state", 
            "zipCode", "country", "isDefault", "label"
        ]
        
        for field in updatable_fields:
            if field in data:
                if field == "state":
                    update_expression += f", #state = :{field}"
                    expression_names["#state"] = "state"
                else:
                    update_expression += f", {field} = :{field}"
                expression_values[f":{field}"] = data[field]
        
        
        update_params = {
            "Key": {
                "userId": userId,
                "addressId": addressId
            },
            "UpdateExpression": update_expression,
            "ExpressionAttributeValues": expression_values,
            "ReturnValues": "ALL_NEW"
        }
        

        if expression_names:
            update_params["ExpressionAttributeNames"] = expression_names
            
        response = table.update_item(**update_params)
        
        updated_address = response["Attributes"]
        

        try:
            publish_address_event("Updated", userId, addressId, updated_address)
        except Exception as event_error:
            logger.warning(f"Failed to publish event: {event_error}")
        
        return {
            "statusCode": 200,
            "body": json.dumps(updated_address, cls=DecimalEncoder),
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
        logger.error(f"Error updating address: {str(e)}")
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
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        path_parameters = event.get('pathParameters') or {}
        
        if http_method == 'PUT' and path.startswith('/addresses/'):
            address_id = path_parameters.get('addressId')
            if address_id:
                return edit_user_address(event, address_id)
        
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