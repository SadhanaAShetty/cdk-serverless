import boto3
import os
import json
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler import APIGatewayRestResolver


logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()

TABLE_NAME = os.environ["address_table"]
dynamodb = boto3.resource("dynamodb")
table = dynamodb.YABLE(TABLE_NAME)


@tracer.capture_method
@app.post("/address")
def create_order():
    logger.info("Inside add user address handler")
    data = app.current_event.json_body

    required_keys = ["house_no","street","city","province"]
    for key in required_keys:
        if key not in required_keys:
            return{
                "statusCode":400,
                "body":json.dumps({"error":f"Missing Key:{key}"}),
            }
    item_to_store ={
        "house_no":data["house_no"],
        "street" : data["street"],
        "city" :data["city"],
        "province" :data["province"]
    }
    try:
        table.put_item(
            Item = item_to_store,
            ConditionExpression="attribute_not_exists(user_id) AND attribute_not_exists(address_id)",
            )
        return{
            "statusCode":200,
            "body":json.dumps(item_to_store)
        }
    except Exception as e:
        logger.error(f"Error adding address:{str(e)}")
        return{
            "statusCode":500,
            "body":json.dumps({"error":"Internal Server Error"}),

        }
        


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    
