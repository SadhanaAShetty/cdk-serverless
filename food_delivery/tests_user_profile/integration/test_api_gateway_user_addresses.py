import pytest
import json
import uuid


class TestAddressAPI:

    @pytest.fixture(autouse=True)
    def setup(self, mock_environment_variables, address_table, event_bus):
        """Setup test environment."""
        self.table = address_table
        self.event_bus = event_bus

    def test_add_address_success(self, api_gateway_event, lambda_context, mock_cognito_claims, sample_address_data):
        from address_assets.address.add_user_address import lambda_handler
        
        event = api_gateway_event(
            http_method="POST",
            path="/addresses",
            body=sample_address_data,
            claims=mock_cognito_claims
        )
        
        response = lambda_handler(event, lambda_context)
        
        assert response["statusCode"] == 201
        body = json.loads(response["body"]) 
        assert body["userId"] == mock_cognito_claims["sub"]
        assert body["addressLine1"] == sample_address_data["addressLine1"]
        assert body["city"] == sample_address_data["city"]
        assert "addressId" in body
        assert "createdAt" in body

    def test_add_address_missing_required_field(self, api_gateway_event, lambda_context, mock_cognito_claims):
        from address_assets.address.add_user_address import lambda_handler
        
        incomplete_data = {
            "addressLine1": "123 Main Street",
            "city": "New York"
        }
        
        event = api_gateway_event(
            http_method="POST",
            path="/addresses",
            body=incomplete_data,
            claims=mock_cognito_claims
        )
        
        response = lambda_handler(event, lambda_context)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        assert "Missing required field" in body["error"]

    def test_add_address_unauthorized(self, api_gateway_event, lambda_context, sample_address_data):
        from address_assets.address.add_user_address import lambda_handler
        
        event = api_gateway_event(
            http_method="POST",
            path="/addresses",
            body=sample_address_data,
            claims={}  # No claims
        )
        
        response = lambda_handler(event, lambda_context)
        
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert body["error"] == "Unauthorized"

    def test_list_addresses_success(self, api_gateway_event, lambda_context, mock_cognito_claims):
        from address_assets.address.list_user_addresses import lambda_handler
        
        user_id = mock_cognito_claims["sub"]
        test_addresses = [
            {
                "userId": user_id,
                "addressId": str(uuid.uuid4()),
                "addressLine1": "123 Main St",
                "city": "New York",
                "state": "NY",
                "zipCode": "10001",
                "country": "USA",
                "createdAt": "2024-01-01T00:00:00Z"
            },
            {
                "userId": user_id,
                "addressId": str(uuid.uuid4()),
                "addressLine1": "456 Oak Ave",
                "city": "Boston",
                "state": "MA",
                "zipCode": "02101",
                "country": "USA",
                "createdAt": "2024-01-02T00:00:00Z"
            }
        ]
        
        for address in test_addresses:
            self.table.put_item(Item=address)
        
        event = api_gateway_event(
            http_method="GET",
            path="/addresses",
            claims=mock_cognito_claims
        )
        
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "addresses" in body
        assert len(body["addresses"]) == 2
        assert body["addresses"][0]["createdAt"] == "2024-01-02T00:00:00Z"

    def test_list_addresses_empty(self, api_gateway_event, lambda_context, mock_cognito_claims):
        from address_assets.address.list_user_addresses import lambda_handler
        
        event = api_gateway_event(
            http_method="GET",
            path="/addresses",
            claims=mock_cognito_claims
        )
        
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "addresses" in body
        assert body["addresses"] == []

    def test_edit_address_success(self, api_gateway_event, lambda_context, mock_cognito_claims):
        from address_assets.address.edit_user_address import lambda_handler
        
        user_id = mock_cognito_claims["sub"]
        address_id = str(uuid.uuid4())
        existing_address = {
            "userId": user_id,
            "addressId": address_id,
            "addressLine1": "123 Main St",
            "city": "New York",
            "state": "NY",
            "zipCode": "10001",
            "country": "USA",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z"
        }
        self.table.put_item(Item=existing_address)
        
        update_data = {
            "addressLine1": "456 Updated Street",
            "city": "Boston",
            "state": "MA"
        }
        
        event = api_gateway_event(
            http_method="PUT",
            path=f"/addresses/{address_id}",
            body=update_data,
            path_parameters={"addressId": address_id},
            claims=mock_cognito_claims
        )
        
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["addressLine1"] == "456 Updated Street"
        assert body["city"] == "Boston"
        assert body["state"] == "MA"
        assert body["zipCode"] == "10001"
        assert body["updatedAt"] != existing_address["updatedAt"]

    def test_edit_address_not_found(self, api_gateway_event, lambda_context, mock_cognito_claims):
        from address_assets.address.edit_user_address import lambda_handler
        
        non_existent_id = str(uuid.uuid4())
        update_data = {"addressLine1": "Updated Street"}
        
        event = api_gateway_event(
            http_method="PUT",
            path=f"/addresses/{non_existent_id}",
            body=update_data,
            path_parameters={"addressId": non_existent_id},
            claims=mock_cognito_claims
        )
        
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["error"] == "Address not found"

    def test_delete_address_success(self, api_gateway_event, lambda_context, mock_cognito_claims):
        from address_assets.address.delete_user_address import lambda_handler
        
        user_id = mock_cognito_claims["sub"]
        address_id = str(uuid.uuid4())
        existing_address = {
            "userId": user_id,
            "addressId": address_id,
            "addressLine1": "123 Main St",
            "city": "New York",
            "state": "NY",
            "zipCode": "10001",
            "country": "USA"
        }
        self.table.put_item(Item=existing_address)
        
        event = api_gateway_event(
            http_method="DELETE",
            path=f"/addresses/{address_id}",
            path_parameters={"addressId": address_id},
            claims=mock_cognito_claims
        )
        
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 204

      
        db_response = self.table.get_item(Key={"userId": user_id, "addressId": address_id})
        assert "Item" not in db_response

    def test_delete_address_not_found(self, api_gateway_event, lambda_context, mock_cognito_claims):
        from address_assets.address.delete_user_address import lambda_handler
        
        non_existent_id = str(uuid.uuid4())
        
        event = api_gateway_event(
            http_method="DELETE",
            path=f"/addresses/{non_existent_id}",
            path_parameters={"addressId": non_existent_id},
            claims=mock_cognito_claims
        )
        
        response = lambda_handler(event, lambda_context)
        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["error"] == "Address not found"
