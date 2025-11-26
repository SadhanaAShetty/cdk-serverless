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

**🏗 Architecture**
EventBridge (daily) → Lambda → Metrics → CloudWatch Dashboard
                              ↳ Alerts → SNS Email
