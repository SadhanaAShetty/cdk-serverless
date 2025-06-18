from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_lambda as lmbda,
    aws_s3 as s3,
    aws_iam as iam,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_s3_notifications as s3n,
    aws_ecr as ecr,
    aws_ecr_assets as ecr_assets,
    aws_logs as logs
)
from constructs import Construct

class ImageProcessingStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


        upload_bucket = s3.Bucket(self, "RawImagesBucket",
                                  removal_policy=RemovalPolicy.DESTROY,
                                  auto_delete_objects=True)
        
        processed_bucket = s3.Bucket(self, "ProcessedImagesBucket",
                                     removal_policy=RemovalPolicy.DESTROY,
                                     auto_delete_objects=True)


        vpc = ec2.Vpc.from_lookup(self, "DefaultVpc", is_default=True)


        fargate_sg = ec2.SecurityGroup(self, "FargateSG", vpc=vpc, allow_all_outbound=True)


        cluster = ecs.Cluster(self, "ImageProcessorCluster", vpc=vpc)

        docker_image_asset = ecr_assets.DockerImageAsset(self, "ImageProcessorImage",
                                                        directory="image_processing") 

        task_definition = ecs.FargateTaskDefinition(self, "ImageProcessorTaskDef",
                                                   cpu=256,
                                                   memory_limit_mib=512)
        log_group = logs.LogGroup(
            self, "ImageProcessorLogGroup",
            log_group_name=f"/ecs/{task_definition.family}"
        )

        container = task_definition.add_container(
            "ImageProcessorContainer",
            image=ecs.ContainerImage.from_docker_image_asset(docker_image_asset),
            logging=ecs.LogDrivers.aws_logs(stream_prefix="ImageProcessor",log_group=log_group),
            environment={
                "INPUT_BUCKET": upload_bucket.bucket_name,
                "OUTPUT_BUCKET": processed_bucket.bucket_name
            }
        )

        upload_bucket.grant_read(task_definition.task_role)
        processed_bucket.grant_write(task_definition.task_role)

        task_definition.add_to_execution_role_policy(iam.PolicyStatement(
            actions=[
                "ecr:GetAuthorizationToken",
                "ecr:BatchGetImage",
                "ecr:GetDownloadUrlForLayer",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            resources=["*"]
        ))

        task_definition.task_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "s3:GetObject",
                "s3:PutObject"
            ],
            resources=["*"]
        ))

        trigger_function = lmbda.Function(
            self, "TriggerFargateTask",
            runtime=lmbda.Runtime.PYTHON_3_12,
            handler="lambda_trigger.lambda_handler",
            code=lmbda.Code.from_asset("image_processing/assets/functions"),
            environment={
                "CLUSTER": cluster.cluster_name,
                "INPUT_BUCKET": upload_bucket.bucket_name, 
                "OUTPUT_BUCKET": processed_bucket.bucket_name,
                "TASK_DEF_ARN": task_definition.task_definition_arn,
                "SUBNETS": ",".join([subnet.subnet_id for subnet in vpc.public_subnets]),
                "SECURITY_GROUPS": fargate_sg.security_group_id,
            },
            timeout=Duration.seconds(60)
        )

        trigger_function.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "ecs:RunTask",
                "iam:PassRole",
                "ecs:DescribeClusters",
                "ecs:DescribeTasks",
                "ec2:DescribeNetworkInterfaces",
                "ec2:DescribeSubnets",
                "ec2:DescribeSecurityGroups",
            ],
            resources=["*"]
        ))

        task_definition.task_role.grant_pass_role(trigger_function.role)

        
        upload_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(trigger_function)
        )
