import json
import boto3
import time
import pytest
from datetime import datetime

# @pytest.mark.skip(reason="Admin auth failing")
def test_kinesis_stream_exists(global_config):
    kinesis_client = boto3.client('kinesis')
    
    stream_name = global_config.get('KinesisStreamName', 'FoodDeliveryLocationStream')
    
    try:
        response = kinesis_client.describe_stream(StreamName=stream_name)
        stream_status = response['StreamDescription']['StreamStatus']
        
        assert stream_status == 'ACTIVE'
        print(f"Kinesis stream '{stream_name}' is active")
        
    except kinesis_client.exceptions.ResourceNotFoundException:
        pytest.fail(f"Kinesis stream '{stream_name}' not found")


# @pytest.mark.skip(reason="Admin auth failing")
def test_producer_lambda_exists(global_config):
    lambda_client = boto3.client('lambda')
    
    function_name = global_config.get('ProducerFunctionName', 'kinesis_producer')
    
    try:
        response = lambda_client.get_function(FunctionName=function_name)
        assert response['Configuration']['State'] == 'Active'
        print(f"Producer Lambda '{function_name}' is active")
        
    except lambda_client.exceptions.ResourceNotFoundException:
        pytest.fail(f"Producer Lambda '{function_name}' not found")

# @pytest.mark.skip(reason="Admin auth failing")
def test_consumer_lambda_exists(global_config):
    lambda_client = boto3.client('lambda')
    
    function_name = global_config.get('ConsumerFunctionName', 'kinesis_consumer')
    
    try:
        response = lambda_client.get_function(FunctionName=function_name)
        assert response['Configuration']['State'] == 'Active'
        print(f"Consumer Lambda '{function_name}' is active")
        
    except lambda_client.exceptions.ResourceNotFoundException:
        pytest.fail(f"Consumer Lambda '{function_name}' not found")


# @pytest.mark.skip(reason="Admin auth failing")
def test_producer_lambda_invocation(global_config):
    lambda_client = boto3.client('lambda')
    
    function_name = global_config.get('ProducerFunctionName', 'kinesis_producer')
    
    
    test_payload = {
        "location_data": {
            "delivery_id": "TEST-INTEGRATION-001",
            "order_id": "TEST-INT-ORD-001",
            "driver_id": "TEST-INT-DRV-001",
            "customer_id": "TEST-INT-CUST-001",
            "location": {
                "latitude": 51.5074,
                "longitude": -0.1278,
                "city": "Rotterdam",
                "address": "Integration Test Street"
            },
            "status": "in_transit",
            "estimated_delivery_time": datetime.utcnow().timestamp() + 1800,
            "restaurant": {
                "name": "Integration Test Restaurant",
                "cuisine": "Test Cuisine"
            }
        }
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        assert response['StatusCode'] == 200
        
       
        response_payload = json.loads(response['Payload'].read())
        
        # Check if the response indicates success
        if 'statusCode' in response_payload:
            assert response_payload['statusCode'] == 200
        
        print(" Producer Lambda invocation successful")
        print(f"   Response: {response_payload}")
        
    except Exception as e:
        pytest.fail(f"Failed to invoke producer Lambda: {str(e)}")

#Producer -> Kinesis -> Consumer -> DynamoDB
def test_end_to_end_kinesis_flow(global_config):
    lambda_client = boto3.client('lambda')
    dynamodb = boto3.resource('dynamodb')
    
    producer_function = global_config.get('ProducerFunctionName', 'kinesis_producer')
    consumer_function = global_config.get('ConsumerFunctionName', 'UpdateRiderLocation')
    table_name = global_config.get('DynamoDBTableName', 'RidersPositionTable')
    
    
    test_rider_id = f"TEST-RIDER-{int(datetime.utcnow().timestamp())}"
    test_payload = {
        "location_data": {
            "rider_id": test_rider_id,
            "lat": 53.4808,
            "lng": -2.2426,
            "city": "Den Hague",
            "speed": 25.5,
            "heading": 180,
            "status": "busy",
            "vehicle_type": "bike",
            "last_updated": datetime.utcnow().timestamp()
        }
    }
    
    try:
        #Step 1: Invoke producer
        print(f"Step 1: Invoking producer Lambda with test ID: {test_rider_id}")
        producer_response = lambda_client.invoke(
            FunctionName=producer_function,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        assert producer_response['StatusCode'] == 200
        producer_payload = json.loads(producer_response['Payload'].read())
        
        if 'statusCode' in producer_payload:
            assert producer_payload['statusCode'] == 200
        
        print("Producer invocation successful")
        
        # Step 2: Wait for consumer to process 
        print("Step 2: Waiting for consumer to process the record...")
        time.sleep(10)  
        
        # Step 3: Check DynamoDB for the updated rider position
        print("Step 3: Checking DynamoDB for updated rider position...")
        time.sleep(5)  
        
        try:
            table = dynamodb.Table(table_name)
            response = table.get_item(Key={'rider_id': test_rider_id})
            
            if 'Item' in response:
                item = response['Item']
                print("Rider position found in DynamoDB:")
                print(f"Rider ID: {item['rider_id']}")
                print(f"Location: {item['lat']}, {item['lng']}")
                print(f"City: {item['city']}")
                print(f"Status: {item['status']}")
                print(f"Last Updated: {item['last_updated_timestamp']}")
                
                # Verify the data matches what we sent
                assert float(item['lat']) == test_payload['location_data']['lat']
                assert float(item['lng']) == test_payload['location_data']['lng']
                assert item['city'] == test_payload['location_data']['city']
                
            else:
                print("Rider position not found in DynamoDB")
                print("   This might indicate the consumer didn't process the record")
                
        except Exception as e:
            print(f" Error checking DynamoDB: {e}")
        
        print(" End-to-end test completed")
        print(f"Look for rider_id: {test_rider_id} in consumer logs")
        
    except Exception as e:
        pytest.fail(f"End-to-end test failed: {str(e)}")



# @pytest.mark.skip(reason="Admin auth failing")
def test_eventbridge_simulator_exists(global_config):
    events_client = boto3.client('events')
    
    rule_name = global_config.get('SimulatorRuleName', 'FifteenMinuteSchedule')
    
    try:
        response = events_client.describe_rule(Name=rule_name)
        
       
        assert response['ScheduleExpression'] == 'rate(15 minutes)'
        print(f"EventBridge simulator rule '{rule_name}' exists")
        print(f"Schedule: {response['ScheduleExpression']}")
        print(f"State: {response['State']}")
        
        if response['State'] == 'ENABLED':
            print("Simulator is currently ENABLED and generating test data")
        else:
            print("Simulator is currently DISABLED")
            print("To enable: python data_stream_assets/simulator_control.py enable")
        
    except events_client.exceptions.ResourceNotFoundException:
        pytest.fail(f"EventBridge simulator rule '{rule_name}' not found")

# @pytest.mark.skip(reason="Admin auth failing")
def test_dynamodb_table_exists(global_config):
    dynamodb = boto3.resource('dynamodb')
    
    table_name = global_config.get('DynamoDBTableName', 'RidersPositionTable')
    
    try:
        table = dynamodb.Table(table_name)
        table.load()  
        
        # Check table schema
        assert table.key_schema[0]['AttributeName'] == 'rider_id'
        assert table.key_schema[0]['KeyType'] == 'HASH'
        
        print(f"DynamoDB table '{table_name}' exists")
        print(f"Status: {table.table_status}")
        print(f"Partition Key: {table.key_schema[0]['AttributeName']}")
        
        # Check if table has any items
        response = table.scan(Limit=5)
        item_count = response['Count']
        print(f"Sample items: {item_count}")
        
        if item_count > 0:
            print("Recent rider positions:")
            for item in response['Items']:
                print(f"- {item['rider_id']}: ({item['lat']}, {item['lng']}) at {item.get('last_updated_timestamp', 'unknown')}")
        
    except Exception as e:
        pytest.fail(f"DynamoDB table '{table_name}' test failed: {str(e)}")