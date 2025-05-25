#!/usr/bin/env python3
import os

import aws_cdk as cdk
from dotenv import load_dotenv

# from order_processing.order_processing_frontend_stack import OrderProcessingFrontendStack
# from order_processing.order_processing_backend_stack import OrderProcessingBackendStack
from notify_my_turn.notify_my_turn import NotifyMyTurnStack





load_dotenv()
account = os.getenv("AWS_ACCOUNT_ID")
region = os.getenv("AWS_REGION")

app = cdk.App()

# frontend_stack = OrderProcessingFrontendStack(app, "OrderProcessingFrontendStack",
#    env=cdk.Environment(account=account, region=region),
#     )
# backend_stack = OrderProcessingBackendStack(app, "OrderProcessingBackendStack",
#    env=cdk.Environment(account=account, region=region)
#     )
# backend_stack.add_dependency(frontend_stack)

stack = NotifyMyTurnStack(app, "NotifyMyTurnStack", 
                                            env =cdk.Environment(account = account, region = region),
)




app.synth()






