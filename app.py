#!/usr/bin/env python3
import os

import aws_cdk as cdk
from dotenv import load_dotenv


from notify_my_turn.notify_frontend import NotifyMyTurnFrontendStack
from notify_my_turn.notify_backend import NotifyMyTurnBackendStack


load_dotenv()
account = os.getenv("AWS_ACCOUNT_ID")
region = os.getenv("AWS_REGION")

app = cdk.App()

frontend_stack = NotifyMyTurnFrontendStack(app, "NotifyMyTurnFrontendStack",
                                            env =cdk.Environment(account = account, region = region),
)
backend_stack = NotifyMyTurnBackendStack(app, "NotifyMyTurnBackendStack",
                                            env =cdk.Environment(account = account, region = region),

)
backend_stack.add_dependency(frontend_stack)
app.synth()


#OrderProcessing
# from order_processing.order_processing_frontend_stack import OrderProcessingFrontendStack
# from order_processing.order_processing_backend_stack import OrderProcessingBackendStack

# frontend_stack = OrderProcessingFrontendStack(app, "OrderProcessingFrontendStack",
#    env=cdk.Environment(account=account, region=region),
#     )
# backend_stack = OrderProcessingBackendStack(app, "OrderProcessingBackendStack",
#    env=cdk.Environment(account=account, region=region)
#     )
# backend_stack.add_dependency(frontend_stack)

