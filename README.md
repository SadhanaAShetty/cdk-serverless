# cdk-serverless
# CDK Serverless Projects

A collection of AWS serverless applications built with AWS CDK (Cloud Development Kit) in Python. This repository demonstrates various serverless architectures, patterns, and AWS services integration.

## 🏗️ Repository Structure

```
cdk-serverless/
├── constructs/          # Reusable CDK constructs
├── food_delivery/       # Food delivery platform
├── blogpost_genAI/      # AI blog generator with Bedrock
├── order_processing/    # Order processing system
├── loan_processing/     # Loan processing workflows
├── image_processing/    # Image processing pipeline
├── notify_my_turn/      # Notification service
└── quicksight_visuals/  # QuickSight dashboards
```

## 📦 Projects

### 🍕 Food Delivery Platform
**Path:** `food_delivery/`

A comprehensive serverless food delivery backend with multiple microservices.

**Features:**
- Order management (create, edit, cancel, fetch)
- User profile & address management
- Favorite restaurants with SQS processing
- Real-time rider location tracking (Kinesis)
- EventBridge-driven order updates
- Cognito authentication with role-based access
- CloudWatch monitoring & SNS alerts

**Tech Stack:** API Gateway, Lambda, DynamoDB, Kinesis, SQS, EventBridge, Cognito

**Stacks:** 5 (Main, User Profile, Favorites, Order Updates, Data Stream)

[📖 Full Documentation](food_delivery/README.md)

---

### 🤖 AI Blog Generator
**Path:** `blogpost_genAI/`

Generate blog posts using AWS Bedrock's llm model via REST API.

**Features:**
- AI-powered content generation (200-word blogs)
- Automatic S3 storage with timestamps
- API key authentication (optional)
- Cost tracking & token usage logging
- LLM integration

**Tech Stack:** API Gateway, Lambda, Bedrock, S3

**Performance:** ~1-2 seconds per blog generation

[📖 Full Documentation](blogpost_genAI/README.md)


---

### 📦 Order Processing
**Path:** `order_processing/`

Serverless backend order processing system.

**Features:**
- Order workflow management
- RESTful API endpoints
- Order state management
- Event-driven architecture

**Tech Stack:** API Gateway, Lambda, DynamoDB

---

### 💰 Loan Processing
**Path:** `loan_processing/`, `loan_processor2/`, `loan_processor3/`

Loan application processing workflows with multiple iterations.

**Features:**
- Loan application management
- Approval workflows
- Document processing

**Tech Stack:** Lambda, DynamoDB, Step Functions

---

### 🖼️ Image Processing
**Path:** `image_processing/`

Serverless image processing pipeline.

**Features:**
- Image upload & transformation
- Automated processing triggers
- S3 event-driven architecture

**Tech Stack:** Lambda, S3, CloudFront

---

### 🔔 Notify My Turn
**Path:** `notify_my_turn/`

Automated appointment notification system with EventBridge Scheduler.

**Features:**
- EventBridge Scheduler for appointment checks
- Overlap detection & prevention
- Dual-time alert notifications (2 scheduled times)
- Appointment availability monitoring
- SNS/SES notifications

**Tech Stack:** EventBridge Scheduler, Lambda, SNS, SES, DynamoDB

---

### 📊 QuickSight Visuals
**Path:** `quicksight_visuals/`

AWS QuickSight dashboard with automated data pipeline.

**Features:**
- Business intelligence dashboards
- Glue Crawler for schema discovery
- Athena for SQL queries
- S3 data lake storage
- Automated data cataloging

**Tech Stack:** QuickSight, Glue Crawler, Athena, S3

---

## 🔧 Reusable Constructs

**Path:** `constructs/`

Custom CDK constructs for code reusability across projects.

### Available Constructs:

#### `LambdaConstruct`
Simplified Lambda function creation with built-in best practices.

**Features:**
- Python 3.13 runtime
- AWS Powertools layer included
- Automatic DLQ creation
- CDK-nag suppressions
- Default timeout & memory settings

**Usage:**
```python
from constructs.lmbda_construct import LambdaConstruct

lambda_fn = LambdaConstruct(
    self, "MyFunction",
    function_name="my_function",
    handler="index.handler",
    code_path="lambda/",
    env={"KEY": "value"}
)
```

#### `DynamoTable`
Reusable DynamoDB TableV2 construct with sensible defaults.

**Features:**
- On-demand billing
- Automatic grant methods
- Simplified key configuration

**Usage:**
```python
from constructs.ddb import DynamoTable

table = DynamoTable(
    self, "MyTable",
    table_name="MyTable",
    partition_key="id",
    sort_key="timestamp"
)
```

#### `ApiGatewayConstruct`
API Gateway with logging, throttling, and CDK-nag suppressions.

**Features:**
- CloudWatch logging enabled
- Throttling configured
- Common suppressions applied
- Helper methods for auth

**Usage:**
```python
from constructs.api_gateway_construct import ApiGatewayConstruct

api = ApiGatewayConstruct(
    self, "MyApi",
    api_name="MyAPI",
    throttling_rate_limit=1000
)
```

#### `S3BucketConstruct`
S3 bucket with security best practices.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- AWS CLI configured
- AWS CDK CLI installed


### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd cdk-serverless

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Bootstrap CDK (first time only)
cdk bootstrap
```

### Deployment

```bash
# List all stacks
cdk list

# Deploy a specific stack
cdk deploy FoodDeliveryStack

# Deploy all stacks
cdk deploy --all

# Destroy a stack
cdk destroy FoodDeliveryStack
```

### Environment Variables

Create a `.env` file in the root directory:

```bash
AWS_ACCOUNT_ID=your-account-id
AWS_REGION=eu-west-1
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific project tests
pytest food_delivery/tests/

# Run with coverage
pytest --cov=food_delivery
```

---

## 📋 CDK-Nag Compliance

Latest few projects use CDK-nag for security and best practices validation.

**Approach:**
- Fix critical security issues
- Suppress warnings with justification for dev/learning projects
- Common suppressions in reusable constructs

---

## 🏛️ Architecture Patterns

### Event-Driven Architecture
- EventBridge for order updates
- Kinesis for real-time data streaming
- SQS for async processing

### Microservices
- Separate stacks for different domains
- Independent deployment
- Shared constructs for consistency

### Performance Optimization
- Parallel DynamoDB queries
- Connection pooling
- Minimal Lambda cold starts
- Optimized memory allocation


---

## 🛠️ Tech Stack

**Core Services:**
- AWS Lambda (Python 3.13)
- API Gateway (REST)
- DynamoDB (TableV2)
- S3
- Cognito

**Event Processing:**
- EventBridge
- Kinesis Data Streams
- SQS

**AI/ML:**
- AWS Bedrock 

**Monitoring:**
- CloudWatch Logs & Metrics
- CloudWatch Alarms
- SNS Notifications
- AWS Lambda Powertools

**IaC:**
- AWS CDK (Python)
- CDK-nag for compliance

---

## 📝 Best Practices

### Lambda Functions
- Use Powertools for logging/tracing
- Implement DLQs for reliability
- Optimize memory for performance
- Use environment variables for config

### DynamoDB
- Use on-demand billing for variable workloads
- Implement projection expressions
- Use boto3 client for performance
- Parallel queries where possible

### API Gateway
- Enable CloudWatch logging
- Configure throttling
- Use custom authorizers
- Implement proper error handling

### Security
- Least privilege IAM policies
- Enable encryption at rest
- Use Cognito for authentication
- Validate all inputs

---

## 🤝 Contributing

This is a personal learning repository. Feel free to fork and adapt for your own projects.

---

**Built with ❤️ using AWS CDK**

