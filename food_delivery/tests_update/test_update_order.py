import json
import boto3
import datetime
import time
from decimal import Decimal


def test_initial_order_status_in_dynamodb(global_config, capsys):
    """Test that the initial order is stored correctly in DynamoDB"""
    dynamodb = boto3.resource('dynamodb')
    table_name = global_config.get('UsersTableOutput') or global_config.get('OrdersTablenameOutput') or 'UserOrdersTable'
    table = dynamodb.Table(table_name)
    
    order = global_config['order']
    user_id = global_config['regularUserSub']
    order_id = order['data']['orderId']
    
    print(f"Checking initial order status in DynamoDB for userId: {user_id}, orderId: {order_id}")
    
   
    response = table.get_item(Key={'userId': user_id, 'orderId': order_id})
    
    assert 'Item' in response, "Order should exist in DynamoDB"
    
    stored_order = response['Item']
    assert stored_order['data']['status'] == 'PLACED', "Initial status should be PLACED"
    assert stored_order['data']['orderId'] == order_id
    assert stored_order['data']['userId'] == user_id
    
    print(f"Initial order status verified: {stored_order['data']['status']}")


def test_order_update_via_eventbridge(global_config, capsys):
    """Test the complete order update flow: EventBridge → Lambda → DynamoDB"""
    
    order = global_config['order'].copy()
    order['data']['status'] = 'IN-PROCESS'
    
    eb_client = boto3.client('events')
    print(f"Publishing EventBridge event to update order status to: IN-PROCESS")
    
    response = eb_client.put_events(
        Entries=[
            {
                'Time': datetime.datetime.now(),
                'Source': 'restaurant',
                'DetailType': 'order.updated',
                'EventBusName': global_config['RestaurantBusName'],
                'Detail': json.dumps(order),
            }
        ]
    )
    
    assert response['FailedEntryCount'] == 0, "EventBridge event should be published successfully"
    print(f" EventBridge event published successfully")
    

    print("Waiting for Lambda to process the EventBridge event...")
    time.sleep(5)  
    
 
    dynamodb = boto3.resource('dynamodb')
    table_name = global_config.get('UsersTableOutput') or global_config.get('OrdersTablenameOutput') or 'UserOrdersTable'
    table = dynamodb.Table(table_name)
    
    user_id = global_config['regularUserSub']
    order_id = order['data']['orderId']
    
    print(f"Checking updated order status in DynamoDB for userId: {user_id}, orderId: {order_id}")
    
    response = table.get_item(Key={'userId': user_id, 'orderId': order_id})
    
    assert 'Item' in response, "Order should still exist in DynamoDB after update"
    
    updated_order = response['Item']
    print(f"Order status after EventBridge update: {updated_order['data']['status']}")
    
    assert updated_order['data']['status'] == 'IN-PROCESS', "Order status should be updated to IN-PROCESS"
    assert updated_order['data']['orderId'] == order_id
    assert updated_order['data']['userId'] == user_id
    
    print(f" Order status successfully updated via EventBridge: {updated_order['data']['status']}")


def test_multiple_status_updates(global_config, capsys):
    """Test multiple status updates to verify the update mechanism works reliably"""
    
    eb_client = boto3.client('events')
    dynamodb = boto3.resource('dynamodb')
    table_name = global_config.get('UsersTableOutput') or global_config.get('OrdersTablenameOutput') or 'UserOrdersTable'
    table = dynamodb.Table(table_name)
    
    user_id = global_config['regularUserSub']
    order_id = global_config['order']['data']['orderId']
    
   
    status_sequence = ['PREPARING', 'READY', 'OUT_FOR_DELIVERY', 'DELIVERED']
    
    for new_status in status_sequence:
        print(f"Updating order status to: {new_status}")
        
        
        order_update = global_config['order'].copy()
        order_update['data']['status'] = new_status
        
        
        response = eb_client.put_events(
            Entries=[
                {
                    'Time': datetime.datetime.now(),
                    'Source': 'restaurant',
                    'DetailType': 'order.updated',
                    'EventBusName': global_config['RestaurantBusName'],
                    'Detail': json.dumps(order_update),
                }
            ]
        )
        
        assert response['FailedEntryCount'] == 0, f"EventBridge event for {new_status} should be published successfully"
        
       
        time.sleep(3)
        
       
        response = table.get_item(Key={'userId': user_id, 'orderId': order_id})
        assert 'Item' in response, f"Order should exist after {new_status} update"
        
        updated_order = response['Item']
        assert updated_order['data']['status'] == new_status, f"Order status should be updated to {new_status}"
        
        print(f" Status successfully updated to: {new_status}")
    
    print(f" All status updates completed successfully")