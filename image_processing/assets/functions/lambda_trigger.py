import boto3
import os
import json
import urllib.parse

client = boto3.client('ecs')
s3 = boto3.client('s3')

cluster = os.environ["CLUSTER"]
task_definition = os.environ["TASK_DEF_ARN"]
input_bucket = os.environ["INPUT_BUCKET"]
output_bucket = os.environ["OUTPUT_BUCKET"]


subnets = [s for s in os.environ.get("SUBNETS", "").split(",") if s.strip()]
security_groups = [s for s in os.environ.get("SECURITY_GROUPS", "").split(",") if s.strip()]

def lambda_handler(event, context):
    print("Event:", json.dumps(event))
    
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        
        output_key = f"thumbnails/{key.split('/')[-1]}"
        
        print(f"Starting ECS task for bucket: {bucket}, key: {key}")
        print(f"Output Key: {output_key}")

        try:
            response = client.run_task(
                cluster=cluster,
                launchType="FARGATE",
                taskDefinition=task_definition,
                networkConfiguration={
                    "awsvpcConfiguration": {
                        "subnets": subnets,
                        "assignPublicIp": "ENABLED",
                        "securityGroups": security_groups
                    }
                },
                overrides={
                    "containerOverrides": [
                        {
                            "name": "ImageProcessorContainer",
                            "environment": [
                                {"name": "INPUT_BUCKET", "value": bucket},
                                {"name": "OUTPUT_BUCKET", "value": output_bucket},
                                {"name": "INPUT_KEY", "value": key},
                                {"name": "OUTPUT_KEY", "value": output_key}
                            ]
                        }
                    ]
                }
            )
            print(f"ECS run_task response: {response}")
        except Exception as e:
            print(f"Error starting ECS task: {str(e)}")
            raise
