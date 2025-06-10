import os
import boto3
import json
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

rds_data_client = boto3.client("rds-data")
sns = boto3.client("sns")
stepfunctions_client = boto3.client("stepfunctions")

db_name = os.environ["DATABASE_NAME"]
cluster_arn = os.environ["DB_CLUSTER_ARN"]
secret_arn = os.environ["DB_SECRET_ARN"]
sns_topic_arn = os.environ["APPROVAL_TOPIC_ARN"]

tracer = Tracer()
logger = Logger()
app = APIGatewayRestResolver()


def send_sns_notification(subject: str, message: str):
    sns.publish(TopicArn=sns_topic_arn, Subject=subject, Message=message)


def update_loan_status(appointment_id: str, status: str):
    sql = """
        UPDATE loan_applications
        SET status = :status
        WHERE id = :appointment_id
    """
    parameters = [
        {"name": "status", "value": {"stringValue": status}},
        {"name": "appointment_id", "value": {"stringValue": appointment_id}},
    ]

    response = rds_data_client.execute_statement(
        resourceArn=cluster_arn,
        secretArn=secret_arn,
        database=db_name,
        sql=sql,
        parameters=parameters,
    )
    logger.info(f"Loan status updated to {status} for id: {appointment_id}")
    return response


@tracer.capture_method
@app.get("/approve")
def approve_handler():
    appointment_id = app.current_event.get_query_string_value("appointment_id")
    task_token = app.current_event.get_query_string_value("task_token")

    if not appointment_id:
        return {"error": "Missing appointment_id"}
    if not task_token:
        return {"statusCode": 400, "body": "Missing task_token"}

    update_loan_status(appointment_id, "approved")

    subject = "Loan Approved"
    body = (
        "Hello,\n\n"
        "Your loan application has been approved.\n"
        "The amount will be processed within 5-6 business days to your bank."
    )
    send_sns_notification(subject, body)
    logger.info(f"Sending task success for token: {task_token}")

    stepfunctions_client.send_task_success(
        taskToken=task_token, output=json.dumps({"status": "approved"})
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

    update_loan_status(appointment_id, "denied")

    subject = "Loan Denied"
    body = (
        "Hello,\n\n"
        "Unfortunately, your loan application has been denied.\n"
        "Please contact our support staff for more details."
    )
    send_sns_notification(subject, body)
    logger.info(f"Sending task success for token: {task_token}")

    stepfunctions_client.send_task_success(
        taskToken=task_token, output=json.dumps({"status": "denied"})
    )

    return {"status": "denied", "appointment_id": appointment_id}


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    return app.resolve(event, context)
