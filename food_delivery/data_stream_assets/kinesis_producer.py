import os
import json
import boto3
import uuid
import random
from datetime import datetime
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext


logger = Logger(service="kinesis_producer")
tracer = Tracer(service="kinesis_producer")


kinesis_client = boto3.client('kinesis')
STREAM_NAME = os.environ.get('KINESIS_STREAM_NAME', 'FoodDeliveryLocationStream')


#lambda fn to produce message to kinesis stream
@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    try:
        logger.info(f"Received event: {event}")
        
        
        if 'body' in event:
            # API Gateway event
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            #Direct invocation or other event sources
            body = event
        
        #Check if this is from EventBridge simulator
        is_simulator = body.get('simulator', False)
        
        #Generate sample delivery location data if not provided
        if is_simulator:
            location_data = generate_vehicle_location_data()  
        else:
            location_data = body.get('location_data', generate_sample_location_data())
        
        # Add metadata
        kinesis_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_id': str(uuid.uuid4()),
            'source': 'eventbridge_simulator' if is_simulator else 'food_delivery_service',
            'data': location_data
        }
        
        logger.info(f"Sending record to Kinesis: {kinesis_record}")
        
        # Send record to Kinesis
        partition_key = location_data.get('rider_id') or location_data.get('delivery_id') or str(uuid.uuid4())
        response = kinesis_client.put_record(
            StreamName=STREAM_NAME,
            Data=json.dumps(kinesis_record),
            PartitionKey=partition_key
        )
        
        logger.info(f"Successfully sent record to Kinesis. Shard ID: {response['ShardId']}, Sequence Number: {response['SequenceNumber']}")
        
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Successfully sent data to Kinesis',
                'shard_id': response['ShardId'],
                'sequence_number': response['SequenceNumber'],
                'record_id': kinesis_record['event_id']
            })
        }
        
    except Exception as e:
        logger.exception(f"Error sending data to Kinesis: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to send data to Kinesis',
                'details': str(e)
            })
        }
#generate sample delivery location
def generate_sample_location_data():
    locations = [
        {'city': 'Amsterdam', 'lat': 51.5074, 'lng': -0.1278},
        {'city': 'Rotterdam', 'lat': 53.4808, 'lng': -2.2426},
        {'city': 'Den Hague', 'lat': 52.4862, 'lng': -1.8904},
        {'city': 'Eindhoven', 'lat': 53.4084, 'lng': -2.9916},
        {'city': 'Delft', 'lat': 53.8008, 'lng': -1.5491}
    ]
    
    location = random.choice(locations)
    
    return {
        'delivery_id': f"DEL-{uuid.uuid4().hex[:8].upper()}",
        'order_id': f"ORD-{uuid.uuid4().hex[:8].upper()}",
        'driver_id': f"DRV-{uuid.uuid4().hex[:6].upper()}",
        'customer_id': f"CUST-{uuid.uuid4().hex[:6].upper()}",
        'location': {
            'latitude': round(location['lat'] + random.uniform(-0.1, 0.1), 6),
            'longitude': round(location['lng'] + random.uniform(-0.1, 0.1), 6),
            'city': location['city'],
            'address': f"{random.randint(1, 999)} {random.choice(['High Street', 'Main Road', 'Church Lane', 'Victoria Street'])}"
        },
        'status': random.choice(['picked_up', 'in_transit', 'delivered', 'delayed']),
        'estimated_delivery_time': (datetime.utcnow().timestamp() + random.randint(600, 3600)), 
        'restaurant': {
            'name': random.choice(['Pizza Palace', 'Burger Barn', 'Sushi Spot', 'Curry Corner', 'Taco Town']),
            'cuisine': random.choice(['Italian', 'American', 'Japanese', 'Indian', 'Mexican'])
        }
    }
#generate sample vehicle location data
def generate_vehicle_location_data():
    locations = [
        {'city': 'London', 'lat': 51.5074, 'lng': -0.1278},
        {'city': 'Manchester', 'lat': 53.4808, 'lng': -2.2426},
        {'city': 'Birmingham', 'lat': 52.4862, 'lng': -1.8904},
        {'city': 'Liverpool', 'lat': 53.4084, 'lng': -2.9916},
        {'city': 'Leeds', 'lat': 53.8008, 'lng': -1.5491}
    ]
    
    location = random.choice(locations)
    
    return {
        'rider_id': f"RIDER-{random.randint(1, 100):03d}",  
        'lat': round(location['lat'] + random.uniform(-0.05, 0.05), 6),
        'lng': round(location['lng'] + random.uniform(-0.05, 0.05), 6),
        'city': location['city'],
        'speed': round(random.uniform(0, 60), 1),
        'heading': random.randint(0, 359),  
        'status': random.choice(['available', 'busy', 'offline']),
        'vehicle_type': random.choice(['bike', 'scooter', 'car']),
        'last_updated': datetime.utcnow().timestamp()
    }