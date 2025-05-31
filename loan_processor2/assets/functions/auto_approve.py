import boto3
import os

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

sns = boto3.client('sns')
sns_topic_arn = os.environ["APPROVAL_TOPIC_ARN"]

tracer = Tracer()
logger = Logger()


@tracer.capture_method
def publish_to_sns(subject: str, message: str):
    sns.publish(
        TopicArn=sns_topic_arn,
        Subject=subject,
        Message=message
    )
    logger.info("SNS message published")


@tracer.capture_method
def handle_event(event: dict, context: LambdaContext):
    amount = event.get('amount')
    appointment_id = event.get('appointment_id')

    if amount <= 3000:
        table.update_item(
            Key={"appointment_id": appointment_id},
            UpdateExpression="SET #s = :val",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":val": "approved"}
        )
        subject = "Loan Application Approved"
        body = (
            "Hi,\n\n"
            "Your loan application has been approved. You will be notified about the process. The amount will be sent within 5-6 business days.\n\n"
            "Thanks."
        )
        publish_to_sns(subject, body)
        return {"status": "approved", "notification_sent": True}

    return {"status": "requires manual review", "notification_sent": False}


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    return handle_event(event, context)
