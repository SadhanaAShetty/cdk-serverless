import os
import json
import time
import urllib.request
from jose import jwk, jwt
from jose.utils import base64url_decode

USER_POOL_ID = os.getenv("USER_POOL_ID")
APP_CLIENT_ID = os.getenv("APPLICATION_CLIENT_ID")
ADMIN_GROUP_NAME = os.getenv("ADMIN_GROUP_NAME")

keys = {}
is_cold_start = True

def get_cognito_keys(region):
    global keys, is_cold_start
    if is_cold_start:
        url = f"https://cognito-idp.{region}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
        print("Fetching JWKS from:", url)
        with urllib.request.urlopen(url) as f:
            keys = json.loads(f.read().decode("utf-8"))["keys"]
        is_cold_start = False
    return keys

def validate_token(token, region):
    print("Validating token:", token[:50] + "..." if len(token) > 50 else token)
    keys = get_cognito_keys(region)
    headers = jwt.get_unverified_headers(token)
    kid = headers.get("kid")
    key = next((k for k in keys if k["kid"] == kid), None)
    if not key:
        raise Exception("Invalid token: no matching key")

    public_key = jwk.construct(key)
    message, encoded_sig = token.rsplit(".", 1)
    decoded_sig = base64url_decode(encoded_sig.encode("utf-8"))
    if not public_key.verify(message.encode("utf-8"), decoded_sig):
        raise Exception("Invalid token signature")

    claims = jwt.get_unverified_claims(token)
    if time.time() > claims.get("exp", 0):
        raise Exception("Token expired")
    if claims.get("aud") != APP_CLIENT_ID:
        raise Exception("Wrong audience")
    return claims

def generate_policy(principal_id, effect, resources, context=None):
    if isinstance(resources, str):
        resources = [resources]
    
    policy = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "execute-api:Invoke",
                "Effect": effect,
                "Resource": resources
            }]
        }
    }
    
    if context:
        policy["context"] = context
        
    return policy

def lambda_handler(event, context):
    print(f"Method ARN: {event['methodArn']}")
    print(f"Expected admin group: '{ADMIN_GROUP_NAME}'")
    
    token = event.get("authorizationToken", "")
    if token.lower().startswith("bearer "):
        token = token.split(" ")[1]
    
    region = event["methodArn"].split(":")[3]
    
    try:
        claims = validate_token(token, region)
    except Exception as e:
        print(f"Token validation failed: {e}")
        raise Exception("Unauthorized")
    
    principal_id = claims.get("sub")
    user_groups = claims.get('cognito:groups', [])
    
    print(f"Principal ID: {principal_id}")
    print(f"User groups from token: {user_groups}")
    
    is_admin = isinstance(user_groups, list) and ADMIN_GROUP_NAME in user_groups
    print(f"Is admin result: {is_admin}")
    

    arn_parts = event['methodArn'].split(':')
    api_gateway_arn = arn_parts[5] 
    api_id, stage_name, _ = api_gateway_arn.split('/', 2)
    base_arn = f"arn:aws:execute-api:{region}:{arn_parts[4]}:{api_id}/{stage_name}"
    print(f"Base ARN: {base_arn}")
    
    user_context = {
        "userId": principal_id,
        "groups": json.dumps(user_groups) if user_groups else "[]",
        "isAdmin": str(is_admin).lower()
    }
    
    if is_admin:
        admin_resources = [f"{base_arn}/*"]
        print(f"Admin resources: {admin_resources}")
        return generate_policy(principal_id, "Allow", admin_resources, user_context)
    else:
        regular_resources = [
            f"{base_arn}/GET/users/{principal_id}",
            f"{base_arn}/PUT/users/{principal_id}",
            f"{base_arn}/DELETE/users/{principal_id}",
        ]
        print(f"Regular user resources: {regular_resources}")
        return generate_policy(principal_id, "Allow", regular_resources, user_context)
