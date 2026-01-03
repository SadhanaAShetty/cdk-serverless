import boto3
import datetime
import os
import random
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit

logger = Logger(service="cloudcost-tracker")
tracer = Tracer(service="cloudcost-tracker")
metrics = Metrics(namespace="CloudCostTracker", service="cloudcost-tracker")

ce_client = boto3.client("ce")
sns_client = boto3.client("sns")
ALERT_TOPIC_ARN = os.environ.get("ALERT_TOPIC_ARN")
COST_THRESHOLD = float(os.environ.get("COST_THRESHOLD", "10.0"))
FORCE_FAKE_COST = os.environ.get("FORCE_FAKE_COST", "false").lower() == "true"

@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event, context):
    if FORCE_FAKE_COST:
        daily_cost = simulate_daily_cost()
        logger.info(f"FORCED Fake Cost: ${daily_cost:.2f}")
    else:
    # Get yesterday's cost from Cost Explorer
        daily_cost = get_daily_cost()
    
    metrics.add_metric(
        name="DailyCost",
        unit=MetricUnit.Count,
        value=daily_cost
    )

    # Detect anomaly - cost exceeds threshold
    anomaly_value = 1 if daily_cost > COST_THRESHOLD else 0

    metrics.add_metric(
        name="CostAnomaly",
        unit=MetricUnit.Count,
        value=anomaly_value
    )

    if anomaly_value:
        message = f"Alert!! Your daily AWS cost is unusually high: ${daily_cost:.2f} (Threshold: ${COST_THRESHOLD:.2f})"
        send_alert(message)
        logger.warning(message)
    else:
        logger.info(f"Your daily cost is normal: ${daily_cost:.2f}")

    return {
        "daily_cost": daily_cost,
        "anomaly": anomaly_value,
        "threshold": COST_THRESHOLD
    }

def get_daily_cost():
    """Get yesterday's AWS cost from Cost Explorer."""
    try:
        today = datetime.datetime.now().date()
        yesterday = today - datetime.timedelta(days=1)
        
        start_date = yesterday.strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        
        logger.info(f"Fetching cost data from {start_date} to {end_date}")
        
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                "Start": start_date,
                "End": end_date
            },
            Granularity="DAILY",
            Metrics=["UnblendedCost"]
        )
        
        # Extract the cost value
        if response["ResultsByTime"]:
            cost = float(response["ResultsByTime"][0]["Total"]["UnblendedCost"]["Amount"])
            logger.info(f"Retrieved daily cost: ${cost:.2f}")
            return cost
        else:
            logger.warning("No cost data available")
            return 0.0
            
    except Exception as e:
        logger.error(f"Error fetching cost data: {str(e)}")
        raise


def send_alert(message):
    """Send an alert to the SNS topic."""
    sns_client.publish(
        TopicArn=ALERT_TOPIC_ARN,
        Message=message,
        Subject="AWS Cost Alert"
    )   

def simulate_daily_cost():
    """Simulated cost for demo.""" 
    return random.uniform(7, 27)
    















