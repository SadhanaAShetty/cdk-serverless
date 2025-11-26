import boto3
import datetime
import random
import os
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit

logger = Logger(service="cloudcost-tracker")
tracer = Tracer(service="cloudcost-tracker")
metrics = Metrics(namespace="CloudCostTracker", service="cloudcost-tracker")

sns_client = boto3.client("sns")
ALERT_TOPIC_ARN = os.environ.get("ALERT_TOPIC_ARN")

@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event, context):

    daily_cost = simulate_daily_cost()
    
    metrics.add_metric(
        name="DailyCost",
        unit=MetricUnit.Count,
        value=daily_cost
    )

    # Detect anomaly
    anomaly_value = 1 if daily_cost > 5 else 0

    metrics.add_metric(
        name="CostAnomaly",
        unit=MetricUnit.Count,
        value=anomaly_value
    )

    if anomaly_value:
        message = f"Alert!! Your daily AWS cost is unusually high: {daily_cost}"
        send_alert(message)
        logger.warning(message)
    else:
        logger.info(f"Your daily cost is normal: {daily_cost}")

    return {
        "daily_cost": daily_cost,
        "anomaly": anomaly_value
    }

def send_alert(message):
    """Send an alert to the SNS topic."""
    sns_client.publish(
    TopicArn=ALERT_TOPIC_ARN,
    Message= message,
    Subject="Cost Exceed Alert"
)


def simulate_daily_cost():
    """Simulated cost for demo."""
    return random.uniform(4, 14)   

    















