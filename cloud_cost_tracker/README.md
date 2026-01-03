**📊 CloudCostTracker**

A simple AWS serverless project that tracks your daily AWS cost, detects anomalies, publishes metrics, and sends alerts. Uses Lambda, EventBridge, SNS, and CloudWatch with AWS Lambda Powertools.

**🚀 What It Does**

Runs once per day using EventBridge

Lambda calls Cost Explorer → gets today & yesterday’s spend



**Publishes two Powertools metrics:**

DailyCost

CostAnomaly

Sends an SNS alert email if cost is unusually high

Displays graphs + logs on a CloudWatch Dashboard

For manual testing, you can enable random fake costs using FORCE_FAKE_COST=true to trigger alerts and metrics immediately.

**🏗 Architecture**
EventBridge (daily) → Lambda → Metrics → CloudWatch Dashboard
                              ↳ Alerts → SNS Email

EventBridge: triggers the Lambda function at midnight UTC.

Lambda: fetches costs, calculates anomalies, publishes metrics, and sends alerts.

SNS: sends alert emails when anomalies are detected.

CloudWatch Dashboard: shows metrics (DailyCost, CostAnomaly) and Lambda logs.