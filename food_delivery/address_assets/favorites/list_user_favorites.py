import os
import json
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler.api_gateway import Response

logger = Logger(service=os.getenv("POWERTOOLS_SERVICE_NAME", "favorites-service"))
tracer = Tracer()
app = APIGatewayRestResolver()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


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
def list_user_favorites(event):
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

        response = table.query(KeyConditionExpression=Key("userId").eq(userId))
        favorites = response.get("Items", [])
        favorites.sort(key=lambda x: x.get("createdAt", ""), reverse=True)

        logger.info(f"Found {len(favorites)} favorites for user {userId}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({"favorites": favorites, "count": len(favorites)}, cls=DecimalEncoder),
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        }

    except Exception as e:
        logger.error(f"Error listing favorites: {e}")
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
        
        if http_method == 'GET' and path == '/favorites':
            return list_user_favorites(event)
        else:
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
