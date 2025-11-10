from aws_cdk import (
    Stack, Duration,RemovalPolicy,
    CfnOutput,
    aws_lambda as lmbda,
    aws_kinesis as kinesis,
    aws_lambda_event_sources as lambda_event_sources,
    aws_events as events,
    aws_events_targets as targets,
    aws_dynamodb as dynamodb
)
from constructs import Construct
from constructs.ddb import DynamoTable
from cdk_nag import NagSuppressions

class FoodDeliveryDataStream(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        #Kinesis Stream
        kinesis_stream = kinesis.Stream(
            self,
            "LocationStream",               
            stream_name="LocationStream",  
            retention_period=Duration.hours(24),  
            stream_mode=kinesis.StreamMode.ON_DEMAND  
        )

        #DynamoDB table for rider positions
        riders_position_table = DynamoTable(
            self,
            "RidersPositionTable",
            table_name="RidersPositionTable",
            partition_key="rider_id"
        )
        
        #PowerTools Layer
        powertools_layer = lmbda.LayerVersion.from_layer_version_arn(
            self,
            "PowertoolsLayer",
            "arn:aws:lambda:eu-west-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:79"
        )

        #Kinesis Producer Lambda
        kinesis_producer = lmbda.Function(
            self, "KinesisProducer",
            function_name="kinesis_producer",
            runtime=lmbda.Runtime.PYTHON_3_13,
            handler="kinesis_producer.lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/data_stream_assets"),
            layers=[powertools_layer],
            environment={
                "KINESIS_STREAM_NAME": kinesis_stream.stream_name
            },
            timeout=Duration.seconds(30)
        )

        #Kinesis Consumer Lambda (UpdateRiderLocation)
        kinesis_consumer = lmbda.Function(
            self, "UpdateRiderLocation",
            function_name="UpdateRiderLocation",  
            runtime=lmbda.Runtime.PYTHON_3_13,
            handler="kinesis_consumer.lambda_handler",
            code=lmbda.Code.from_asset("food_delivery/data_stream_assets"),
            layers=[powertools_layer],
            environment={
                "KINESIS_STREAM_NAME": kinesis_stream.stream_name,
                "TABLE_NAME": riders_position_table.table_name
            },
            timeout=Duration.seconds(30)
        )

        #EventBridge Simulator 
        simulator_rule = events.Rule(
            self,
            "FifteenMinuteSchedule",
            rule_name="FifteenMinuteSchedule", 
            schedule=events.Schedule.rate(Duration.minutes(15)),
            enabled=False  
        )

        #Add producer as target for the simulator
        simulator_rule.add_target(
            targets.LambdaFunction(
                kinesis_producer,
                event=events.RuleTargetInput.from_object({
                    "simulator": True,
                    "location_data": {
                        "source": "eventbridge_simulator"
                    }
                })
            )
        )

        #Grant permissions
        kinesis_stream.grant_write(kinesis_producer)
        kinesis_stream.grant_read(kinesis_consumer)
        riders_position_table.grant_write_data(kinesis_consumer)

        #Add Kinesis as event source for consumer Lambda
        kinesis_consumer.add_event_source(
            lambda_event_sources.KinesisEventSource(
                kinesis_stream,
                batch_size=10,
                starting_position=lmbda.StartingPosition.LATEST
            )
        )

        #Nag Suppression
        lambda_functions = [
            kinesis_consumer,
            kinesis_producer
        ]

        NagSuppressions.add_resource_suppressions(
            [fn.role for fn in lambda_functions if fn.role],
            suppressions=[{
                "id": "AwsSolutions-IAM4",
                "reason": "AWSLambdaBasicExecutionRole is the minimal AWS managed policy providing only CloudWatch Logs access, equivalent to a least-privilege custom role."
            }],
            apply_to_children=True
        )

        # Outputs
        CfnOutput(self, "KinesisStreamName", value=kinesis_stream.stream_name)
        CfnOutput(self, "KinesisStreamArn", value=kinesis_stream.stream_arn)
        CfnOutput(self, "ProducerFunctionName", value=kinesis_producer.function_name)
        CfnOutput(self, "ConsumerFunctionName", value=kinesis_consumer.function_name)
        CfnOutput(self, "DynamoDBTableName", value=riders_position_table.table_name)
        CfnOutput(self, "SimulatorRuleName", value=simulator_rule.rule_name)