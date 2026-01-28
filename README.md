# AWS CDK Serverless Projects

This is my collection of AWS serverless projects built while learning CDK. I started this repository to understand how AWS services work together. 

## Repository Contents

The repository contains multiple projects with varying complexity levels. Here is what I have built:

```
cdk-serverless/
├── constructs/          # Reusable CDK constructs
├── food_delivery/       # Food delivery application
├── blogpost_genAI/      # AI blog generation service
├── order_processing/    # Order management system
├── loan_processing/     # Loan application processing
├── image_processing/    # Image processing pipeline  
├── notify_my_turn/      # Appointment notification system
├── quicksight_visuals/  # Data visualization dashboards
├── cloud_cost_tracker/  # AWS cost monitoring and alerting
├── holiday_home_swap/   # Home exchange platform
```

## Projects

### Food Delivery Application (food_delivery/)

This project expanded beyond the initial scope. It started as a simple order creation API and now includes five separate stacks.I tried to build something similar to Thuisbezorgd/uber eats

The application handles:
- Order creation, editing, and cancellation
- User profile and address management
- Favorite restaurant processing with SQS
- Real-time rider location tracking using Kinesis
- Order status updates through EventBridge
- User authentication with Cognito role-based access

Stack count: 5
Technologies: API Gateway, Lambda, DynamoDB, Kinesis, SQS, EventBridge, Cognito



### AI Blog Generator (blogpost_genAI/)

This project uses AWS Bedrock to generate blog content. The system accepts a topic and produces a 200-word blog post stored in S3.

The service includes:
- Content generation using Bedrock's Claude model
- Automatic S3 storage with timestamp organization
- Optional API key authentication
- Cost and token usage tracking

Technologies: API Gateway, Lambda, Bedrock, S3

Note: Bedrock usage costs require monitoring.

### Order Processing (order_processing/)

This is an early project implementing basic CRUD operations for order management. The system provides standard REST endpoints for order workflow management.

### Loan Processing (loan_processing/, loan_processor2/, loan_processor3/)

Three iterations of loan application processing systems. Each version improved upon the previous implementation.

The systems handle:
- Loan application submission
- Approval workflow processing
- Document management

### Image Processing (image_processing/)

An S3-triggered image processing pipeline. The system automatically resizes uploaded images using Lambda functions triggered by S3 events.

### Appointment Notification System (notify_my_turn/)

This system monitors appointment availability and sends notifications. It uses EventBridge Scheduler to check for available appointment slots.

The system includes:
- Scheduled appointment availability checking
- Duplicate notification prevention
- Multiple notification timing options
- Both SNS and SES notification methods

### Data Visualization (quicksight_visuals/)

A complete data pipeline from S3 storage to QuickSight dashboard visualization.

Technologies: QuickSight, Glue Crawler, Athena, S3

The Glue Crawler handles automatic schema discovery for the data catalog.

### AWS Cost Monitoring (cloud_cost_tracker/)

A serverless cost monitoring system that tracks daily AWS spending and detects cost anomalies. The system runs daily via EventBridge and sends alerts when spending exceeds normal patterns.

The system includes:
- Daily cost retrieval using AWS Cost Explorer API
- Cost anomaly detection algorithm
- CloudWatch metrics publishing for DailyCost and CostAnomaly
- SNS email alerts for unusual spending patterns
- CloudWatch dashboard with cost visualization
- Manual testing capability with simulated cost data

Technologies: Lambda, EventBridge, SNS, CloudWatch, Cost Explorer API

The system uses AWS Lambda Powertools for metrics and observability.

### Holiday Home Exchange Platform (holiday_home_swap/)

A FastAPI-based platform for home exchange between travelers. Users can list homes, create swap requests, and receive automatic matches with other homeowners.

The platform handles:
- User registration and JWT authentication
- Home listing creation with photo uploads
- Swap bid submission for specific locations and dates
- Automatic matching algorithm based on location and date compatibility
- Email notifications for successful matches
- Image storage and optimization via S3
- User preference management

Technologies: FastAPI, SQLite, SQLAlchemy, JWT, AWS S3, AWS SES, AWS CDK

Note: This project is currently in development.


## Reusable Constructs (constructs/)

After repeating Lambda function configurations multiple times, I created reusable constructs to reduce code duplication.

### LambdaConstruct
Standard Lambda function setup with common configurations:
- Python 3.13 runtime
- AWS Powertools layer integration
- Dead letter queue configuration
- Standard timeout and memory allocation

```python
lambda_fn = LambdaConstruct(
    self, "MyFunction",
    function_name="my_function", 
    handler="index.handler",
    code_path="lambda/",
    env={"KEY": "value"}
)
```

### DynamoTable
DynamoDB table configuration with on-demand billing and standard access patterns.

### ApiGatewayConstruct
API Gateway setup with CloudWatch logging and request throttling enabled by default.

## Setup Instructions

Requirements:
- Python 3.9 or higher
- AWS CLI with configured credentials
- CDK CLI installation (npm install -g aws-cdk)

Installation process:
```bash
git clone <repository-url>
cd cdk-serverless

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install -r requirements-dev.txt

cdk bootstrap
```

Deployment commands:
```bash
cdk list
cdk deploy FoodDeliveryStack
cdk deploy --all
cdk destroy FoodDeliveryStack
```

Environment configuration:
Create a .env file with:
```bash
AWS_ACCOUNT_ID=your-account-number
AWS_REGION=your-region
```

## Testing

Testing is implemented for select projects using pytest. Currently, tests exist for the food delivery and holiday home swap projects.

Testing framework:
- pytest for test execution
- unittest.mock for dependency mocking
- FastAPI TestClient for API testing


## Security Compliance

Recent projects use CDK-nag for security validation. The tool enforces AWS security best practices. For learning projects, some warnings are suppressed with documented justifications.

## Technical Observations

Architecture patterns used:
- Event-driven processing with EventBridge and SQS
- Microservice separation through independent stacks
- Serverless-first approach with Lambda functions



Effective patterns:
- Lambda with API Gateway for HTTP APIs
- DynamoDB for most database requirements
- S3 for file storage and static content
- EventBridge for service decoupling
- AWS Lambda Powertools for observability

## Technology Stack

Core services:
- AWS Lambda (Python 3.13)
- API Gateway
- DynamoDB
- S3
- EventBridge
- SQS and SNS for messaging

Monitoring and observability:
- CloudWatch logs, metrics, and alarms
- AWS Lambda Powertools

Infrastructure management:
- AWS CDK with Python
- CDK-nag for security validation

