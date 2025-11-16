from aws_cdk import (
    Duration,
    aws_lambda as lmbda,
)
from constructs import Construct


class LambdaConstruct(Construct):
    """
    A clean reusable Python Lambda construct that removes boilerplate.
    
    Defaults:
    - Python 3.13 runtime
    - 10s timeout
    - 256 MB memory
    - Simple env={} dict
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
        )
