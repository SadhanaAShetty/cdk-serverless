from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import boto3
import os
import jwt
import requests
import random
import string

from jwt import PyJWKClient 
                             

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
table = dynamodb.Table("SecureNoteTable")

COGNITO_POOL_REGION = 'eu-west-1'
COGNITO_POOL_ID = 'eu-west-1_DqbcqJ1hS'
COGNITO_APP_CLIENT_ID = '5ckt2961bs3ded3f47bdjg0ucq'
COGNITO_ISSUER = f"https://cognito-idp.{COGNITO_POOL_REGION}.amazonaws.com/{COGNITO_POOL_ID}"
JWKS_URL = f"{COGNITO_ISSUER}/.well-known/jwks.json"
jwk_client = PyJWKClient(JWKS_URL)

def get_user_id_from_token(token: str) -> str:
    try:
        signing_key = jwk_client.get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=COGNITO_APP_CLIENT_ID,
            issuer=COGNITO_ISSUER
        )
        return payload["sub"] 
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token invalid: {str(e)}")


@app.post("/api/notes")
async def create_note(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    user_id = get_user_id_from_token(token)
    body = await request.json()
    content = body.get("content")

    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    def generate_note_id(length=5):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    note_id = generate_note_id()

    table.put_item(Item={
        "userId": user_id,
        "noteId": note_id,
        "content": content
    })

    return {"message": "Note saved", "noteId": note_id}


@app.get("/api/notes/{note_id}")
async def get_note(note_id: str, request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    user_id = get_user_id_from_token(token)

    response = table.get_item(Key={
        "userId": user_id,
        "noteId": note_id
    })

    item = response.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Note not found")

    return {"noteId": note_id, "content": item["content"]}
