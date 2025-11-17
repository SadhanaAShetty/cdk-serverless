from aws_cdk import (
    Duration,
    aws_lambda as lmbda,
    aws_sqs as sqs,
)
from constructs import Construct
from cdk_nag import NagSuppressions


class LambdaConstruct(Construct):
    """
    A clean reusable Python Lambda construct that removes boilerplate.

    Defaults:
    - Python 3.13 runtime
    - DLQ automatically created
    - Tracing disabled with cdk-nag suppression
    - 10s timeout
    - 256 MB memory
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        function_name: str,
        handler: str,
        code_path: str,
        env: dict = None,
        layers: list = None,
        runtime: lmbda.Runtime = lmbda.Runtime.PYTHON_3_13,
        timeout: int = 10,
        memory: int = 256,
    ):
        super().__init__(scope, id)

   
        dlq = sqs.Queue(
            self,
            "DLQ",
            queue_name=f"{function_name}-dlq",
            enforce_ssl=True
        )

        # Suppress redrive policy warning for this DLQ
        NagSuppressions.add_resource_suppressions(
            dlq,
            suppressions=[
                {
                    "id": "Serverless-SQSRedrivePolicy",
                    "reason": (
                        "This DLQ is sufficient for the current workload. Redrive to another queue "
                        "is not necessary for this project."
                    )
                }
            ]
        )

       
        self.lambda_fn = lmbda.Function(
            self,
            "Lambda",
            function_name=function_name,
            handler=handler,
            runtime=runtime,
            code=lmbda.Code.from_asset(code_path),
            timeout=Duration.seconds(timeout),
            memory_size=memory,
            environment=env or {},
            layers=layers or [],
            dead_letter_queue=dlq,              
            tracing=lmbda.Tracing.DISABLED,  
        )

        # NAG Suppressions for Lambda function
        NagSuppressions.add_resource_suppressions(
            self.lambda_fn,
            suppressions=[
                {
                    "id": "Serverless-LambdaTracing",
                    "reason": (
                        "X-Ray tracing is intentionally disabled to reduce costs. "
                        "CloudWatch Logs with Powertools structured logging provides sufficient observability."
                    )
                }
            ]
        )

        # NAG Suppressions for Lambda IAM role
        if self.lambda_fn.role:
            NagSuppressions.add_resource_suppressions(
                self.lambda_fn.role,
                suppressions=[
                    {
                        "id": "AwsSolutions-IAM4",
                        "reason": (
                            "AWSLambdaBasicExecutionRole is the minimal AWS managed policy providing "
                            "only CloudWatch Logs access, equivalent to a least-privilege custom role."
                        )
                    },
                    {
                        "id": "AwsSolutions-IAM5",
                        "reason": (
                            "AWSLambdaBasicExecutionRole provides only CloudWatch logging permissions, "
                            "equivalent to a custom role with minimal privileges."
                        )
                    },
                    {
                        "id": "Serverless-LambdaTracing",
                        "reason": (
                            "Tracing is intentionally disabled for cost-sensitive Lambdas."
                        )
                    }
                ]
            )
