import boto3
import pytest
import requests
import json
import jwt
import uuid

new_order_id = ""
new_order =  {
      "restaurantId": 200,
      "orderId": str(uuid.uuid4()),
      "orderItems": [
          {
              "name": "Pasta Carbonara",
              "price": 14.99,
              "id": 123,
              "quantity": 1
          }
      ],
      "totalAmount": 14.99
  }


def auth_header(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

# @pytest.mark.skip(reason="Admin auth failing")
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

# @pytest.mark.skip(reason="Admin auth failing")
def test_access_to_the_users_without_authentication(global_config):
    response = requests.get(global_config["ApiUrl"] + 'users')
    assert response.status_code == 401

# @pytest.mark.skip(reason="Admin auth failing")
def test_get_list_of_orders_by_regular_user(global_config):
    response = requests.get(
        global_config["ApiUrl"] + 'orders',
        headers=auth_header(global_config["regularUserIdToken"])
    )
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    assert response.status_code == 200

# @pytest.mark.skip(reason="Admin auth failing")
def test_create_order_by_regular_user(global_config):
    response = requests.post(
        global_config["ApiUrl"] + 'orders',
        data=json.dumps(new_order),
        headers=auth_header(global_config["regularUserIdToken"])
    )
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    assert response.status_code == 200

# @pytest.mark.skip(reason="Admin auth failing")
def test_create_order_by_administrative_user(global_config):
    global new_order_id
    
    decoded_admin = jwt.decode(global_config["adminUserIdToken"], options={"verify_signature": False})
    print(f"Decoded admin token: {json.dumps(decoded_admin, indent=2)}")
    
    response = requests.post(
        global_config["ApiUrl"] + 'orders',
        data=json.dumps(new_order),
        headers={
            "Authorization": f"Bearer {global_config['adminUserIdToken']}",
            "Content-Type": "application/json"
        }
    )

    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    print(f"Response body: {response.text}")
    
    if response.status_code != 200:
        print(f"ERROR: Expected 200 but got {response.status_code}")
        print("This suggests the admin authorization is failing")
        
    assert response.status_code == 200
    data = response.json()
    print(f"Response JSON parsed: {json.dumps(data, indent=2)}") 


    assert data['orderId'] is not None
    
    new_order_id = data['orderId']
    print(f"Created order with ID: {new_order_id}")

# @pytest.mark.skip(reason="Admin auth failing")
def test_deny_post_invalid_order(global_config):
    new_invalid_order = {"invalid_field": "test"} 
    
    response = requests.post(
        global_config["ApiUrl"] + 'orders',
        data=json.dumps(new_invalid_order),
        headers=auth_header(global_config["adminUserIdToken"])
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    data = response.json()
    
    print(f"Parsed JSON: {json.dumps(data, indent=2)}")
    
    assert data["statusCode"] == 400
    assert "Missing key: restaurantId" in data["body"]

# @pytest.mark.skip(reason="Admin auth failing")
def test_get_order_by_regular_user(global_config):
    if not new_order_id:
        pytest.skip("No order created to test with")
    
    response = requests.get(
        global_config["ApiUrl"] + f'orders/{new_order_id}',
        headers=auth_header(global_config["regularUserIdToken"])
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    print(f"Trying to access order ID: {new_order_id}")
    

    assert response.status_code == 200

