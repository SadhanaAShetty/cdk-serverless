import boto3
import json
import os
import uuid  

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.api_gateway import Response
from aws_lambda_powertools.utilities.typing import LambdaContext

client = boto3.client('stepfunctions')
dynamodb = boto3.resource('dynamodb')
loan_table = dynamodb.Table(os.environ['TABLE_NAME'])  
sender_email = os.environ['sender_email']   
receiver_email = os.environ['receiver_email']

tracer = Tracer()
logger = Logger()
app = APIGatewayRestResolver()


@tracer.capture_method
@app.post("/loan_application")
def order_call():
    logger.info("Inside create user handler")
    data = app.current_event.json_body

    required_keys = [
        "bsn", "f_name", "l_name", "account_number", "loan_request_amount", "net_salary", "loan_type"
    ]

    for key in required_keys:
        if key not in data:
            return Response(
                status_code=400,
                content_type="application/json",
                body=json.dumps({"error": f"Missing key: {key}"})
            )

    appointment_id = uuid.uuid4().hex[:8]
    amount = float(data["loan_request_amount"])

    item = {
        "appointment_id": appointment_id,
        "bsn": data["bsn"],
        "f_name": data["f_name"],
        "l_name": data["l_name"],
        "account_number": data["account_number"],
        "loan_request_amount": data["loan_request_amount"],
        "net_salary": data["net_salary"],
        "loan_type": data["loan_type"],
        "status": "pending"
    }

    loan_table.put_item(Item=item)

    client.start_execution(
        stateMachineArn=os.environ["STATE_MACHINE_ARN"],
        input=json.dumps({
            "appointment_id": appointment_id,
            "amount": amount,
            "applicant": f'{data["f_name"]} {data["l_name"]}'
        })
    )

    return Response(
        status_code=200,
        content_type="application/json",
        body=json.dumps({
            "message": "We have received your loan application. You will be notified about the status once it is processed.",
            "appointment_id": appointment_id
        })
    )


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    logger.info("Lambda handler invoked")
    return app.resolve(event, context)
