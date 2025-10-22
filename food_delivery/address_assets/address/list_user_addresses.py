import os
import json
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler.api_gateway import Response

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["ADDRESS_TABLE_NAME"])


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


@tracer.capture_method
@app.get("/addresses")
def list_user_addresses():
    user_id = app.current_event.request_context.authorizer.claims.get("sub")
    if not user_id:
        return Response(
            status_code=401,
            content_type="application/json",
            body=json.dumps({"error": "Unauthorized"})
        )

    response = table.query(KeyConditionExpression=Key("userId").eq(user_id))
    addresses = response.get("Items", [])
    addresses.sort(key=lambda x: x.get("createdAt", ""), reverse=True)

    return Response(
        status_code=200,
        content_type="application/json",
        body=json.dumps({"addresses": addresses}, cls=DecimalEncoder)
    )


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)
