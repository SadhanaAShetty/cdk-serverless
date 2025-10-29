from aws_cdk import (
    Stack, Duration,
    CfnOutput, Fn,
    aws_events as events,
    aws_lambda as lmbda,
    aws_events_targets as targets,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_kinesis as kinesis
)
from constructs import Construct

class FoodDeliveryDataStream(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)


        kinesis_stream = kinesis.Stream(
            self,
            "KinesisStream",               
            stream_name="LocationStream",  
            retention_period=Duration.hours(24),  
            stream_mode=kinesis.StreamMode.ON_DEMAND  
        )

        powertools_layer = lmbda.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79"
        )

        kinesis_producer = lmbda.Function(
            self, "KinesisProducer",
            function_name="kinesis_producer",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="kinesis_producer.lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/data_stream_assets"),
            layers=[powertools_layer],
            environment={
            },
            timeout=Duration.seconds(10)
        )

        kinesis_consumer = lmbda.Function(
            self, "KinesisConsumer",
            function_name="kinesis_consumer",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="kinesis_consumer .lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/data_stream_assets"),
            layers=[powertools_layer],
            environment={
            },
            timeout=Duration.seconds(10)
        )

        kinesis_stream.grant_write(kinesis_producer)