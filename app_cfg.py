# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Purpose

Shows how to use the AWS SDK for Python (Boto3) with Amazon API Gateway V2 to
create a websocket chat application. The application routes all requests to an AWS
Lambda function that tracks connections in an Amazon DynamoDB table and posts
messages to other chat participants.
"""

import argparse
import os
import asyncio
import io
import json
import logging
import zipfile
import boto3
from botocore.exceptions import ClientError
import websockets
from ApiGatewayHelper import ApiGatewayHelper

logger = logging.getLogger(__name__)

def stack_deploy(stack_name, cf_resource):
    """
    Deploys prerequisite resources used by the `usage_demo` script. The resources are
    defined in the associated `setup.yaml` AWS CloudFormation script and are deployed
    as a CloudFormation stack so they can be easily managed and destroyed.

    :param stack_name: The name of the CloudFormation stack.
    :param cf_resource: A Boto3 CloudFormation resource.
    """
    print(f"Creating and deploying stack {stack_name}.")
    with open('setup.yaml') as setup_file:
        setup_template = setup_file.read()
    stack = cf_resource.create_stack(
        StackName=stack_name,
        TemplateBody=setup_template,
        Capabilities=['CAPABILITY_NAMED_IAM'])
    print("Waiting for stack to deploy. This typically takes about 1 minute.")
    waiter = cf_resource.meta.client.get_waiter('stack_create_complete')
    waiter.wait(StackName=stack.name)
    stack.load()
    print(f"Stack status: {stack.stack_status}")
    print("Created resources:")
    for resource in stack.resource_summaries.all():
        print(f"\t{resource.resource_type}, {resource.physical_resource_id}")

def create_apirest(
        api_gateway:ApiGatewayHelper
        , account
        , lambda_role_name
        , iam_resource
        , lambda_function_name
        , lambda_client
        ):
    """
    use the API Gateway API to create and deploy a websocket API that is
    backed by a Lambda function.
    Info:https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/apigateway.html#APIGateway.Client.create_rest_api

    :param sock_gateway: The API Gateway websocket wrapper object.
    :param account: The AWS account number of the current account.
    :param lambda_role_name: The name of an existing role that is associated with
                             the Lambda function. A policy is attached to this role
                             that lets the Lambda function call the API Gateway
                             Management API.
    :param iam_resource: A Boto3 IAM resource.
    :param lambda_function_name: The name of an existing Lambda function that can
                                 handle websocket requests.
    :param lambda_client: A Boto3 Lambda client.
    """
    print(f"Creating REST API {api_gateway.api_name}.")

    lambda_info=lambda_client.get_function(FunctionName=lambda_function_name)
    lambda_function_arn=lambda_info['Configuration']['FunctionArn']

    api_id=api_gateway.create_rest_api(
        apigateway_client=api_gateway.apig_v1_client
        , api_name= api_gateway.api_name
        , api_base_path='{participant_id+}'
        , api_stage=api_gateway.stage
        , account_id=account
        , lambda_client=lambda_client
        , lambda_function_arn=lambda_function_arn
        )
    return api_id

def create_lambda(
        api_gateway:ApiGatewayHelper, account, lambda_role_name, iam_resource, lambda_function_name,
        lambda_client):
    """
    :param api_gateway: The API Gateway wrapper object.
    :param account: The AWS account number of the current account.
    :param lambda_role_name: The name of an existing role that is associated with
                             the Lambda function. A policy is attached to this role
                             that lets the Lambda function call the API Gateway
                             Management API.
    :param iam_resource: A Boto3 IAM resource.
    :param lambda_function_name: The name of an existing Lambda function that can
                                 handle websocket requests.
    :param lambda_client: A Boto3 Lambda client.
    """
    lambda_file_name = 'lambda_websocket.py'
    print(f"Updating Lambda function {lambda_function_name} with code file "
          f"{lambda_file_name}.")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zipped:
        zipped.write(lambda_file_name)
    buffer.seek(0)
    try:
        lambda_func = lambda_client.update_function_code(
            FunctionName=lambda_function_name, ZipFile=buffer.read())
    except ClientError:
        logger.exception("Couldn't update Lambda function %s.", lambda_function_name)
        raise

    return lambda_func

def create_api_websocket(api_gateway:ApiGatewayHelper
        , account
        , lambda_role_name
        , iam_resource
        , lambda_client
        , lambda_func
        ):

    print(f"Creating websocket API {api_gateway.api_name}.")
    api_gateway.create_api('$request.body.action')

    print("Adding permission to let the Lambda function send messages to "
          "websocket connections.")
    api_gateway.add_connection_permissions(account, lambda_role_name, iam_resource)

    print("Adding routes to the API and integrating with the Lambda function.")
    for route in ['$connect', '$disconnect', 'sendmessage']:
        api_gateway.add_route_and_integration(route, lambda_func, lambda_client)

    print("Deploying the API to stage test.")
    chat_uri = api_gateway.deploy_api(api_gateway.stage)

    print("Try it yourself! Connect a websocket client to the URI to start as chat.")
    print(f"\tChat URI: {chat_uri}")
    print("Send messages in this format:")
    print('\t{"space":"space_name", "action": "sendmessage", "msg": "YOUR MESSAGE HERE"}')


def update_lambda(lambda_function_name,lambda_file_name,
                    lambda_client
                    , extraDirs=[]):
    """
    Update Lambda function.
    :param lambda_function_name: The name of an existing Lambda function
    :param lambda_file_name: The lambda_file_name of an existing Lambda function          
    :param lambda_client: A Boto3 Lambda client.
    :param extraDirs: An array with dirs to include. This is useful for lambda functions that needs extra libraries
    """

    print(f"Updating Lambda function {lambda_function_name} with code file "
          f"{lambda_file_name}.")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zipped:        
        zipped.write(lambda_file_name)
        if (len(extraDirs)>0):
            for path in extraDirs:
                zipdir(path, zipped)
        
    buffer.seek(0)
    try:
        lambda_func = lambda_client.update_function_code(
            FunctionName=lambda_function_name, ZipFile=buffer.read())
        return lambda_func
    except ClientError:
        logger.exception("Couldn't update Lambda function %s.", lambda_function_name)
        raise

def zipdir(path, ziph:zipfile.ZipFile):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file), 
                       os.path.relpath(os.path.join(root, file), 
                                       os.path.join(path, '..')))


async def chat_demo(uri):
    """
    Shows how to use the deployed websocket API to connect users to the chat
    application and send messages to them.

    The demo connects three passive users who listen for messages, and one active
    user who sends messages to the other users through the websocket API.

    :param uri: The websocket URI of the chat application.
    """
    async def receiver(name,space):
        
        async with websockets.connect(f'{uri}?participant_id={name}&space={space}') as socket:
            print(f"> Connected to {uri}. Hello, {name}!")
            msg = ''
            while 'Bye' not in msg:
                msg = await socket.recv()
                print(f"> {name} got message: {msg}")

    async def sender(name,space):
        async with websockets.connect(f'{uri}?participant_id={name}&space={space}') as socket:
            for msg in ("Server send first message", "Server send second message..."):
                await asyncio.sleep(1)
                print(f"< {name}: {msg}")
                await socket.send(json.dumps({  'participant_id': 'id1' ,'space':space,'action': 'sendmessage', 'msg': msg}))

    await asyncio.gather(
        *(receiver(user,"TEST") for user in ('id1', 'id2', 'id3')),
        sender('ADMIN','TEST'))


def stack_destroy(api_gateway:ApiGatewayHelper, lambda_role_name, iam_resource, stack, cf_resource):
    """
    Removes the connection permission policy added to the Lambda role, deletes the
    API Gateway websocket API, destroys the resources managed by the CloudFormation
    stack, and deletes the CloudFormation stack itself.

    :param sock_gateway: The API Gateway websocket wrapper object.
    :param lambda_role_name: The name of the Lambda role that has the connection
                             permission policy attached.
    :param iam_resource: A Boto3 IAM resource.
    :param stack: The CloudFormation stack that manages the demo resources.
    :param cf_resource: A Boto3 CloudFormation resource.
    """
    print(f"Deleting websocket API {api_gateway.api_name}.")
    api_gateway.remove_connection_permissions(iam_resource.Role(lambda_role_name))
    api_gateway.delete_websocket_api()
    print(f"Deleting REST API {api_gateway.api_name}.")
    api_gateway.delete_rest_api()

    print(f"Deleting stack {stack.name}.")
    stack.delete()
    print("Waiting for stack removal.")
    waiter = cf_resource.meta.client.get_waiter('stack_delete_complete')
    waiter.wait(StackName=stack.name)
    print("Stack delete complete.")


def main():
    parser = argparse.ArgumentParser(
        description="Create websocket app. Run this script "
                    "with the 'deploy-stack' flag to deploy prerequisite resources, with the "
                    "'deploy-lbd' flag to create and deploy lambda with websocket API" 
                    ", 'deploy-rest' flag to create and deploy rest post api,"
                    "and with the 'chat' flag to see an automated demo of using the "
                    "chat API from a websocket client."
                    "Use 'lbd-update' to update lambda function only, not the zip."
                    "Run with the 'destroy-stack' flag to "
                    "clean up all resources.")
    parser.add_argument(
        'action', choices=['deploy-stack','deploy-rest', 'deploy-lbd', 'lbd-update', 'chat', 'destroy-stack'],
        help="Indicates the action the script performs.")
    args = parser.parse_args()

    print('-'*88)
    print("Welcome to the Amazon API Gateway websocket!")
    print('-'*88)

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    #session = boto3.Session(profile_name='your profile to use if you have several')
    session = boto3.Session()
    cf_resource = session.resource('cloudformation')
    stack = cf_resource.Stack('app-apigateway-websocket-service-v1')
    #sock_gateway = ApiGatewayWebsocket(stack.name, boto3.client('apigatewayv2'))
    api_gateway = ApiGatewayHelper(stack.name, boto3.client('apigatewayv2'))
    api_gateway.apig_v1_client= session.client('apigateway')
    api_gateway.stage="latest"
    lambda_file_name = 'lambda_websocket.py'

    if args.action == 'deploy-stack':
        print("Deploying prerequisite resources for the app.")
        stack_deploy(stack.name, cf_resource)
        print("run the script again with the 'deploy-rest' and then 'deploy-lbd' flag.")

    elif args.action == 'chat':
        print("Starting websocket chat demo.")
        _, api_endpoint = api_gateway.get_websocket_api_info()
        print ("API-ENDPOINT", api_endpoint)
        asyncio.run(chat_demo(f'{api_endpoint}/{api_gateway.stage}'))

    elif args.action in ['deploy-rest','deploy-lbd', 'destroy-stack','lbd-update']:
        lambda_role_name = None
        lambda_function_name = None
        for resource in stack.resource_summaries.all():
            if resource.resource_type == 'AWS::IAM::Role':
                lambda_role_name = resource.physical_resource_id
            elif resource.resource_type == 'AWS::Lambda::Function':
                lambda_function_name = resource.physical_resource_id

        if args.action == 'deploy-rest':
            print("Amazon API Gateway to create a rest application.")
            account = session.client('sts').get_caller_identity().get('Account')
            create_apirest( api_gateway, account, lambda_role_name, session.resource('iam'),
                lambda_function_name, session.client('lambda'))

        elif args.action == 'deploy-lbd':
            print("Amazon API Gateway to create a websocket application.")
            account = session.client('sts').get_caller_identity().get('Account')
            lambda_func=create_lambda(
                api_gateway, account, lambda_role_name, session.resource('iam'),
                lambda_function_name, session.client('lambda'))

            create_api_websocket( api_gateway, account, lambda_role_name, session.resource('iam'),
                 session.client('lambda'),lambda_func)

            print("To see an automated demo of how to use the API from a "
                  "websocket client, run the script again with the 'chat' flag.")

        elif args.action == 'lbd-update':
            print("Upgrading lambda")
            account = session.client('sts').get_caller_identity().get('Account')
            pathExtras=["package"]
            lambda_func=update_lambda(lambda_function_name,lambda_file_name, session.client('lambda'),pathExtras)

        elif args.action == 'destroy-stack':
            print("Destroying AWS resources created.")
            stack_destroy(
                api_gateway, lambda_role_name, session.resource('iam'), stack,
                cf_resource)
            print("All destroyed")

    print('-'*88)


if __name__ == '__main__':
    main()
