# Food Delivery Backend

A comprehensive serverless **Food Delivery** platform built on **AWS** with multiple microservices and real-time capabilities.

## Core Features

### 🍕 Order Management

- **Order Operations**: Create, edit, cancel, and fetch food orders
- **Order Updates**: Real-time order status updates via EventBridge
- **Order Tracking**: Complete order lifecycle management

### 👤 User Profile Management

- **Address Management**: Add, edit, delete, and list user delivery addresses
- **Favorite Restaurants**: Manage user's favorite restaurant preferences with SQS processing
- **User Authentication**: Secure authentication with Amazon Cognito User Pool
- **Role-based Authorization**: Admin and regular user access control

### 📍 Real-time Location Tracking

- **Kinesis Data Streaming**: Real-time rider location tracking
- **Location Producer**: Simulate and capture rider GPS coordinates
- **Location Consumer**: Process location updates and store in DynamoDB
- **EventBridge Simulator**: Automated location data generation every 15 minutes

### 🔧 Infrastructure & Architecture

- **Multiple API Gateways**: Separate APIs for orders, addresses, and favorites
- **DynamoDB Tables**: Scalable NoSQL storage for orders, addresses, favorites, and rider positions
- **SQS Queues**: Asynchronous processing with dead letter queues for favorites
- **EventBridge**: Custom event buses for order updates and address events
- **Lambda Functions**: 15+ serverless functions handling different operations

### 📊 Monitoring & Observability

- **CloudWatch Alarms**: Comprehensive monitoring for API Gateway, Lambda, DynamoDB, and SQS
- **SNS Notifications**: Email alerts for system health issues
- **Powertools Integration**: Structured logging, tracing, and metrics
- **API Gateway Logging**: Detailed access logs and performance metrics

### 🏗️ Development & Testing

- **CDK Constructs**: Reusable infrastructure components for DynamoDB tables
- **Comprehensive Testing**: Unit and integration tests for all components
- **Multiple Environments**: Separate test suites for different features
- **Infrastructure as Code**: Complete AWS CDK implementation

## Architecture Components

- **4 CDK Stacks**: Main orders, data streaming, favorites, user profiles, and order updates
- **15+ Lambda Functions**: Microservices architecture with single-purpose functions
- **3 API Gateways**: Dedicated APIs for different service domains
- **Multiple DynamoDB Tables**: Optimized data models for different use cases
- **Kinesis Stream**: Real-time data processing pipeline
- **SQS Queues**: Reliable message processing with retry mechanisms
- **EventBridge Buses**: Event-driven architecture for loose coupling
