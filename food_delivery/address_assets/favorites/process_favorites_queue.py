import os
import json
from datetime import datetime
import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.batch import BatchProcessor, EventType, process_partial_response
from aws_lambda_powertools.utilities.data_classes.sqs_event import SQSRecord

logger = Logger(service=os.getenv("POWERTOOLS_SERVICE_NAME", "food-delivery-favorites"))
tracer = Tracer()

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

processor = BatchProcessor(event_type=EventType.SQS)

@tracer.capture_method
def record_handler(record: SQSRecord):
    """Process a single SQS message"""
    logger.info(f"Processing record: {record.message_id}")
    
    try:
        payload = json.loads(record.body)
        
        action = payload.get('action')
        user_id = payload.get('userId')
        
        if not user_id or not action:
            raise ValueError("Missing userId or action in message")
        
        if action == 'ADD':
            favorite_data = payload.get('favoriteData', {})
            favorite_id = favorite_data.get('favoriteId')
            
            if not favorite_id:
                raise ValueError("Missing favoriteId in ADD message")
            
            item = {
                'userId': user_id,
                'favoriteId': favorite_id,
                'type': favorite_data.get('type', ''),
                'name': favorite_data.get('name', ''),
                'restaurantId': favorite_data.get('restaurantId', ''),
                'dishId': favorite_data.get('dishId', ''),
                'description': favorite_data.get('description', ''),
                'imageUrl': favorite_data.get('imageUrl', ''),
                'createdAt': datetime.utcnow().isoformat()
            }
            
            # Use condition to prevent duplicate favorites
            table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(userId) AND attribute_not_exists(favoriteId)"
            )
            logger.info(f"Added favorite: {favorite_id} for user {user_id}")
            
        elif action == 'REMOVE':
            favorite_id = payload.get('favoriteId')
            
            if not favorite_id:
                raise ValueError("Missing favoriteId in REMOVE message")
            
            table.delete_item(
                Key={
                    'userId': user_id,
                    'favoriteId': favorite_id
                }
            )
            logger.info(f"Removed favorite: {favorite_id} for user {user_id}")
        
        else:
            raise ValueError(f"Unknown action: {action}")
            
    except Exception as e:
        logger.error(f"Error processing record {record.message_id}: {str(e)}")
        raise

@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """Process SQS messages in batch"""
    logger.info(f"Processing {len(event['Records'])} records from SQS")
    
    return process_partial_response(
        event=event,
        record_handler=record_handler,
        processor=processor,
        context=context
    )