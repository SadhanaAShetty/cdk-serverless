import boto3
import os
import json
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.batch import (
    BatchProcessor,
    EventType,
    process_partial_response,
)
from aws_lambda_powertools.utilities.data_classes.kinesis_stream_event import (
    KinesisStreamRecord,
)
from aws_lambda_powertools.utilities.typing import LambdaContext


processor = BatchProcessor(event_type=EventType.KinesisDataStreams)
tracer = Tracer()
logger = Logger()


client = boto3.client("kinesis")
STREAM_NAME = os.environ.get("KINESIS_STREAM_NAME", "LocationStream")


@tracer.capture_method
def record_handler(record: KinesisStreamRecord):
  
    logger.info(f"Received record: {record.kinesis.data_as_text}")

  
    payload: dict = record.kinesis.data_as_json()
    logger.info(f"Payload: {payload}")

    
    response = client.put_record(
        StreamName=STREAM_NAME,
        Data=json.dumps(payload).encode("utf-8"),
        PartitionKey=payload.get("userId", "default"),
    )
    logger.info(f"Put record response: {response}")



@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event, context: LambdaContext):
    return process_partial_response(
        event=event, record_handler=record_handler, processor=processor, context=context
    )
