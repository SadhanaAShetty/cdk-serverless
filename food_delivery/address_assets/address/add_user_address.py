import os
import uuid
import json
from datetime import datetime
from decimal import Decimal
import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from http import HTTPStatus
from aws_lambda_powertools.event_handler.api_gateway import Response

logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

dynamodb = boto3.resource("dynamodb")
eventbridge = boto3.client("events")
table = dynamodb.Table(os.environ["ADDRESS_TABLE_NAME"])
event_bus_name = os.environ.get("EVENT_BUS_NAME")


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


@tracer.capture_method
def publish_address_event(event_type, user_id, address_id, address_data):
    if not event_bus_name:
        logger.warning("EVENT_BUS_NAME not configured, skipping event publishing")
        return None

    try:
        event_detail = {
            "userId": user_id,
            "addressId": address_id,
            "eventType": event_type,
            "address": address_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        response = eventbridge.put_events(
            Entries=[
                {
                    "Source": "food-delivery.address",
                    "DetailType": f"Address {event_type}",
                    "Detail": json.dumps(event_detail),
                    "EventBusName": event_bus_name,
                }
            ]
        )
        logger.info(
            f"Published {event_type} event for address {address_id}",
            extra={"response": response},
        )
        return response
    except Exception as e:
        logger.error(f"Failed to publish {event_type} event: {str(e)}")
        return None




@app.post("/addresses")
def add_user_address():
    try:
        userId = app.current_event.request_context.authorizer.claims.get("sub")
        if not userId:
            return Response(
                status_code=HTTPStatus.UNAUTHORIZED,
                content_type="application/json",
                body=json.dumps({"error": "Unauthorized"})
            )

        data = app.current_event.json_body
        required_fields = ["addressLine1", "city", "state", "zipCode", "country"]

        for field in required_fields:
            if field not in data or not data[field]:
                return Response(
                    status_code=HTTPStatus.BAD_REQUEST,
                    content_type="application/json",
                    body=json.dumps({"error": f"Missing required field: {field}"})
                )

        address_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        address_item = {
            "userId": userId,
            "addressId": address_id,
            "addressLine1": data["addressLine1"],
            "addressLine2": data.get("addressLine2", ""),
            "city": data["city"],
            "state": data["state"],
            "zipCode": data["zipCode"],
            "country": data["country"],
            "isDefault": data.get("isDefault", False),
            "label": data.get("label", ""),
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }

        table.put_item(Item=address_item)
        publish_address_event("Created", userId, address_id, address_item)

        return Response(
            status_code=HTTPStatus.CREATED,
            content_type="application/json",
            body=json.dumps(address_item, cls=DecimalEncoder)
        )

    except Exception as e:
        logger.error(f"Error adding address: {str(e)}")
        return Response(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            content_type="application/json",
            body=json.dumps({"error": "Internal Server Error"})
        )



@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    logger.debug(f"Incoming event: {json.dumps(event)}")

    try:
        return app.resolve(event, context)
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"}),
        }
