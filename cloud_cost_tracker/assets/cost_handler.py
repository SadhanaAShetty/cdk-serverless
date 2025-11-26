import boto3
import datetime
import random
import os
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit

logger = Logger(service="cloudcost-tracker")
tracer = Tracer(service="cloudcost-tracker")
metrics = Metrics(namespace="CloudCostTracker", service="cloudcost-tracker")

client = boto3.client('cloudwatch')
client = boto3.client('events')
sns_client = boto3.client("sns")
ALERT_TOPIC_ARN = os.environ.get("ALERT_TOPIC_ARN")

@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event, context):
    daily_cost = simulate_daily_cost()
    
    # Add metrics using Powertools
    metrics.add_metric(name="DailyCost", unit=MetricUnit.None_, value=daily_cost)

    # Detect anomaly
    anomaly_value = 1 if daily_cost > 1000 else 0
    metrics.add_metric(name="CostAnomaly", unit=MetricUnit.Count, value=anomaly_value)

    if anomaly_value:
        message = f"Alert!! Your daily AWS cost is unussually higher : {daily_cost}"
        send_alert(message)
        logger.warning(message)
    else:
        logger.info(f"Your daily dost is normal: {daily_cost}")


    # Flush metrics at the end
    metrics.flush()

    return {"daily_cost": daily_cost, "anomaly": anomaly_value}

def send_alert(message):
    """Send an alert to the SNS topic."""
    sns_client.publish(
    TopicArn=ALERT_TOPIC_ARN,
    Message= message,
    Subject="Cost Exceed Alert"
)


def simulate_daily_cost():
    """Simulate a daily cost value (for demonstration)."""
    return random.uniform(200, 1500)

    
















# @tracer.capture_lambda_handler
# @logger.inject_lambda_context
# def lambda_handler(event, context):

    
#     today = datetime.date.today()
#     yesterday = today - datetime.timedelta(days=1)

#     start = yesterday.strftime("%Y-%m-%d")
#     end = today.strftime("%Y-%m-%d")

#     logger.info(f"Fetching AWS cost from {start} to {end}")

    
#     response = ce.get_cost_and_usage(
#         TimePeriod={"Start": start, "End": end},
#         Granularity="DAILY",
#         Metrics=["UnblendedCost"]
#     )


#     amount = float(
#         response["ResultsByTime"][0]["Total"]["UnblendedCost"]["Amount"]
#     )

#     logger.info({
#         "date": start,
#         "daily_cost_usd": amount
#     })


#     metrics.add_metric(
#         name="DailyCost",
#         unit=MetricUnit.None_,
#         value=amount
#     )
#     metrics.add_metric(
#         name="CostAnomaly",
#         unit=MetricUnit.None_,
#         value=1 if amount > 10 else 0 
#     )

#     metrics.flush()  

#     return {
#         "status": "success",
#         "cost": amount,
#         "date": start
#     }
