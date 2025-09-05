import os
import json
import time
import urllib.request
from jose import jwk, jwt
from jose.utils import base64url_decode

# Environment variables
USER_POOL_ID = os.getenv("USER_POOL_ID")
APP_CLIENT_ID = os.getenv("APPLICATION_CLIENT_ID")
ADMIN_GROUP_NAME = os.getenv("ADMIN_GROUP_NAME")

keys = {}
is_cold_start = True

def get_cognito_keys(region):
    global keys, is_cold_start
    if is_cold_start:
        url = f"https://cognito-idp.{region}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
        with urllib.request.urlopen(url) as f:
            keys = json.loads(f.read().decode("utf-8"))["keys"]
        is_cold_start = False
    return keys

def validate_token(token, region):
    keys = get_cognito_keys(region)
    headers = jwt.get_unverified_headers(token)
    kid = headers["kid"]

    # Find the matching public key
    key = next((k for k in keys if k["kid"] == kid), None)
    if not key:
        raise Exception("Invalid token: no matching key")

    public_key = jwk.construct(key)

    # Verify signature
    message, encoded_sig = token.rsplit(".", 1)
    decoded_sig = base64url_decode(encoded_sig.encode("utf-8"))
    if not public_key.verify(message.encode("utf-8"), decoded_sig):
        raise Exception("Invalid token signature")

    claims = jwt.get_unverified_claims(token)

    # Expiration check
    if time.time() > claims["exp"]:
        raise Exception("Token expired")

    # Audience check
    if claims["aud"] != APP_CLIENT_ID:
        raise Exception("Wrong audience")

    return claims

def generate_policy(principal_id, effect, resource):
    return {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": resource
                }
            ]
        }
    }

def lambda_handler(event, context):
    # Extract API Gateway info
    region = event["methodArn"].split(":")[3]
    token = event["authorizationToken"]

    # Validate token
    claims = validate_token(token, region)
    principal_id = claims["sub"]

    # Base permissions (user can only access their own resource)
    resources = [
        f"{event['methodArn'].rsplit('/', 1)[0]}/GET/users/{principal_id}",
        f"{event['methodArn'].rsplit('/', 1)[0]}/PUT/users/{principal_id}",
        f"{event['methodArn'].rsplit('/', 1)[0]}/DELETE/users/{principal_id}",
    ]

    # If user is in admin group → allow access to everything under /users
    if "cognito:groups" in claims and ADMIN_GROUP_NAME in claims["cognito:groups"]:
        resources.append(f"{event['methodArn'].rsplit('/', 1)[0]}/*")

    # Build allow policy
    return generate_policy(principal_id, "Allow", resources)






















