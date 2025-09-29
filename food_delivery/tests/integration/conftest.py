import os
import boto3
import pytest
import time
import jwt  

APPLICATION_STACK_NAME = os.getenv("food_delivery_stack", "FoodDeliveryStack")
globalConfig = {}

def get_stack_outputs(stack_name):
    result = {}
    cf_client = boto3.client("cloudformation")
    cf_response = cf_client.describe_stacks(StackName=stack_name)
    outputs = cf_response["Stacks"][0]["Outputs"]
    for output in outputs:
        key = output.get("ExportName") or output.get("OutputKey")
        result[key] = output["OutputValue"]
    return result


def create_cognito_accounts():
    result = {}
    sm_client = boto3.client("secretsmanager")
    idp_client = boto3.client("cognito-idp")


    result["regularUserName"] = "regularUser@example.com"
    result["regularUserPassword"] = sm_client.get_random_password(RequireEachIncludedType=True)["RandomPassword"]

    try:
        idp_client.admin_delete_user(
            UserPoolId=globalConfig["UserPool"],
            Username=result["regularUserName"],
        )
    except idp_client.exceptions.UserNotFoundException:
        pass

    idp_client.admin_create_user(
        UserPoolId=globalConfig["UserPool"],
        Username=result["regularUserName"],
        TemporaryPassword=result["regularUserPassword"],
        UserAttributes=[
            {"Name": "email", "Value": result["regularUserName"]},
            {"Name": "email_verified", "Value": "true"},
        ],
        MessageAction="SUPPRESS"
    )

    idp_client.admin_set_user_password(
        UserPoolId=globalConfig["UserPool"],
        Username=result["regularUserName"],
        Password=result["regularUserPassword"],
        Permanent=True
    )

    auth_resp = idp_client.initiate_auth(
        ClientId=globalConfig["UserPoolClient"],
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": result["regularUserName"],
            "PASSWORD": result["regularUserPassword"],
        },
    )

    result["regularUserIdToken"] = auth_resp["AuthenticationResult"]["IdToken"]
    result["regularUserAccessToken"] = auth_resp["AuthenticationResult"]["AccessToken"]
    result["regularUserRefreshToken"] = auth_resp["AuthenticationResult"]["RefreshToken"]

    
    result["adminUserName"] = "adminUser@example.com"
    result["adminUserPassword"] = sm_client.get_random_password(RequireEachIncludedType=True)["RandomPassword"]

    try:
        idp_client.admin_delete_user(
            UserPoolId=globalConfig["UserPool"],
            Username=result["adminUserName"],
        )
    except idp_client.exceptions.UserNotFoundException:
        pass

    idp_client.admin_create_user(
        UserPoolId=globalConfig["UserPool"],
        Username=result["adminUserName"],
        TemporaryPassword=result["adminUserPassword"],
        UserAttributes=[
            {"Name": "email", "Value": result["adminUserName"]},
            {"Name": "email_verified", "Value": "true"},
        ],
        MessageAction="SUPPRESS"
    )

    idp_client.admin_set_user_password(
        UserPoolId=globalConfig["UserPool"],
        Username=result["adminUserName"],
        Password=result["adminUserPassword"],
        Permanent=True
    )


    idp_client.admin_add_user_to_group(
        UserPoolId=globalConfig["UserPool"],
        Username=result["adminUserName"],
        GroupName=globalConfig["UserPoolAdminGroup"],
    )


    time.sleep(5)


    auth_resp = idp_client.initiate_auth(
        ClientId=globalConfig["UserPoolClient"],
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": result["adminUserName"],
            "PASSWORD": result["adminUserPassword"],
        },
    )
    id_token = auth_resp["AuthenticationResult"]["IdToken"]
    decoded = jwt.decode(id_token, options={"verify_signature": False})
    if "cognito:groups" not in decoded or "admin" not in decoded["cognito:groups"]:
        raise RuntimeError("Admin user token does not contain 'admin' group yet!")

    result["adminUserIdToken"] = id_token
    result["adminUserAccessToken"] = auth_resp["AuthenticationResult"]["AccessToken"]
    result["adminUserRefreshToken"] = auth_resp["AuthenticationResult"]["RefreshToken"]

    return result


def clear_dynamo_tables():
    db_client = boto3.client("dynamodb")
    table_name = globalConfig["UsersTable"]

    response = db_client.scan(
        TableName=table_name,
        ProjectionExpression="userId, orderId"
    )

    for item in response.get("Items", []):
        db_client.delete_item(
            TableName=table_name,
            Key={
                "userId": item["userId"],
                "orderId": item["orderId"]
            }
        )


@pytest.fixture(scope="session")
def global_config():
    global globalConfig
    globalConfig.update(get_stack_outputs(APPLICATION_STACK_NAME))
    globalConfig.update(create_cognito_accounts())
    clear_dynamo_tables()
    return globalConfig
