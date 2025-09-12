import boto3
import os
import pytest

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

    
    sm_response = sm_client.get_random_password(RequireEachIncludedType=True)
    result["regularUserName"] = "regularUser@example.com"
    result["regularUserPassword"] = sm_response["RandomPassword"]

    try:
        idp_client.admin_delete_user(
            UserPoolId=globalConfig["UserPoolOutput"],
            Username=result["regularUserName"],
        )
    except idp_client.exceptions.UserNotFoundException:
        print("Regular user hasn’t been created previously")

    idp_response = idp_client.sign_up(
        ClientId=globalConfig["UserPoolClientOutput"],
        Username=result["regularUserName"],
        Password=result["regularUserPassword"],
        UserAttributes=[{"Name": "name", "Value": result["regularUserName"]}],
    )
    result["regularUserSub"] = idp_response["UserSub"]

    idp_client.admin_confirm_sign_up(
        UserPoolId=globalConfig["UserPoolOutput"],
        Username=result["regularUserName"],
    )

    idp_response = idp_client.initiate_auth(
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": result["regularUserName"],
            "PASSWORD": result["regularUserPassword"],
        },
        ClientId=globalConfig["UserPoolClientOutput"],
    )
    result["regularUserIdToken"] = idp_response["AuthenticationResult"]["IdToken"]
    result["regularUserAccessToken"] = idp_response["AuthenticationResult"]["AccessToken"]
    result["regularUserRefreshToken"] = idp_response["AuthenticationResult"]["RefreshToken"]

    # Admin user
    sm_response = sm_client.get_random_password(RequireEachIncludedType=True)
    result["adminUserName"] = "adminUser@example.com"
    result["adminUserPassword"] = sm_response["RandomPassword"]

    try:
        idp_client.admin_delete_user(
            UserPoolId=globalConfig["UserPoolOutput"],
            Username=result["adminUserName"],
        )
    except idp_client.exceptions.UserNotFoundException:
        print("Admin user hasn’t been created previously")

    idp_response = idp_client.sign_up(
        ClientId=globalConfig["UserPoolClientOutput"],
        Username=result["adminUserName"],
        Password=result["adminUserPassword"],
        UserAttributes=[{"Name": "name", "Value": result["adminUserName"]}],
    )
    result["adminUserSub"] = idp_response["UserSub"]

    idp_client.admin_confirm_sign_up(
        UserPoolId=globalConfig["UserPoolOutput"],
        Username=result["adminUserName"],
    )

    idp_client.admin_add_user_to_group(
        UserPoolId=globalConfig["UserPoolOutput"],
        Username=result["adminUserName"],
        GroupName=globalConfig["UserPoolAdminGroupOutput"],
    )

    idp_response = idp_client.initiate_auth(
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": result["adminUserName"],
            "PASSWORD": result["adminUserPassword"],
        },
        ClientId=globalConfig["UserPoolClientOutput"],
    )
    result["adminUserIdToken"] = idp_response["AuthenticationResult"]["IdToken"]
    result["adminUserAccessToken"] = idp_response["AuthenticationResult"]["AccessToken"]
    result["adminUserRefreshToken"] = idp_response["AuthenticationResult"]["RefreshToken"]

    return result


def clear_dynamo_tables():
    db_client = boto3.client("dynamodb")
    db_response = db_client.scan(
        TableName=globalConfig["UsersTableOutput"],
        AttributesToGet=["user_id"],
    )
    for item in db_response["Items"]:
        db_client.delete_item(
            TableName=globalConfig["UsersTableOutput"],
            Key={"user_id": {"S": item["user_id"]["S"]}},
        )


@pytest.fixture(scope="session")
def global_config():
    global globalConfig
    globalConfig.update(get_stack_outputs(APPLICATION_STACK_NAME))
    globalConfig.update(create_cognito_accounts())
    clear_dynamo_tables()
    return globalConfig
