import boto3
import os
import pytest

DATA_STREAM_STACK_NAME = os.getenv("food_delivery_data_stream_stack", "FoodDeliveryDataStream")

def get_stack_outputs(stack_name):
    result = {}
    cf_client = boto3.client('cloudformation')
    
    try:
        cf_response = cf_client.describe_stacks(StackName=stack_name)
        outputs = cf_response["Stacks"][0]["Outputs"]
        
        for output in outputs:
            result[output["OutputKey"]] = output["OutputValue"]
            
        parameters = cf_response["Stacks"][0]["Parameters"]
        for parameter in parameters:
            result[parameter["ParameterKey"]] = parameter["ParameterValue"]
            
    except Exception as e:
        print(f"Warning: Could not get stack outputs for {stack_name}: {e}")
       
        result = {
            'KinesisStreamName': 'FoodDeliveryLocationStream',
            'ProducerFunctionName': 'kinesis_producer',
            'ConsumerFunctionName': 'kinesis_consumer'
        }
    
    return result

@pytest.fixture(scope='session')
def global_config(request):
    config = get_stack_outputs(DATA_STREAM_STACK_NAME)
    
    print("Data Stream Test Configuration:")
    print(f"Stream Name: {config.get('KinesisStreamName')}")
    print(f"Producer Function: {config.get('ProducerFunctionName')}")
    print(f"Consumer Function: {config.get('ConsumerFunctionName')}")
    
    yield config