import json
import os
import boto3
from urllib.parse import urlencode

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

ses = boto3.client('ses')
client = boto3.client('stepfunctions')
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client("lambda")
ssm = boto3.client("ssm")

sender_email = os.environ['sender_email']
receiver_email = os.environ['receiver_email']
param_name = os.environ["API_BASE_URL_PARAM"]
api_base_url = ssm.get_parameter(Name=param_name)["Parameter"]["Value"]

tracer = Tracer()
logger = Logger()
app = APIGatewayRestResolver()

@tracer.capture_method
def send_email(to_email: str, subject: str, body: str):
    ses.send_email(
        Source=sender_email,
        Destination={'ToAddresses': [to_email]},
        Message={
            'Subject': {'Data': subject},
            'Body': {'Text': {'Data': body}}
        }
    )

@tracer.capture_method
def handle_event(event: dict, context: LambdaContext):
    task_token = event.get("taskToken")
    input_data = event.get("input", {})

    appointment_id = input_data.get("appointment_id")
    amount = input_data.get("amount")
    name = input_data.get("applicant")

    if not (task_token and appointment_id):
        return {"statusCode": 400, "body": "Missing required parameters"}

    approve_params = urlencode({
        "task_token": task_token,
        "appointment_id": appointment_id,
        "action": "approve"
    })

    deny_params = urlencode({
        "task_token": task_token,
        "appointment_id": appointment_id,
        "action": "deny"
    })

    approve_url = f"{api_base_url}/approve?{approve_params}"
    deny_url = f"{api_base_url}/deny?{deny_params}"

    subject = "Loan Application Status"
    body = (
        f"Dear Manager,\n\n"
        f"A loan application requires your review.\n\n"
        f"Applicant: {name}\n"
        f"Amount Requested: €{amount}\n\n"
        f"Please review the request:\n"
        f"Approve: {approve_url}\n"
        f"Deny: {deny_url}\n"
    )

    send_email(receiver_email, subject, body)

    return {
        "statusCode": 200,
        "body": f"Approval email sent for appointment_id {appointment_id}"
    }

@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    return handle_event(event, context)
