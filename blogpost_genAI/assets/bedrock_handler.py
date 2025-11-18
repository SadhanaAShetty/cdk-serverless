import boto3
import os
import json
from datetime import datetime
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.api_gateway import Response
from aws_lambda_powertools.utilities.typing import LambdaContext

# AWS clients
s3_client = boto3.client('s3')
bedrock_client = boto3.client('bedrock-runtime')

# Environment variables
bucket_name = os.environ["STATIC_BUCKET_NAME"]

# Powertools utilities
tracer = Tracer()
logger = Logger()
app = APIGatewayRestResolver()

def save_blog_to_s3(key: str, content: str):
    try:
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=content)
        logger.info(f"Blog saved to S3 at {key}")
    except Exception as e:
        logger.exception(f"Failed to save blog to S3: {e}")

@tracer.capture_method
@app.post("/create_blog")
def blog_handler(blogtopic: str) -> Response:
    logger.info(f"Creating blog for topic: {blogtopic}")

    
    prompt = f"""<s>[INST]Human: Write a 200 words blog on the topic {blogtopic}
        Assistant:[/INST]
        """

    payload = {
        "prompt": prompt,
        "max_gen_len": 256,
        "temperature": 0.5,
        "top_p": 0.9
    }

    try:
        response = bedrock_client.invoke_model(
            modelId="meta.llama3-2-1b-instruct-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )

        response_body = json.loads(response["body"].read())
        generated_text = response_body.get("generation", "")

        # Save generated blog to S3
        current_time = datetime.now().strftime("%Y%m%d-%H%M%S")
        key = f"blog-output/{current_time}.txt"
        save_blog_to_s3(key, generated_text)

        return Response(
            status_code=200,
            content_type="application/json",
            body=json.dumps({
                "prompt": prompt,
                "result": generated_text,
                "s3_key": key
            })
        )

    except Exception as e:
        logger.exception(f"Error generating blog: {e}")
        return Response(
            status_code=500,
            content_type="application/json",
            body=json.dumps({"error": str(e)})
        )

def lambda_handler(event: dict, context: LambdaContext):
    return app.resolve(event, context)
