import argparse
import asyncio
import io
import json
import logging
import websockets
import zipfile
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class ApiGatewayHelper:
    """Encapsulates Amazon API Gateway websocket functions."""
    def __init__(self, api_name, apig2_client):
        """
        :param api_name: The name of the websocket API.
        :param apig2_client: A Boto3 API Gateway V2 client.
        """
        self.apig2_client = apig2_client
        self.apig_v1_client = None
        self.api_name = api_name
        self.api_id = None
        self.api_endpoint = None
        self.api_arn = None
        self.stage = None
        self.root_id = None


    permission_policy_suffix = 'manage-connections'

    def create_api(self, route_selection):
        """
        Creates a websocket API. The newly created API has no routes.

        :param route_selection: Used to determine route selection. For example,
                                specifying 'request.body.action' looks for an 'action'
                                field in the request body and uses the value of that
                                field to route requests.
        :return: The ID of the newly created API.
        """
        try:
            response = self.apig2_client.create_api(
                Name=self.api_name,
                ProtocolType='WEBSOCKET',
                RouteSelectionExpression=route_selection)
            self.api_id = response['ApiId']
            self.api_endpoint = response['ApiEndpoint']
            logger.info(
                "Created websocket API %s with ID %s.", self.api_name, self.api_id)
        except ClientError:
            logger.exception("Couldn't create websocket API %s.", self.api_name)
            raise
        else:
            return self.api_id

    def create_rest_api(self,
            apigateway_client, api_name, api_base_path, api_stage,
            account_id, lambda_client, lambda_function_arn):
        """
        Creates a REST API in Amazon API Gateway. The REST API is backed by the specified
        AWS Lambda function.

        The following is how the function puts the pieces together, in order:
        1. Creates a REST API in Amazon API Gateway.
        2. Creates a '/demoapi' resource in the REST API.
        3. Creates a method that accepts all HTTP actions and passes them through to
        the specified AWS Lambda function.
        4. Deploys the REST API to Amazon API Gateway.
        5. Adds a resource policy to the AWS Lambda function that grants permission
        to let Amazon API Gateway call the AWS Lambda function.

        :param apigateway_client: The Boto3 Amazon API Gateway client object.
        :param api_name: The name of the REST API.
        :param api_base_path: The base path part of the REST API URL.
        :param api_stage: The deployment stage of the REST API.
        :param account_id: The ID of the owning AWS account.
        :param lambda_client: The Boto3 AWS Lambda client object.
        :param lambda_function_arn: The Amazon Resource Name (ARN) of the AWS Lambda
                                    function that is called by Amazon API Gateway to
                                    handle REST requests.
        :return: The ID of the REST API. This ID is required by most Amazon API Gateway
                methods.
        """
        try:
            response = apigateway_client.create_rest_api(name=api_name
                ,endpointConfiguration={
                        'types': ['REGIONAL']
                    }
            )
            api_id = response['id']
            logger.info("Create REST API %s with ID %s.", api_name, api_id)
        except ClientError:
            logger.exception("Couldn't create REST API %s.", api_name)
            raise

        try:
            response = apigateway_client.get_resources(restApiId=api_id)
            root_id = next(item['id'] for item in response['items'] if item['path'] == '/')
            logger.info("Found root resource of the REST API with ID %s.", root_id)
        except ClientError:
            logger.exception("Couldn't get the ID of the root resource of the REST API.")
            raise

        try:
            response = apigateway_client.create_resource(
                restApiId=api_id, parentId=root_id, pathPart=api_base_path)
            base_id = response['id']
            logger.info("Created base path %s with ID %s.", api_base_path, base_id)
        except ClientError:
            logger.exception("Couldn't create a base path for %s.", api_base_path)
            raise

        try:
            apigateway_client.put_method(
                restApiId=api_id, resourceId=base_id, httpMethod='ANY',
                authorizationType='NONE')
            logger.info("Created a method that accepts all HTTP verbs for the base "
                        "resource.")
        except ClientError:
            logger.exception("Couldn't create a method for the base resource.")
            raise

        lambda_uri = \
            f'arn:aws:apigateway:{apigateway_client.meta.region_name}:' \
            f'lambda:path/2015-03-31/functions/{lambda_function_arn}/invocations'
        try:
            # NOTE: You must specify 'POST' for integrationHttpMethod or this will not work.
            apigateway_client.put_integration(
                restApiId=api_id, resourceId=base_id, httpMethod='ANY', type='AWS_PROXY',
                integrationHttpMethod='POST', uri=lambda_uri)
            logger.info(
                "Set function %s as integration destination for the base resource.",
                lambda_function_arn)
        except ClientError:
            logger.exception(
                "Couldn't set function %s as integration destination.", lambda_function_arn)
            raise

        try:
            apigateway_client.create_deployment(restApiId=api_id, stageName=api_stage)
            logger.info("Deployed REST API %s.", api_id)
        except ClientError:
            logger.exception("Couldn't deploy REST API %s.", api_id)
            raise

        source_arn = \
            f'arn:aws:execute-api:{apigateway_client.meta.region_name}:' \
            f'{account_id}:{api_id}/*/*/{api_base_path}'
        try:
            
            lambda_client.add_permission(
                FunctionName=lambda_function_arn
                , StatementId=f'{self.api_name}-rest-invoke',
                Action='lambda:InvokeFunction', Principal='apigateway.amazonaws.com',
                SourceArn=source_arn)
            logger.info("Granted permission to let Amazon API Gateway invoke function %s "
                        "from %s.", lambda_function_arn, source_arn)
        except ClientError:
            logger.exception("Couldn't add permission to let Amazon API Gateway invoke %s.",
                            lambda_function_arn)
            raise

        return api_id



    def create_api_rest(self,api_name):
            """
            Creates a websocket API. The newly created API has no routes.

            :param route_selection: Used to determine route selection. For example,
                                    specifying 'request.body.action' looks for an 'action'
                                    field in the request body and uses the value of that
                                    field to route requests.
            :return: The ID of the newly created API.
            """

            try:
                result = self.apig_v1_client.create_rest_api(name=api_name
                ,endpointConfiguration={
                    'types': ['REGIONAL']
                }
                )
                self.api_id = result['id']
                logger.info("Created REST API %s with ID %s.", api_name, self.api_id)
            except ClientError:
                logger.exception("Couldn't create REST API %s.", api_name)
                raise

            try:
                result = self.apig_v1_client.get_resources(restApiId=self.api_id)
                self.root_id = next(
                    item for item in result['items'] if item['path'] == '/')['id']
            except ClientError:
                logger.exception("Couldn't get resources for API %s.", self.api_id)
                raise
            except StopIteration as err:
                logger.exception("No root resource found in API %s.", self.api_id)
                raise ValueError from err

            return self.api_id



    def add_connection_permissions(self, account, lambda_role_name, iam_resource):
            """
            Adds permission to let the AWS Lambda handler access connections through the
            API Gateway Management API. This is required so the Lambda handler can
            post messages to other chat participants.

            :param account: The AWS account number of the account that owns the
                            websocket API.
            :param lambda_role_name: The name of the role used by the AWS Lambda function.
                                    The connection permission policy is attached to this
                                    role.
            :param iam_resource: A Boto3 AWS Identity and Access Management (IAM) resource.
            """
            self.api_arn = (f'arn:aws:execute-api:{self.apig2_client.meta.region_name}:'
                            f'{account}:{self.api_id}/*')
            policy = None
            try:
                policy = iam_resource.create_policy(
                    PolicyName=f'{lambda_role_name}-{self.permission_policy_suffix}',
                    PolicyDocument=json.dumps({
                        'Version': '2012-10-17',
                        'Statement': [{
                            'Effect': 'Allow',
                            'Action': ['execute-api:ManageConnections'],
                            'Resource': self.api_arn}]}))
                policy.attach_role(RoleName=lambda_role_name)
                logger.info(
                    "Created and attached policy %s to Lambda role.", policy.policy_name)
            except ClientError:
                if policy is not None:
                    policy.delete()
                logger.exception(
                    "Couldn't create or attach policy to Lambda role %s.", lambda_role_name)
                raise

    def remove_connection_permissions(self, lambda_role):
            """
            Removes the connection permission policy from the AWS Lambda function's role
            and deletes the policy.

            :param lambda_role: The role that is attached to the connection permission
                                policy.
            """
            policy_name = f'{lambda_role.name}-{self.permission_policy_suffix}'
            try:
                for policy in lambda_role.attached_policies.all():
                    if policy.policy_name == policy_name:
                        lambda_role.detach_policy(PolicyArn=policy.arn)
                        policy.delete()
                        break
                logger.info("Detached and deleted connection policy %s.", policy_name)
            except ClientError:
                logger.exception(
                    "Couldn't detach or delete connection policy %s.", policy_name)
                raise

    def add_route_and_integration(self, route_name, lambda_func, lambda_client):
            """
            Adds a route to the websocket API and an integration to a Lambda
            function that is used to handle the request.

            Also adds permission to let API Gateway invoke the Lambda function from
            the specified route.

            :param route_name: The name of the new route. This is used as the last part
                            of the route URI. The special routes $connect, $disconnect,
                            and $default can be specified as well as custom routes.
            :param lambda_func: The Lambda function that handles a request to the route.
            :param lambda_client: A Boto3 Lambda client.
            :return: The ID of the newly added route.
            """
            integration_uri = (
                f'arn:aws:apigateway:{self.apig2_client.meta.region_name}:lambda:'
                f'path/2015-03-31/functions/{lambda_func["FunctionArn"]}/invocations')
            try:
                response = self.apig2_client.create_integration(
                    ApiId=self.api_id,
                    IntegrationType='AWS_PROXY',
                    IntegrationMethod='POST',
                    IntegrationUri=integration_uri)
                logging.info("Created integration to %s.", integration_uri)
            except ClientError:
                logging.exception("Couldn't create integration to %s.", integration_uri)
                raise
            else:
                integration_id = response['IntegrationId']

            target = f'integrations/{integration_id}'
            try:
                response = self.apig2_client.create_route(
                    ApiId=self.api_id, RouteKey=route_name, Target=target)
                logger.info("Created route %s to %s.", route_name, target)
            except ClientError:
                logger.exception("Couldn't create route %s to %s.", route_name, target)
                raise
            else:
                route_id = response['RouteId']

            source_arn = f'{self.api_arn}/{route_name}'
            try:
                alpha_route = route_name[1:] if route_name[0] == '$' else route_name
                lambda_client.add_permission(
                    FunctionName=lambda_func['FunctionName'],
                    StatementId=f'{self.api_name}-{alpha_route}-invoke',
                    Action='lambda:InvokeFunction',
                    Principal='apigateway.amazonaws.com',
                    SourceArn=source_arn)
                logger.info(
                    "Added permission to let API Gateway invoke Lambda function %s "
                    "from the new route.", lambda_func['FunctionName'])
            except ClientError:
                logger.exception(
                    "Couldn't add permission to AWS Lambda function %s.",
                    lambda_func['FunctionName'])
                raise

            return route_id

    def add_integration_method(
                self, resource_id, rest_method, lambda_func, service_endpoint_prefix, service_action,
                service_method, role_arn, mapping_template):
            """
            Adds an integration method to a REST API. An integration method is a REST
            resource, such as '/users', and an HTTP verb, such as GET. The integration
            method is backed by an AWS service, such as Amazon DynamoDB.

            :param resource_id: The ID of the REST resource.
            :param rest_method: The HTTP verb used with the REST resource.
            :param service_endpoint_prefix: The service endpoint that is integrated with
                                            this method, such as 'dynamodb'.
            :param service_action: The action that is called on the service, such as
                                'GetItem'.
            :param service_method: The HTTP method of the service request, such as POST.
            :param role_arn: The Amazon Resource Name (ARN) of a role that grants API
                            Gateway permission to use the specified action with the
                            service.
            :param mapping_template: A mapping template that is used to translate REST
                                    elements, such as query parameters, to the request
                                    body format required by the service.
            """
            service_uri = (f'arn:aws:apigateway:{self.apig_client.meta.region_name}'
                        f':{service_endpoint_prefix}:action/{service_action}')
            integration_uri = (
                f'arn:aws:apigateway:{self.apig2_client.meta.region_name}:lambda:'
                f'path/2015-03-31/functions/{lambda_func["FunctionArn"]}/invocations')
            try:
                self.apig_client.put_method(
                    restApiId=self.api_id,
                    resourceId=resource_id,
                    httpMethod=rest_method,
                    authorizationType='NONE')
                self.apig_client.put_method_response(
                    restApiId=self.api_id,
                    resourceId=resource_id,
                    httpMethod=rest_method,
                    statusCode='200',
                    responseModels={'application/json': 'Empty'})
                logger.info("Created %s method for resource %s.", rest_method, resource_id)
            except ClientError:
                logger.exception(
                    "Couldn't create %s method for resource %s.", rest_method, resource_id)
                raise

            try:
                self.apig_client.put_integration(
                    restApiId=self.api_id,
                    resourceId=resource_id,
                    httpMethod=rest_method,
                    type='AWS',
                    integrationHttpMethod=service_method,
                    credentials=role_arn,
                    requestTemplates={'application/json': json.dumps(mapping_template)},
                    uri=service_uri,
                    passthroughBehavior='WHEN_NO_TEMPLATES')
                self.apig_client.put_integration_response(
                    restApiId=self.api_id,
                    resourceId=resource_id,
                    httpMethod=rest_method,
                    statusCode='200',
                    responseTemplates={'application/json': ''})
                logger.info(
                    "Created integration for resource %s to service URI %s.", resource_id,
                    service_uri)
            except ClientError:
                logger.exception(
                    "Couldn't create integration for resource %s to service URI %s.",
                    resource_id, service_uri)
                raise

    def deploy_api(self, stage):
            """
            Deploys an API stage, which lets clients send requests to it.
            The stage must be appended to the endpoint URI when sending requests to
            the API.

            :param stage: The name of the stage.
            :return: The endpoint URI for the deployed stage.
            """
            try:
                self.apig2_client.create_stage(
                    ApiId=self.api_id, AutoDeploy=True, StageName=stage)
                self.stage = stage
                logger.info("Created and deployed stage %s.", stage)
            except ClientError:
                logger.exception("Couldn't create deployment stage %s.", stage)
                raise

            return f'{self.api_endpoint}/{self.stage}'

    def deploy_api_rest(self, stage):
            """
            Deploys a REST API. After a REST API is deployed, it can be called from any
            REST client, such as the Python Requests package or Postman.

            :param stage_name: The stage of the API to deploy, such as 'test'.
            :return: The base URL of the deployed REST API.
            """
            try:
                self.apig_v1_client.create_deployment(
                    restApiId=self.api_id, stageName=stage)
                self.stage = stage
                logger.info("Deployed stage %s.", stage)
            except ClientError:
                logger.exception("Couldn't deploy stage %s.", stage)
                raise
            else:
                return self.api_url()


    def get_websocket_api_info(self):
            """
            Gets data about a websocket API by name. This function scans API Gateway
            APIs in the current account and selects the first one that matches the
            API name.
            :return: The ID and endpoint URI of the named API.
            """
            self.api_id = None
            paginator = self.apig2_client.get_paginator('get_apis')
            for page in paginator.paginate():
                for item in page['Items']:
                    if item['Name'] == self.api_name:
                        self.api_id = item['ApiId']
                        self.api_endpoint = item['ApiEndpoint']
                        return self.api_id, self.api_endpoint
            raise ValueError

    def delete_websocket_api(self):
            """
            Deletes an API Gateway API, including all of its routes and integrations.
            """
            try:
                api_id, _ = self.get_websocket_api_info()
                self.apig2_client.delete_api(ApiId=api_id)
                logger.info("Deleted API %s.", api_id)
            except ClientError:
                logger.exception("Couldn't delete websocket API.")
                raise
    
    def delete_rest_api(self,api_name):
        """
        Deletes a REST API, including all of its resources and configuration.
        """
        try:
            api_id=self.get_rest_api_id(api_name)
            self.apig_v1_client.delete_rest_api(restApiId=api_id)
            logger.info("Deleted REST API %s.", api_id)
            self.api_id = None
        except ClientError:
            logger.exception("Couldn't delete REST API %s.", self.api_id)
            raise

    def get_rest_api_id(self, api_name):
        """
        Gets the ID of a REST API from its name by searching the list of REST APIs
        for the current account. Because names need not be unique, this returns only
        the first API with the specified name.

        :param api_name: The name of the API to look up.
        :return: The ID of the specified API.
        """
        try:
            rest_api = None
            paginator = self.apig_client.get_paginator('get_rest_apis')
            for page in paginator.paginate():
                rest_api = next(
                    (item for item in page['items'] if item['name'] == api_name), None)
                if rest_api is not None:
                    break
            self.api_id = rest_api['id']
            logger.info("Found ID %s for API %s.", rest_api['id'], api_name)
        except ClientError:
            logger.exception("Couldn't find ID for API %s.", api_name)
            raise
        else:
            return rest_api['id']
