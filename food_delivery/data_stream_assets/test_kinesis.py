"""
Test script for Kinesis Data Streams functionality
This script can be used to test the producer Lambda function
"""

import json
import boto3
import time
from datetime import datetime

#test the Kinesis producer Lambda function
def test_kinesis_producer():
    lambda_client = boto3.client('lambda')
    
    #sample test data
    test_events = [
        {
            "location_data": {
                "delivery_id": "TEST-DEL-001",
                "order_id": "TEST-ORD-001",
                "driver_id": "TEST-DRV-001",
                "customer_id": "TEST-CUST-001",
                "location": {
                    "latitude": 51.5074,
                    "longitude": -0.1278,
                    "city": "Rotterdam",
                    "address": "123 Test Street"
                },
                "status": "in_transit",
                "estimated_delivery_time": datetime.utcnow().timestamp() + 1800,
                "restaurant": {
                    "name": "Test Restaurant",
                    "cuisine": "Test Cuisine"
                }
            }
        },
        {
            "location_data": {
                "delivery_id": "TEST-DEL-002",
                "order_id": "TEST-ORD-002",
                "driver_id": "TEST-DRV-002",
                "customer_id": "TEST-CUST-002",
                "location": {
                    "latitude": 53.4808,
                    "longitude": -2.2426,
                    "city": "Amsterdam",
                    "address": "456 Test Avenue"
                },
                "status": "delayed",
                "estimated_delivery_time": datetime.utcnow().timestamp() - 300,
                "restaurant": {
                    "name": "Another Test Restaurant",
                    "cuisine": "Another Test Cuisine"
                }
            }
        }
    ]
    
    print("Testing Kinesis Producer Lambda...")
    
    for i, test_event in enumerate(test_events, 1):
        try:
            print(f"\nSending test event {i}...")
            
            #invoke the producer Lambda
            response = lambda_client.invoke(
                FunctionName='kinesis_producer',
                InvocationType='RequestResponse',
                Payload=json.dumps(test_event)
            )
            
            response_payload = json.loads(response['Payload'].read())
            
            if response['StatusCode'] == 200:
                print(f" Test event {i} sent successfully!")
                print(f" Response: {response_payload}")
            else:
                print(f" Test event {i} failed!")
                print(f"   Response: {response_payload}")
                
        except Exception as e:
            print(f" Error sending test event {i}: {str(e)}")
        

        time.sleep(2)
    
    print("\n" + "="*50)
    print("Test completed!")
    print("Check CloudWatch logs for the consumer Lambda to see processed records.")
    print("Consumer function name: kinesis_consumer")

#Test putting records directly to Kinesis stream
def test_direct_kinesis_put():
    kinesis_client = boto3.client('kinesis')
    stream_name = 'FoodDeliveryLocationStream'
    
    print(f"Testing direct Kinesis put to stream: {stream_name}")
    
    test_record = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_id": "DIRECT-TEST-001",
        "source": "direct_test",
        "data": {
            "delivery_id": "DIRECT-DEL-001",
            "order_id": "DIRECT-ORD-001",
            "status": "picked_up",
            "location": {
                "latitude": 52.4862,
                "longitude": -1.8904,
                "city": "Birmingham",
                "address": "789 Direct Test Road"
            }
        }
    }
    
    try:
        response = kinesis_client.put_record(
            StreamName=stream_name,
            Data=json.dumps(test_record),
            PartitionKey=test_record['data']['delivery_id']
        )
        
        print(" Direct record sent successfully!")
        print(f"   Shard ID: {response['ShardId']}")
        print(f"   Sequence Number: {response['SequenceNumber']}")
        
    except Exception as e:
        print(f" Error sending direct record: {str(e)}")

if __name__ == "__main__":
    print("Kinesis Data Streams Test Script")
    print("="*40)
    
    #Test 1: Producer Lambda
    test_kinesis_producer()
    
    print("\n" + "="*50)
    
    #Test 2: Direct Kinesis put
    test_direct_kinesis_put()
    
    print("\nDone! Check CloudWatch logs for detailed processing information.")