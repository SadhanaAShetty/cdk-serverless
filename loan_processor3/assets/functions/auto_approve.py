import boto3
import os

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext


db_name = os.environ["DATABASE_NAME"]
cluster_arn = os.environ["DB_CLUSTER_ARN"]
secret_arn = os.environ["DB_SECRET_ARN"]

sns = boto3.client("sns")
rds_data_client = boto3.client("rds-data")
sns_topic_arn = os.environ["APPROVAL_TOPIC_ARN"]

tracer = Tracer()
logger = Logger()

@tracer.capture_method
def publish_to_sns(subject: str, message: str):
    sns.publish(TopicArn=sns_topic_arn, Subject=subject, Message=message)
    logger.info("SNS message published")


@tracer.capture_method
def update_loan_status(appointment_id: str, new_status: str):
    sql = """
    UPDATE loan_applications
    SET status = :new_status
    WHERE id = :appointment_id
    """
    parameters = [
        {"name": "new_status", "value": {"stringValue": new_status}},
        {"name": "appointment_id", "value": {"stringValue": appointment_id}},
    ]

    response = rds_data_client.execute_statement(
        resourceArn=cluster_arn,
        secretArn=secret_arn,
        database=db_name,
        sql=sql,
        parameters=parameters,
    )

    logger.info("Updated loan status in database: %s", response)
    return response


@tracer.capture_method
def handle_event(event: dict, context: LambdaContext):
    amount = event.get("amount")
    appointment_id = event.get("appointment_id")

    if amount is None or appointment_id is None:
        logger.error("Missing amount or appointment_id in event")
        return {"error": "Missing required data"}

    if amount <= 3000:
        
        update_loan_status(appointment_id, "approved")

        
        subject = "Loan Application Approved"
        body = (
            "Hi,\n\n"
            "Your loan application has been approved. You will be notified about the process. "
            "The amount will be sent within 5-6 business days.\n\n"
            "Thanks."
        )
        publish_to_sns(subject, body)
        return {"status": "approved", "notification_sent": True}

    return {"status": "requires manual review", "notification_sent": False}


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    return handle_event(event, context)
