import json
import os
import boto3
import uuid
import pytest
from moto import mock_dynamodb
from contextlib import contextmanager
from unittest.mock import patch

USERS_MOCK_TABLE_NAME = 'Users'
UUID_MOCK_VALUE_JOHN = 'f8216640-91a2-11eb-8ab9-57aa454facef'
UUID_MOCK_VALUE_JANE = '31a9f940-917b-11eb-9054-67837e2c40b0'
UUID_MOCK_VALUE_NEW_USER = 'new-user-guid'


BASE_DIR = os.path.dirname(__file__)


def mock_uuid():
    return UUID_MOCK_VALUE_NEW_USER


@contextmanager
def my_test_environment():
    with mock_dynamodb():
        set_up_dynamodb()
        put_data_dynamodb()
        yield


def set_up_dynamodb():
    conn = boto3.client('dynamodb')
    conn.create_table(
        TableName=USERS_MOCK_TABLE_NAME,
        KeySchema=[{'AttributeName': 'user_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'user_id', 'AttributeType': 'S'}],
        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
    )


def put_data_dynamodb():
    conn = boto3.client('dynamodb')
    conn.put_item(
        TableName=USERS_MOCK_TABLE_NAME,
        Item={
            'user_id': {'S': UUID_MOCK_VALUE_JOHN},
            'name': {'S': 'John Doe'},
            'time_stamp': {'S': '2021-03-30T21:57:49.860Z'}
        }
    )
    conn.put_item(
        TableName=USERS_MOCK_TABLE_NAME,
        Item={
            'user_id': {'S': UUID_MOCK_VALUE_JANE},
            'name': {'S': 'Jane Doe'},
            'time_stamp': {'S': '2021-03-30T17:13:06.516Z'}
        }
    )



# @pytest.mark.skip("skip")
@patch.dict(os.environ, {'TABLE_NAME': USERS_MOCK_TABLE_NAME, 'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR'})
def test_get_list_of_users():
    with my_test_environment():
        from food_delivery.assets import user
        event_file = os.path.join(BASE_DIR, 'events', 'event-get-all-users.json')
        with open(event_file, 'r') as f:
            apigw_get_all_users_event = json.load(f)

        expected_response = [
            {'userid': UUID_MOCK_VALUE_JOHN, 'name': 'John Doe', 'timestamp': '2021-03-30T21:57:49.860Z'},
            {'userid': UUID_MOCK_VALUE_JANE, 'name': 'Jane Doe', 'timestamp': '2021-03-30T17:13:06.516Z'}
        ]

        ret = user.lambda_handler(apigw_get_all_users_event, '')
        print("Lambda returned:", ret)
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])

        if isinstance(data, dict) and "body" in data:
            inner = data["body"]
            if isinstance(inner, str):
                try:
                    data = json.loads(inner)
                except json.JSONDecodeError:
                    import ast
                    data = ast.literal_eval(inner)
            else:
                data = inner
        assert data == expected_response

@patch.dict(os.environ, {'TABLE_NAME': USERS_MOCK_TABLE_NAME, 'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR'})
def test_get_single_user():
    with my_test_environment():
        from food_delivery.assets import user
        event_file = os.path.join(BASE_DIR, 'events', 'event-get-user-by-id.json')
        with open(event_file, 'r') as f:
            apigw_event = json.load(f)
        apigw_event['pathParameters'] = {"userid": 'f8216640-91a2-11eb-8ab9-57aa454facef'}

        expected_response = {
            'userid': UUID_MOCK_VALUE_JOHN,
            'name': 'John Doe',
            'timestamp': '2021-03-30T21:57:49.860Z'
        }
        ret = user.lambda_handler(apigw_event, '')
        print("Lambda returned:", ret)
        assert ret['statusCode'] == 200
        outer_body = ret['body']
        if isinstance(outer_body, str):
            outer_body = json.loads(outer_body)

       
        inner_body = outer_body.get('body', outer_body)
        if isinstance(inner_body, str):
            inner_body = json.loads(inner_body)

        data = inner_body
        print("Parsed data:", data)

        assert outer_body== expected_response
        data = json.loads(ret['body'])
        assert data == expected_response


        

@pytest.mark.skip("skip")
def test_get_single_user_wrong_id():
    with my_test_environment():
        from food_delivery.assets import user
        event_file = os.path.join(BASE_DIR, 'events', 'event-get-user-by-id.json')
        with open(event_file, 'r') as f:
            apigw_event = json.load(f)
            apigw_event['pathParameters']['user_id'] = '123456789'
            apigw_event['rawPath'] = '/users/123456789'

        ret = user.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        assert json.loads(ret['body']) == {}


@patch('uuid.uuid1', mock_uuid)
@pytest.mark.skip("skip")
@pytest.mark.freeze_time('2001-01-01')
def test_add_user():
    with my_test_environment():
        from food_delivery.assets import user
        event_file = os.path.join(BASE_DIR, 'events', 'event-post-user.json')
        with open(event_file, 'r') as f:
            apigw_event = json.load(f)

        expected_response = json.loads(apigw_event['body'])
        ret = user.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data['user_id'] == UUID_MOCK_VALUE_NEW_USER
        assert data['timestamp'] == '2001-01-01T00:00:00'
        assert data['name'] == expected_response['name']


@pytest.mark.freeze_time('2001-01-01')
@pytest.mark.skip("skip")
def test_add_user_with_id():
    with my_test_environment():
        from food_delivery.assets import user
        event_file = os.path.join(BASE_DIR, 'events', 'event-post-user.json')
        with open(event_file, 'r') as f:
            apigw_event = json.load(f)

        expected_response = json.loads(apigw_event['body'])
        apigw_event['body'] = apigw_event['body'].replace('}', ', "user_id":"123456789"}')

        ret = user.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data['user_id'] == '123456789'
        assert data['timestamp'] == '2001-01-01T00:00:00'
        assert data['name'] == expected_response['name']

@pytest.mark.skip("skip")
def test_delete_user():
    with my_test_environment():
        from food_delivery.assets import user
        event_file = os.path.join(BASE_DIR, 'events', 'event-delete-user-by-id.json')
        with open(event_file, 'r') as f:
            apigw_event = json.load(f)

        ret = user.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        assert json.loads(ret['body']) == {}
