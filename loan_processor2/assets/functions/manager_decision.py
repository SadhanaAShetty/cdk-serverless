import os
import boto3
import json
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")
client = boto3.client("stepfunctions")

table_name = os.environ["TABLE_NAME"]
sns_topic_arn = os.environ["SNS_TOPIC_ARN"]

table = dynamodb.Table(table_name)

tracer = Tracer()
logger = Logger()
app = APIGatewayRestResolver()

def send_sns_notification(subject: str, message: str):
    sns.publish(
        TopicArn=sns_topic_arn,
        Subject=subject,
        Message=message
    )

@tracer.capture_method
@app.get("/approve")
def approve_handler():
    appointment_id = app.current_event.get_query_string_value("appointment_id")
    task_token = app.current_event.get_query_string_value("task_token")
    
    if not appointment_id:
        return {"error": "Missing appointment_id"}
    if not task_token:
        return {"statusCode": 400, "body": "Missing task_token"}

    table.update_item(
        Key={"appointment_id": appointment_id},
        UpdateExpression="SET #s = :val",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":val": "approved"}
    )

    subject = "Loan Approved"
    body = (
        "Hello,\n\n"
        "Your loan application has been approved.\n"
        "The amount will be processed within 5-6 business days."
    )
    send_sns_notification(subject, body)
    logger.info(f"Sending task success for token: {task_token}")

    client.send_task_success(
        taskToken=task_token,
        output=json.dumps({"status": "approved"})
    )

    return {"status": "approved", "appointment_id": appointment_id}


@tracer.capture_method
@app.get("/deny")
def deny_handler():
    appointment_id = app.current_event.get_query_string_value("appointment_id")
    task_token = app.current_event.get_query_string_value("task_token")
    
    if not appointment_id:
        return {"error": "Missing appointment_id"}
    if not task_token:
        return {"statusCode": 400, "body": "Missing task_token"}

    table.update_item(
        Key={"appointment_id": appointment_id},
        UpdateExpression="SET #s = :val",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":val": "denied"}
    )

    subject = "Loan Denied"
    body = (
        "Hello,\n\n"
        "Unfortunately, your loan application has been denied.\n"
        "Please contact our support staff for more details."
    )
    send_sns_notification(subject, body)
    logger.info(f"Sending task success for token: {task_token}")

    client.send_task_success(
        taskToken=task_token,
        output=json.dumps({"status": "denied"})
    )

    return {"status": "denied", "appointment_id": appointment_id}


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    return app.resolve(event, context)
