import boto3
import os
import pytest
import time
import json
from datetime import datetime
from decimal import Decimal

APPLICATION_STACK_NAME = os.getenv("food_delivery_stack", "FoodDeliveryStack")
ORDERS_STACK_NAME = os.getenv("food_delivery_order_update_stack", "FoodDeliveryOrderUpdate")
CLIENT_ID = None 

globalConfig = {}

def load_test_order():
    user_id = globalConfig.get('regularUserSub')
    print(f"Creating test order with userId: {user_id}")
    
    test_order = {
        "data": {
            "orderId": "test-order-123",
            "userId": user_id, 
            "restaurantId": "restaurant-456",
            "totalAmount": 25.99,
            "orderItems": [
                {
                    "itemId": "item-1",
                    "name": "Margherita Pizza",
                    "quantity": 1,
                    "price": 15.99
                },
                {
                    "itemId": "item-2", 
                    "name": "Caesar Salad",
                    "quantity": 1,
                    "price": 10.00
                }
            ],
            "status": "PLACED",
            "orderTime": "2024-01-01T12:00:00Z"
        }
    }
    
    return test_order

def get_stack_outputs(stack_name):
    result = {}
    cf_client = boto3.client('cloudformation')
    cf_response = cf_client.describe_stacks(StackName=stack_name)
    outputs = cf_response["Stacks"][0]["Outputs"]
    for output in outputs:
        result[output["OutputKey"]] = output["OutputValue"]
    parameters = cf_response["Stacks"][0]["Parameters"]
    for parameter in parameters:
        result[parameter["ParameterKey"]] = parameter["ParameterValue"]

    return result


def create_cognito_accounts():
    result = {}
    sm_client = boto3.client('secretsmanager')
    idp_client = boto3.client('cognito-idp')
    sm_response = sm_client.get_random_password(
        ExcludeCharacters='"' '`[]{}():;,$/\\<>|=&', RequireEachIncludedType=True
    )
    result["regularUserName"] = "regularUser@example.com"
    result["regularUserPassword"] = sm_response["RandomPassword"]
    

    user_pool_id = globalConfig.get("UserPoolIdOutput") or globalConfig.get("UserPool")
    client_id = globalConfig.get("UserPoolClientIdOutput") or os.getenv('CLIENT_ID')
    
    if not user_pool_id:
        raise ValueError("UserPool ID not found in stack outputs. Check your stack configuration.")
    if not client_id:
        raise ValueError("Client ID not found in stack outputs. Check your stack configuration.")
    
    try:
        idp_client.admin_delete_user(
            UserPoolId=user_pool_id, Username=result["regularUserName"]
        )
    except idp_client.exceptions.UserNotFoundException:
        print('Regular user haven\'t been created previously')
    idp_response = idp_client.sign_up(
        ClientId=client_id,
        Username=result["regularUserName"],
        Password=result["regularUserPassword"],
        UserAttributes=[{"Name": "name", "Value": result["regularUserName"]}],
    )
    result["regularUserSub"] = idp_response["UserSub"]
    idp_client.admin_confirm_sign_up(
        UserPoolId=user_pool_id, Username=result["regularUserName"]
    )
 
    idp_response = idp_client.initiate_auth(
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': result["regularUserName"],
            'PASSWORD': result["regularUserPassword"],
        },
        ClientId=client_id,
    )
    result["regularUserIdToken"] = idp_response["AuthenticationResult"]["IdToken"]
    result["regularUserAccessToken"] = idp_response["AuthenticationResult"][
        "AccessToken"
    ]
    result["regularUserRefreshToken"] = idp_response["AuthenticationResult"][
        "RefreshToken"
    ]

    return result


def clear_dynamo_tables():
    dbd_client = boto3.client('dynamodb')
    
  
    table_name = globalConfig.get('UsersTableOutput') or globalConfig.get('OrdersTablenameOutput') or 'UserOrdersTable'
    
    db_response = dbd_client.scan(
        TableName=table_name, AttributesToGet=['orderId', 'userId']
    )

    for item in db_response["Items"]:
        dbd_client.delete_item(
            TableName=table_name,
            Key={
                'userId': {'S': globalConfig['regularUserSub']},
                'orderId': {'S': item['orderId']["S"]},
            },
        )
    return


def seed_dynamo_tables():
    
    dynamodb = boto3.resource('dynamodb')
    

    table_name = globalConfig.get('UsersTableOutput') or globalConfig.get('OrdersTablenameOutput') or 'UserOrdersTable'
    table = dynamodb.Table(table_name)
    
    print(f"Seeding DynamoDB table: {table_name}")
    
    test_order = globalConfig["order"]
    order_id = test_order["data"]['orderId']
    user_id = globalConfig['regularUserSub']
    
    print(f"Storing order {order_id} for user {user_id}")
    
    ddb_item = {
        'orderId': order_id,
        'userId': user_id,
        'data': {
            'orderId': order_id,
            'userId': user_id,
            'restaurantId': test_order["data"]["restaurantId"],
            'totalAmount': test_order["data"]["totalAmount"],
            'orderItems': test_order["data"]["orderItems"],
            'status': test_order["data"]['status'],
            'orderTime': test_order["data"]['orderTime']
        }
    }

    ddb_item = json.loads(json.dumps(ddb_item), parse_float=Decimal)
    
    print(f"DDB Item to store: {json.dumps(ddb_item, default=str)}")

    table.put_item(Item=ddb_item)
    print("Order stored successfully")
    

@pytest.fixture(scope='session')
def global_config(request):
    global globalConfig
    globalConfig.update(get_stack_outputs(APPLICATION_STACK_NAME))
    globalConfig.update(get_stack_outputs(ORDERS_STACK_NAME))
    
 
    if 'APIEndpointOutput' in globalConfig:
        globalConfig['OrdersServiceEndpoint'] = globalConfig['APIEndpointOutput']
    
 
    globalConfig.update(create_cognito_accounts())
    
 
    globalConfig['order'] = load_test_order()

    seed_dynamo_tables()
    yield globalConfig
    clear_dynamo_tables()




