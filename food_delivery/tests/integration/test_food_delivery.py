import boto3
import pytest
import requests
import json

new_user_id = ""
new_user = {"name": "John Doe"}


def test_cognito_users_created(global_config):
    idp_client = boto3.client("cognito-idp")
    for username in [global_config["regularUserName"], global_config["adminUserName"]]:
        resp = idp_client.admin_get_user(
            UserPoolId=global_config["UserPool"],
            Username=username
        )
        assert any(
            attr['Name'] == 'email' and attr['Value'] == username
            for attr in resp['UserAttributes']
        ), f"Cognito user {username} not found or email mismatch"


def test_access_to_the_users_without_authentication(global_config):
    response = requests.get(global_config["ApiUrl"] + '/users')
    assert response.status_code == 401


def test_get_list_of_users_by_regular_user(global_config):
    response = requests.get(
        global_config["ApiUrl"] + '/users',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 403


def test_deny_post_user_by_regular_user(global_config):
    response = requests.post(
        global_config["ApiUrl"] + '/users',
        data=json.dumps(new_user),
        headers={
            'Authorization': global_config["regularUserIdToken"],
            'Content-Type': 'application/json'
        }
    )
    assert response.status_code == 403


def test_allow_post_user_by_administrative_user(global_config):
    response = requests.post(
        global_config["ApiUrl"] + '/users',
        data=json.dumps(new_user),
        headers={
            'Authorization': global_config["adminUserIdToken"],
            'Content-Type': 'application/json'
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data['name'] == new_user['name']

    global new_user_id
    new_user_id = data['userid']


def test_deny_post_invalid_user(global_config):
    new_invalid_user = {"name": "John Doe"}
    response = requests.post(
        global_config["ApiUrl"] + '/users',
        data=json.dumps(new_invalid_user),
        headers={
            'Authorization': global_config["adminUserIdToken"],
            'Content-Type': 'application/json'
        }
    )
    assert response.status_code == 400


def test_get_user_by_regular_user(global_config):
    response = requests.get(
        global_config["ApiUrl"] + f'/users/{new_user_id}',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 403
