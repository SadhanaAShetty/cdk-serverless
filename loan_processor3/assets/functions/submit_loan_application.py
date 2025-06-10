import boto3
import json
import os
import uuid

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.api_gateway import Response
from aws_lambda_powertools.utilities.typing import LambdaContext

stepfunctions_client = boto3.client("stepfunctions")
rds_data_client = boto3.client("rds-data")

db_name = os.environ["DATABASE_NAME"]
cluster_arn = os.environ["DB_CLUSTER_ARN"]
secret_arn = os.environ["DB_SECRET_ARN"]

tracer = Tracer()
logger = Logger()
app = APIGatewayRestResolver()


@tracer.capture_method
@app.post("/loan_application")
def order_call():
    logger.info("Inside create user handler")
    data = app.current_event.json_body

    required_keys = [
        "bsn",
        "f_name",
        "l_name",
        "account_number",
        "loan_request_amount",
        "net_salary",
        "loan_type",
    ]

    for key in required_keys:
        if key not in data:
            return Response(
                status_code=400,
                content_type="application/json",
                body=json.dumps({"error": f"Missing key: {key}"}),
            )

    id = uuid.uuid4().hex[:8]  
    amount = float(data["loan_request_amount"])

    sql = """
    INSERT INTO loan_applications
    (id, bsn, f_name, l_name, account_number, loan_request_amount, net_salary, loan_type, status)
    VALUES
    (:id, :bsn, :f_name, :l_name, :account_number, :loan_request_amount, :net_salary, :loan_type, :status)
    """

    parameters = [
        {"name": "id", "value": {"stringValue": id}},
        {"name": "bsn", "value": {"stringValue": data["bsn"]}},
        {"name": "f_name", "value": {"stringValue": data["f_name"]}},
        {"name": "l_name", "value": {"stringValue": data["l_name"]}},
        {"name": "account_number", "value": {"stringValue": data["account_number"]}},
        {"name": "loan_request_amount","value": {"stringValue": data["loan_request_amount"]}},
        {"name": "net_salary", "value": {"stringValue": data["net_salary"]}},
        {"name": "loan_type", "value": {"stringValue": data["loan_type"]}},
        {"name": "status", "value": {"stringValue": "pending"}},
    ]

    response = rds_data_client.execute_statement(
        resourceArn=cluster_arn,
        secretArn=secret_arn,
        database=db_name,
        sql=sql,
        parameters=parameters,
    )

    stepfunctions_client.start_execution(
        stateMachineArn=os.environ["STATE_MACHINE_ARN"],
        input=json.dumps(
            {
                "appointment_id": id,  
                "amount": amount,
                "applicant": f"{data['f_name']} {data['l_name']}",
            }
        ),
    )

    return Response(
        status_code=200,
        content_type="application/json",
        body=json.dumps(
            {
                "message": "We have received your loan application. You will be notified about the status once it is processed.",
                "appointment_id": id,
            }
        ),
    )


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    logger.info("Lambda handler invoked")
    return app.resolve(event, context)
