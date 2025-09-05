import boto3
import os

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

ses = boto3.client("ses")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

sender_email = os.environ["sender_email"]
receiver_email = os.environ["receiver_email"]

tracer = Tracer()
logger = Logger()


@tracer.capture_method
def send_email(to_email: str, subject: str, body: str):
    ses.send_email(
        Source=sender_email,
        Destination={"ToAddresses": [to_email]},
        Message={"Subject": {"Data": subject}, "Body": {"Text": {"Data": body}}},
    )
    logger.info("Email sent")


@tracer.capture_method
def handle_event(event: dict, context: LambdaContext):
    amount = event.get("amount")
    appointment_id = event.get("appointment_id")

    if amount <= 3000:
        table.update_item(
            Key={"appointment_id": appointment_id},
            UpdateExpression="SET #s = :val",
            ExpressionAttributeNames={"#s": "status"},
<<<<<<< HEAD
            ExpressionAttributeValues={":val": "Auto-approved"}
=======
            ExpressionAttributeValues={":val": "approved"},
>>>>>>> b69f515 (initial code to use aurora as a database for loanprocessor project)
        )
        subject = "Loan Application Approved"
        body = (
            "Hi,\n\n"
            "Your loan application has been approved. The amount will be sent within 5-6 business days.\n\n"
            "Thanks."
        )
        send_email(receiver_email, subject, body)
        return {"status": "approved", "email_sent": True}

    return {"status": "requires manual review", "email_sent": False}


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    return handle_event(event, context)
