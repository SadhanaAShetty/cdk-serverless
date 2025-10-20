# src/api/favorites/list_user_favorites.py
import os
import json
import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service=os.getenv("POWERTOOLS_SERVICE_NAME", "serverless-workshop"))
tracer = Tracer()

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """
    List all favorite restaurants for a user
    """
    logger.info("Listing user favorites", extra={"event": event})
    
    try:
        # Get user_id from Cognito authorizer
        user_id = event['requestContext']['authorizer']['claims']['sub']
        
        # Query DynamoDB for all favorites for this user
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id)
        )
        
        favorites = response.get('Items', [])
        
        logger.info(f"Found {len(favorites)} favorites for user {user_id}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'favorites': favorites,
                'count': len(favorites)
            })
        }
        
    except KeyError as e:
        logger.error(f"Missing key: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Missing required field: {str(e)}'})
        }
    except Exception as e:
        logger.exception("Error listing favorites")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }


# src/api/favorites/process_favorites_queue.py
import os
import json
import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.batch import BatchProcessor, EventType, process_partial_response
from aws_lambda_powertools.utilities.data_classes.sqs_event import SQSRecord

logger = Logger(service=os.getenv("POWERTOOLS_SERVICE_NAME", "serverless-workshop"))
tracer = Tracer()

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

processor = BatchProcessor(event_type=EventType.SQS)


@tracer.capture_method
def record_handler(record: SQSRecord):
    """
    Process a single SQS message
    """
    logger.info(f"Processing record: {record.message_id}")
    
    # Parse the message body
    payload = json.loads(record.body)
    
    user_id = payload.get('userId') or payload.get('user_id')
    restaurant_id = payload.get('restaurantId') or payload.get('restaurant_id')
    action = payload.get('action', 'add')  # 'add' or 'remove'
    
    if not user_id or not restaurant_id:
        raise ValueError("Missing userId or restaurantId in message")
    
    if action == 'add':
        # Add favorite
        item = {
            'user_id': user_id,
            'restaurant_id': restaurant_id,
            'restaurant_name': payload.get('restaurantName', ''),
            'added_at': payload.get('timestamp', '')
        }
        
        table.put_item(Item=item)
        logger.info(f"Added favorite: {restaurant_id} for user {user_id}")
        
    elif action == 'remove':
        # Remove favorite
        table.delete_item(
            Key={
                'user_id': user_id,
                'restaurant_id': restaurant_id
            }
        )
        logger.info(f"Removed favorite: {restaurant_id} for user {user_id}")
    
    else:
        raise ValueError(f"Unknown action: {action}")


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """
    Process SQS messages in batch
    """
    logger.info(f"Processing {len(event['Records'])} records from SQS")
    
    return process_partial_response(
        event=event,
        record_handler=record_handler,
        processor=processor,
        context=context
    )