import os
import json
import time
import urllib.request
from jose import jwk, jwt
from jose.utils import base64url_decode

user_pool_id = os.getenv('USER_POOL_ID')
app_client_id = os.getenv('APPLICATION_CLIENT_ID')
admin_group_name = os.getenv('ADMIN_GROUP_NAME')
keys = None

def get_jwks(region):
    global keys
    if keys is None:
        url = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json'
        with urllib.request.urlopen(url) as f:
            response = f.read()
        keys = json.loads(response.decode())['keys']
    return keys

def validate_token(token, region):
    keys = get_jwks(region)
    headers = jwt.get_unverified_headers(token)
    kid = headers['kid']
    key = next((k for k in keys if k['kid'] == kid), None)
    if not key:
        print('Public key not found')
        return None
    public_key = jwk.construct(key)
    message, encoded_sig = token.rsplit('.', 1)
    decoded_sig = base64url_decode(encoded_sig.encode())
    if not public_key.verify(message.encode(), decoded_sig):
        print('Signature verification failed')
        return None
    claims = jwt.get_unverified_claims(token)
    if time.time() > claims['exp']:
        print('Token expired')
        return None
    if claims['aud'] != app_client_id:
        print('Invalid audience')
        return None
    return jwt.decode(token, key, audience=app_client_id)

def generate_policy(principal_id, effect, resource):
    return {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "execute-api:Invoke",
                "Effect": effect,
                "Resource": resource
            }]
        }
    }

def lambda_handler(event, context):
    region = event['methodArn'].split(':')[3]
    resource = event['methodArn']
    token = event['authorizationToken']
    decoded_token = validate_token(token, region)
    if not decoded_token:
        raise Exception('Unauthorized')
    principal_id = decoded_token['sub']
    user_resource = resource.rsplit('/', 1)[0] + f"/users/{principal_id}/*"
    if 'cognito:groups' in decoded_token and admin_group_name in decoded_token['cognito:groups']:
        return generate_policy(principal_id, 'Allow', resource + '/*')
    else:
        return generate_policy(principal_id, 'Allow', user_resource)
