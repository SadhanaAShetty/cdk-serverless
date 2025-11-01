import os
import json
import base64
import boto3
import random
from datetime import datetime
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext


logger = Logger(service="kinesis_consumer")
tracer = Tracer(service="kinesis_consumer")


dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME')
table = dynamodb.Table(table_name)

#lambda to consume message
@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    try:
        logger.info(f"Received Kinesis event with {len(event['Records'])} records")
        
        processed_records = []
        failed_records = []
        
        for record in event['Records']:
            try:
                kinesis_data = record['kinesis']
                
                
                encoded_data = kinesis_data['data']
                decoded_data = base64.b64decode(encoded_data).decode('utf-8')
                record_data = json.loads(decoded_data)
                
                logger.info(f"Processing record: {record_data['event_id']}")
                
                # Process the delivery location data
                processed_record = process_delivery_location(record_data)
                processed_records.append(processed_record)
                
                # Update DynamoDB if this is rider location data
                if 'rider_id' in record_data['data']:
                    update_rider_position(record_data['data'])
                
                # Add Kinesis metadata
                processed_record['kinesis_metadata'] = {
                    'sequence_number': kinesis_data['sequenceNumber'],
                    'partition_key': kinesis_data['partitionKey'],
                    'shard_id': record['eventSourceARN'].split('/')[-1],
                    'approximate_arrival_timestamp': kinesis_data['approximateArrivalTimestamp']
                }
                
                logger.info(f"Successfully processed record: {processed_record['summary']}")
                
            except Exception as e:
                logger.error(f"Failed to process record: {str(e)}")
                failed_records.append({
                    'record': record,
                    'error': str(e)
                })
        
        
        logger.info(f"Processing complete. Successful: {len(processed_records)}, Failed: {len(failed_records)}")
        
       
        
        return {
            'statusCode': 200,
            'processed_count': len(processed_records),
            'failed_count': len(failed_records),
            'processed_records': processed_records[:5],  
            'batch_processing_time': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.exception(f"Error processing Kinesis records: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e)
        }

#process individual delivery location record
def process_delivery_location(record_data: dict) -> dict:
    try:
        data = record_data['data']
        
        # Extract key information
        delivery_id = data['delivery_id']
        order_id = data['order_id']
        status = data['status']
        location = data['location']
        
        # Perform analytics
        analytics = {
            'delivery_distance_estimate': calculate_delivery_distance(location),
            'delivery_zone': determine_delivery_zone(location),
            'priority_level': calculate_priority(data),
            'estimated_delay': calculate_estimated_delay(data)
        }
        
        # Generate alerts if needed
        alerts = generate_alerts(data, analytics)
        
        # Create processed record
        processed_record = {
            'event_id': record_data['event_id'],
            'timestamp': record_data['timestamp'],
            'delivery_id': delivery_id,
            'order_id': order_id,
            'status': status,
            'location': location,
            'analytics': analytics,
            'alerts': alerts,
            'summary': f"Delivery {delivery_id} is {status} in {location['city']}"
        }
        
        return processed_record
        
    except Exception as e:
        logger.error(f"Error processing delivery location: {str(e)}")
        raise

def calculate_delivery_distance(location: dict) -> float:
    return round(random.uniform(0.5, 15.0), 2) 

def determine_delivery_zone(location: dict) -> str:
    city = location.get('city', 'Unknown')
    
    
    zone_mapping = {
    'Amsterdam': 'Zone-West',
    'Rotterdam': 'Zone-Southwest',
    'The Hague': 'Zone-West',
    'Utrecht': 'Zone-Central',
    'Eindhoven': 'Zone-Southeast'
    }
    
    return zone_mapping.get(city, 'Zone-Other')

def calculate_priority(data: dict) -> str:
    status = data['status']
    estimated_time = data.get('estimated_delivery_time', 0)
    current_time = datetime.utcnow().timestamp()
    
    # High priority if delayed or overdue
    if status == 'delayed':
        return 'HIGH'
    elif estimated_time < current_time:
        return 'HIGH'
    elif status == 'in_transit':
        return 'MEDIUM'
    else:
        return 'LOW'


#calculate delay in minutes
def calculate_estimated_delay(data: dict) -> int:
    estimated_time = data.get('estimated_delivery_time', 0)
    current_time = datetime.utcnow().timestamp()
    
    if estimated_time < current_time:
        delay_seconds = current_time - estimated_time
        return int(delay_seconds / 60) 
    
    return 0

def generate_alerts(data: dict, analytics: dict) -> list:
    alerts = []
    
    #Alert for high priority deliveries
    if analytics['priority_level'] == 'HIGH':
        alerts.append({
            'type': 'HIGH_PRIORITY',
            'message': f"High priority delivery {data['delivery_id']} requires attention"
        })
    
    # Alert for delays
    if analytics['estimated_delay'] > 0:
        alerts.append({
            'type': 'DELIVERY_DELAY',
            'message': f"Delivery {data['delivery_id']} is delayed by {analytics['estimated_delay']} minutes"
        })
    
    # Alert for long distance deliveries
    if analytics['delivery_distance_estimate'] > 10:
        alerts.append({
            'type': 'LONG_DISTANCE',
            'message': f"Long distance delivery {data['delivery_id']} ({analytics['delivery_distance_estimate']} km)"
        })
    
    return alerts

#update rider position in dynamodb
def update_rider_position(rider_data: dict):
    try:
        rider_id = rider_data['rider_id']
        
        item = {
            'rider_id': rider_id,
            'lat': rider_data['lat'],
            'lng': rider_data['lng'],
            'city': rider_data.get('city', 'Unknown'),
            'speed': rider_data.get('speed', 0),
            'heading': rider_data.get('heading', 0),
            'status': rider_data.get('status', 'unknown'),
            'vehicle_type': rider_data.get('vehicle_type', 'unknown'),
            'last_updated_timestamp': int(datetime.utcnow().timestamp())
        }
        
        # Update DynamoDB
        table.put_item(Item=item)
        
        logger.info(f"Updated rider position for {rider_id}: lat={item['lat']}, lng={item['lng']}")
        
    except Exception as e:
        logger.error(f"Failed to update rider position: {str(e)}")
        raise