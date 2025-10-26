#!/usr/bin/env python3
import os

import aws_cdk as cdk
from dotenv import load_dotenv

# from order_processing.order_processing_frontend_stack import OrderProcessingFrontendStack
# from order_processing.order_processing_backend_stack import OrderProcessingBackendStack
# from notify_my_turn.notify_my_turn import NotifyMyTurnStack


# from loan_processor2.loan_processing_stack import LoanProcessingStack
# from loan_processor3.loan_processing_stack import LoanProcessingStack
# from image_processing.image_processing_stack import ImageProcessingStack
# from loan_processing.loan_processing_stack import LoanProcessingStack
# from food_delivery.food_delivery_stack import FoodDeliveryStack
from food_delivery.food_delivery_user_profile_stack import AddressStack
# from food_delivery.food_delivery_favorites_stack import FavoritesStack




load_dotenv()
account = os.getenv("AWS_ACCOUNT_ID")
region = os.getenv("AWS_REGION")

app = cdk.App()
# #OrderProcessing
# frontend_stack = OrderProcessingFrontendStack(app, "OrderProcessingFrontendStack",
#    env=cdk.Environment(account=account, region=region),
#     )
# backend_stack = OrderProcessingBackendStack(app, "OrderProcessingBackendStack",
#    env=cdk.Environment(account=account, region=region)
#     )
# backend_stack.add_dependency(frontend_stack)

# notify_my_turn
# stack = NotifyMyTurnStack(app, "NotifyMyTurnStack",
#                                             env =cdk.Environment(account = account, region = region),
# )


#loan Processing
# stack = LoanProcessingStack(app, "LoanProcessingStack",
#         env=cdk.Environment(account=account, region=region),
#             )


# loan Processing
# stack = LoanProcessingStack(
#     app,
#     "LoanProcessingStack",
#     env=cdk.Environment(account=account, region=region),
# )


# stack = ImageProcessingStack(app, "ImageProcessingStack",
#                              env =cdk.Environment(account =account, region = region),
#                              )

# stack_main = FoodDeliveryStack(app, "FoodDeliveryStack",
#                              env =cdk.Environment(account =account, region = region),
#                              )
stack_user = AddressStack(app, "AddressStack",
                          env =cdk.Environment(account =account, region = region),
                            )
# stack_address = FavoritesStack(app, "FavoritesStack",
#                             env =cdk.Environment(account =account, region = region),
# )
# stack_address.add_dependency(stack_main)


app.synth()
