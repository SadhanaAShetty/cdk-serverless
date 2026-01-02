from aws_cdk import (
    Stack,
    Duration,
    aws_iam as iam,
    aws_events as events,
    aws_events_targets as targets,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_sns_subscriptions as subs,
    aws_cloudwatch as cloudwatch,
    aws_ssm as ssm
)
from constructs import Construct

from cdk_nag import NagSuppressions
from constructs.lmbda_construct import Lambda 


class CloudCostTracker(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        receiver = ssm.StringParameter.from_string_parameter_name(
            self, "SesReceiverIdentityParam",
            string_parameter_name="/ses/parameter/email/receiver"
        ).string_value

        # SNS Topic for alerts
        alert_topic = sns.Topic(
            self,
            "CostAlertTopic",
            display_name="CloudCostTracker Alerts",
            enforce_ssl=True
        )
        
        # Add email subscription
        alert_topic.add_subscription(subs.EmailSubscription(receiver))

        # Lambda using your custom construct
        cost_handler = Lambda(
            self,
            "CostHandlerFunction",
            function_name="cost_handler",
            handler="cost_handler.lambda_handler",
            code_path="cloud_cost_tracker/assets",
            env={
                "ALERT_TOPIC_ARN": alert_topic.topic_arn,
                "COST_THRESHOLD": "10.0",
                "FORCE_FAKE_COST": "true"
            }
        )

        # This is the actual Lambda function object
        cost_lambda = cost_handler.lambda_fn

        # EventBridge rule – runs daily at midnight UTC
        rule = events.Rule(
            self,
            "DailyCostCheck",
            schedule=events.Schedule.cron(minute="0", hour="0")
        )
        # Add DLQ for EventBridge target
        event_dlq = sqs.Queue(
            self, "DailyCostCheckDLQ",
            retention_period=Duration.days(14),
            enforce_ssl=True
        )

        rule.add_target(
            targets.LambdaFunction(
                cost_lambda,
                dead_letter_queue=event_dlq
            )
        )

        # SNS subscription DLQ (with SSL enforced)
        sns_dlq = sqs.Queue(
            self, "CostAlertSubscriptionDLQ",
            retention_period=Duration.days(14),
            enforce_ssl=True
        )

        # Attach DLQ to Lambda subscription
        alert_topic.add_subscription(
            subs.LambdaSubscription(
                cost_lambda,
                dead_letter_queue=sns_dlq
            )
        )

        # Allow Lambda to publish to SNS
        alert_topic.grant_publish(cost_lambda)
        
        # Grant Lambda permissions to access Cost Explorer
        cost_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["ce:GetCostAndUsage"],
                resources=["*"]
            )
        )

        # CloudWatch Dashboard
        dashboard = cloudwatch.Dashboard(
            self,
            "CloudCostTrackerDashboard",
            dashboard_name="CloudCostTrackerDashboard",
        )

        # Daily cost metric
        daily_cost_widget = cloudwatch.GraphWidget(
            title="Daily AWS Cost",
            left=[
                cloudwatch.Metric(
                    namespace="CloudCostTracker",
                    metric_name="DailyCost",
                    dimensions_map={"service": "cloudcost-tracker"}, 
                    statistic="Average",
                )
            ],
            width=12,
        )

        # Cost anomaly metric
        anomaly_widget = cloudwatch.GraphWidget(
            title="Cost Anomaly Detection",
            left=[
                cloudwatch.Metric(
                    namespace="CloudCostTracker",
                    metric_name="CostAnomaly",
                    dimensions_map={"service": "cloudcost-tracker"},  
                    statistic="Maximum",
                )
            ],
            width=12,
        )

        #ogs widget
        logs_widget = cloudwatch.LogQueryWidget(
            title="Lambda Log Events",
            log_group_names=[f"/aws/lambda/{cost_lambda.function_name}"],
            query_lines=[
                "fields @timestamp, @message",
                "sort @timestamp desc",
                "limit 20",
            ],
            width=24,
        )

        # Add widgets to dashboard
        dashboard.add_widgets(daily_cost_widget)
        dashboard.add_widgets(anomaly_widget)
        dashboard.add_widgets(logs_widget)

        # Nag suppression: IAM wildcard only
        NagSuppressions.add_resource_suppressions(
            cost_lambda,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Lambda requires wildcard permissions for CloudWatch Logs, Cost Explorer, and SNS publish actions."
                }
            ],
            apply_to_children=True
        )

        # suppress DLQ warnings (Nag wants redrive on DLQs themselves)
        for queue in [sns_dlq, event_dlq]:
            NagSuppressions.add_resource_suppressions(
                queue,
                [
                    {
                        "id": "Serverless-SQSRedrivePolicy",
                        "reason": "This queue is used as a DLQ; no further DLQ required."
                    },
                    {
                        "id": "AwsSolutions-SQS3",
                        "reason": "This queue is a DLQ, not intended for direct processing."
                    }
                ]
            )

        NagSuppressions.add_resource_suppressions(
            alert_topic,
            [
                {
                    "id": "Serverless-SNSRedrivePolicy",
                    "reason": (
                        "CDK creates a hidden TokenSubscription for the Lambda. "
                        "It uses a DLQ at runtime, but Nag sees no RedrivePolicy on that hidden resource. "
                        "Suppressing is safe."
                    )
                }
            ],
            apply_to_children=True
        )

