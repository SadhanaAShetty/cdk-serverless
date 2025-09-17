import os
import sys
import pytest
from unittest.mock import patch, MagicMock


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

@patch.dict(os.environ, {
    "USER_POOL_ID": "mock-pool",
    "APPLICATION_CLIENT_ID": "mock-client",
    "ADMIN_GROUP_NAME": "admin"
})
def test_autherize_lambda_runs(monkeypatch):
    from assets import autherize

    fake_token = "fake.jwt.token"
    fake_claims = {"sub": "user-123", "aud": "mock-client", "exp": 9999999999}

    
    dummy_key = {"kid": "fake-kid"}
    monkeypatch.setattr(autherize, "get_cognito_keys", lambda region: [dummy_key])
    
   
    monkeypatch.setattr(autherize.jwt, "get_unverified_headers", lambda t: {"kid": "fake-kid"})
    monkeypatch.setattr(autherize.jwt, "get_unverified_claims", lambda t: fake_claims)
    
  
    monkeypatch.setattr(autherize.jwk, "construct", lambda key: MagicMock(verify=lambda msg, sig: True))
    
  
    monkeypatch.setattr(autherize, "base64url_decode", lambda x: b"decoded")

    event = {"authorizationToken": fake_token, "methodArn": "arn:aws:execute-api:region:account:api/*/GET/users"}
    result = autherize.lambda_handler(event, None)

    assert result["principalId"] == "user-123"
    assert "policyDocument" in result
    assert result["policyDocument"]["Statement"][0]["Effect"] == "Allow"
