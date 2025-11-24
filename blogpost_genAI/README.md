# Blog Post Generator with AWS Bedrock

An AI-powered blog post generator using AWS Bedrock's Llama 3.2 model. Generate 200-word blog posts on any topic via a REST API and automatically store them in S3.

## Features

- **AI-Powered Content Generation**: Uses Meta's Llama 3.2 1B Instruct model via AWS Bedrock
- **REST API**: Simple POST endpoint for blog generation
- **API Key Authentication**: Secure access with API keys for Postman testing
- **Automatic Storage**: Generated blog posts saved to S3 with timestamps
- **Serverless Architecture**: Fully serverless using Lambda, API Gateway, and S3
- **Observability**: CloudWatch logging and metrics enabled

## Architecture

Postman → API Gateway (with API Key) → Lambda → Bedrock (Llama 3.2) → S3


## How It Works

1. **Send Request**: POST to `/create_blog` with a topic in the request body
2. **AI Generation**: Lambda invokes Bedrock's Llama 3.2 model with your topic
3. **Storage**: Generated blog post is saved to S3 with timestamp
4. **Response**: Returns the generated content and S3 location

## API Usage

### Endpoint

POST https://{api-id}.execute-api.{region}.amazonaws.com/dev/create_blog


### Headers
```
x-api-key: {your-api-key}
Content-Type: application/json
```

### Request Body
```json
{
  "blogtopic": "Generative AI"
}
```

### Response
```json
{
  "prompt": "Write a 200 words blog on the topic Generative AI",
  "result": "Generated blog content...",
  "s3_key": "blog-output/20241118-143022.txt"
}
```

## Deployment

```bash
cdk deploy BlogPostGenAI
```

After deployment, note the outputs:
- **ApiUrl**: Your API Gateway endpoint
- **ApiKeyId**: Your API key ID (retrieve value from AWS Console)
- **BucketName**: S3 bucket where blogs are stored

## Configuration

- **Model**: Meta Llama 3.2 1B Instruct (`meta.llama3-2-1b-instruct-v1:0`)
- **Max Tokens**: 256
- **Temperature**: 0.5
- **Top P**: 0.9
- **Timeout**: 30 seconds
- **Throttling**: 10 requests/second, burst of 2

## Testing with Postman

1. Get your API key from AWS Console (API Gateway → API Keys)
2. Create a POST request to the API endpoint
3. Add `x-api-key` header with your API key
4. Send JSON body with `blogtopic` field
5. Check S3 bucket for generated blog posts

## Cost Optimization

- **Serverless**: Pay only for what you use
- **On-Demand Pricing**: No upfront costs
- **Throttling**: Rate limits prevent unexpected costs
- **X-Ray Disabled**: Reduced observability costs

## Security

- ✅ API Key authentication
- ✅ IAM least-privilege permissions
- ✅ Encrypted S3 storage
- ✅ CloudWatch logging for audit
- ✅ Rate limiting to prevent abuse

