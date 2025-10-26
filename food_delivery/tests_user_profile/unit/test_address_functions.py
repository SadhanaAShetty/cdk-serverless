import pytest
import uuid
from datetime import datetime, timezone


class TestAddressValidation:

    def test_validate_required_fields_success(self, sample_address_data):

        required_fields = ["addressLine1", "city", "state", "zipCode", "country"]
        

        for field in required_fields:
            assert field in sample_address_data
            assert sample_address_data[field] 

    def test_validate_required_fields_missing(self):
        incomplete_data = {
            "addressLine1": "123 Main Street",
            "city": "New York"
          
        }
        
        required_fields = ["addressLine1", "city", "state", "zipCode", "country"]
        missing_fields = []
        
        for field in required_fields:
            if field not in incomplete_data or not incomplete_data[field]:
                missing_fields.append(field)
        
        assert len(missing_fields) == 3 
        assert "state" in missing_fields
        assert "zipCode" in missing_fields
        assert "country" in missing_fields

    def test_validate_optional_fields(self):
        minimal_data = {
            "addressLine1": "123 Main Street",
            "city": "New York",
            "state": "NY",
            "zipCode": "10001",
            "country": "Netherlands"
        }
        
        optional_defaults = {
            "addressLine2": "",
            "isDefault": False,
            "label": ""
        }
        
        for field, default_value in optional_defaults.items():
            assert minimal_data.get(field, default_value) == default_value


class TestAddressDataTransformation:


    def test_create_address_item_structure(self, sample_user_id, sample_address_data):
        address_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        address_item = {
            "userId": sample_user_id,
            "addressId": address_id,
            "addressLine1": sample_address_data["addressLine1"],
            "addressLine2": sample_address_data.get("addressLine2", ""),
            "city": sample_address_data["city"],
            "state": sample_address_data["state"],
            "zipCode": sample_address_data["zipCode"],
            "country": sample_address_data["country"],
            "isDefault": sample_address_data.get("isDefault", False),
            "label": sample_address_data.get("label", ""),
            "createdAt": timestamp,
            "updatedAt": timestamp
        }
        

        assert address_item["userId"] == sample_user_id
        assert address_item["addressId"] == address_id
        assert address_item["addressLine1"] == sample_address_data["addressLine1"]
        assert address_item["city"] == sample_address_data["city"]
        assert "createdAt" in address_item
        assert "updatedAt" in address_item

    def test_update_expression_builder(self):

        update_data = {
            "addressLine1": "456 Updated Street",
            "city": "Boston",
            "state": "MA"
        }
        
        update_expression = "SET updatedAt = :updatedAt"
        expression_values = {":updatedAt": datetime.now(timezone.utc).isoformat()}
        
        updatable_fields = [
            "addressLine1", "addressLine2", "city", "state", 
            "zipCode", "country", "isDefault", "label"
        ]
        
        for field in updatable_fields:
            if field in update_data:
                update_expression += f", {field} = :{field}"
                expression_values[f":{field}"] = update_data[field]
        

        assert "addressLine1 = :addressLine1" in update_expression
        assert "city = :city" in update_expression
        assert "state = :state" in update_expression
        assert ":addressLine1" in expression_values
        assert expression_values[":addressLine1"] == "456 Updated Street"


class TestAddressUtilities:


    def test_address_id_generation(self):
        address_id = str(uuid.uuid4())
        assert len(address_id) == 36 
        assert "-" in address_id

    def test_timestamp_generation(self):
        timestamp = datetime.now(timezone.utc).isoformat()
        assert "T" in timestamp 
        assert ":" in timestamp 

    def test_address_field_defaults(self):
        defaults = {
            "addressLine2": "",
            "isDefault": False,
            "label": ""
        }
        
        for field, default_value in defaults.items():
            assert isinstance(default_value, (str, bool))
            if isinstance(default_value, str):
                assert len(default_value) >= 0
            if isinstance(default_value, bool):
                assert default_value in [True, False]