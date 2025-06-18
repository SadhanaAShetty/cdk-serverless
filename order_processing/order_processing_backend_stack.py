from aws_cdk import (
    Stack,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_lambda as lmbd,
    aws_lambda_event_sources as event_sources,
    aws_ssm as ssm,
    aws_sns_subscriptions as subscriptions,
    aws_ses as ses,
)
from constructs import Construct


class OrderProcessingBackendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        sender = ssm.StringParameter.from_string_parameter_name(
            self,
            "SesSenderIdentityParam",
            string_parameter_name="/ses/parameter/email/sender",
        ).string_value
        receiver = ssm.StringParameter.from_string_parameter_name(
            self,
            "SesReceiverIdentityParam",
            string_parameter_name="/ses/parameter/email/receiver",
        ).string_value

        ses_service = ses.EmailIdentity.from_email_identity_name(
            self, "ExistingEmailNotification", sender
        )
        ses_receiver_service = ses.EmailIdentity.from_email_identity_name(
            self, "ExistingEmailReceiver", receiver
        )

        topic_param = ssm.StringParameter.from_string_parameter_name(
            self,
            "ImportedTopicArnParam",
            string_parameter_name="/orderprocessing/backend/sns",
        )
        topic_arn = topic_param.string_value

        sns_topic = sns.Topic.from_topic_arn(
            self, "ImportedOrderNotification", topic_arn
        )

        # sqs
        sqs_notify_queue = sqs.Queue(self, "NotifyQueue")

        sqs_inventory_queue = sqs.Queue(self, "InventoryQueue")

        sqs_shipment_queue = sqs.Queue(self, "ShipmentQueue")

        # subscription
        sns_topic.add_subscription(subscriptions.SqsSubscription(sqs_notify_queue))

        sns_topic.add_subscription(subscriptions.SqsSubscription(sqs_inventory_queue))

        sns_topic.add_subscription(subscriptions.SqsSubscription(sqs_shipment_queue))

        # lambda
        notify_lambda = lmbd.Function(
            self,
            "NotifyLambda",
            runtime=lmbd.Runtime.PYTHON_3_12,
            handler="notify.lambda_handler",
            code=lmbd.Code.from_asset("order_processing/assets/functions"),
            environment={
                "QUEUE_URL": sqs_notify_queue.queue_url,
                "sender_email": sender,
                "receiver_email": receiver,
            },
        )

        inventory_lambda = lmbd.Function(
            self,
            "InventoryLambda",
            runtime=lmbd.Runtime.PYTHON_3_12,
            handler="inventory.lambda_handler",
            code=lmbd.Code.from_asset("order_processing/assets/functions"),
            environment={
                "QUEUE_URL": sqs_inventory_queue.queue_url,
                "sender_email": sender,
                "receiver_email": receiver,
            },
        )

        shipment_lambda = lmbd.Function(
            self,
            "ShipmentLambda",
            runtime=lmbd.Runtime.PYTHON_3_12,
            handler="shipment.lambda_handler",
            code=lmbd.Code.from_asset("order_processing/assets/functions"),
            environment={
                "QUEUE_URL": sqs_shipment_queue.queue_url,
                "sender_email": sender,
                "receiver_email": receiver,
            },
        )
        ses_service.grant_send_email(notify_lambda)
        ses_service.grant_send_email(inventory_lambda)
        ses_service.grant_send_email(shipment_lambda)

        ses_receiver_service.grant_send_email(notify_lambda)
        ses_receiver_service.grant_send_email(inventory_lambda)
        ses_receiver_service.grant_send_email(shipment_lambda)

        # sqs
        sqs_notify_queue.grant_send_messages(notify_lambda)
        sqs_inventory_queue.grant_send_messages(inventory_lambda)
        sqs_shipment_queue.grant_send_messages(shipment_lambda)

        # eventsource
        notify_lambda.add_event_source(event_sources.SqsEventSource(sqs_notify_queue))
        inventory_lambda.add_event_source(
            event_sources.SqsEventSource(sqs_inventory_queue)
        )
        shipment_lambda.add_event_source(
            event_sources.SqsEventSource(sqs_shipment_queue)
        )

        # ses_identity_arn = f"arn:aws:ses:{Stack.of(self).region}:{Stack.of(self).account}:identity/{receiver_email}"
        # ses_identity_arn = f"arn:aws:ses:{Stack.of(self).region}:{Stack.of(self).account}:identity/{ses_email_identity}"

        # inventory_lambda.add_to_role_policy(
        #     iam.PolicyStatement(
        #         actions=["ses:SendEmail"],
        #         resources=[ses_identity_arn]
        #     )
        # )
