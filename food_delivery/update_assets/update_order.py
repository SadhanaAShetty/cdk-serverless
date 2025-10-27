import os
import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext


logger = Logger(service="order_updater")
tracer = Tracer(service="order_updater")

# DynamoDB table
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    try:
        logger.info(f"Received event: {event}")
        
        order_data = event['detail']['data']
        order_id = order_data['orderId']
        user_id = order_data['userId']
        status = order_data['status']
        
        logger.info(f"Processing order update: orderId={order_id}, userId={user_id}, status={status}")

        key = {'userId': user_id, 'orderId': order_id}
        update_expression = "SET #data.#status = :status"
        expression_attribute_values = {':status': status}
        expression_attribute_names = {'#status': 'status', '#data': 'data'}

        tracer.put_annotation("orderId", order_id)
        tracer.put_annotation("userId", user_id)

        response = table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ExpressionAttributeNames=expression_attribute_names
        )

        logger.info(f"Updated order {order_id} for user {user_id} with status {status}")
        status_code = 200

    except Exception as err:
        logger.exception(f"Error updating order: {err}")
        response = {"Error": str(err)}
        status_code = 400

    return {
        "statusCode": status_code,
        "body": response
    }

