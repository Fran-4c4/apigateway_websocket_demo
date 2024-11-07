# Amazon API Gateway websocket Demo

## Purpose

Shows how to use the AWS SDK for Python (Boto3) with Amazon API Gateway V2 to
create a websocket API that integrates with AWS Lambda and Postgres.

* Create a websocket API served by API Gateway.
* Define a Lambda handler that stores connections in DB and posts messages to
other  participants.
* Connect to the websocket application and send messages with the Websockets
package.
* This app check AWS SQS too

In the image below you can see an example, this example is using a DynamoDB DDBB but you can use whatever.
![Caht sample](docs/ws-chat-app.png)

 You can follow this tutorial too as a good example:
[Tutorial: Create a WebSocket chat app with a WebSocket API, Lambda and DynamoDB](https://docs.aws.amazon.com/apigateway/latest/developerguide/websocket-api-chat-app.html)



## Prerequisites

- You must have an AWS account, and have your default credentials and AWS Region
  configured as described in the [AWS Tools and SDKs Shared Configuration and
  Credentials Reference Guide](https://docs.aws.amazon.com/credref/latest/refdocs/creds-config-files.html).
- Python 3.7 or later
- Boto3 1.26.102 or later
- Websockets 8.1 or later
- PyTest 6.0.2 or later (to run unit tests)

### Environment
You can use an environment:
`
python -m venv .venv 
`
.venv is the name where the environment will be installed. You can use whatever. This will use the default python interpreter. To use a diferent one use the full path of the python interpreter.
`
c:\\python38\python.exe -m venv .venv
`

- ACTIVATE ENVIRONMENT BEFORE USE OR INSTALL ANYTHING: You must see (.venv) in the terminal after activate. 
`
(.venv) c:\path\app>
`


## Cautions

- As an AWS best practice, grant this code least privilege, or only the 
  permissions required to perform a task. For more information, see 
  [Grant Least Privilege](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#grant-least-privilege) 
  in the *AWS Identity and Access Management 
  User Guide*.
- This code has not been tested in all AWS Regions. Some AWS services are 
  available only in specific Regions. For more information, see the 
  [AWS Region Table](https://aws.amazon.com/about-aws/global-infrastructure/regional-product-services/)
  on the AWS website.
- Running this code might result in charges to your AWS account.

## Running the code

This requires AWS resources that can be deployed by the 
AWS CloudFormation stack that is defined in the accompanying `setup.yaml` file.
This stack manages the following resources:

* A DynamoDB table with a specific key schema.
* For PostgresDB you need to configure first.
* A Lambda function that handles API Gateway websocket request events. 
* An AWS Identity and Access Management (IAM) role that grants permission to let 
Lambda run the function and perform actions on the table.  

### Deploy resources

Deploy prerequisite resources by running the script with the `deploy` flag at 
a command prompt.

```
python app_cfg.py deploy-stack
```

### Run the usage demonstration

Create and deploy the API Gateway websocket API by running with the `demo` flag at 
a command prompt.

```
python app_cfg.py demo
``` 

### Run the chat demonstration

See an automated demo of how to use the Websockets package to connect and send 
messages to the chat application by running with the `chat` flag at a command prompt.

```
python app_cfg.py chat
``` 

*Note:* The Lambda handler for the chat application writes to an
Amazon CloudWatch log. Checking this log can help you troubleshoot issues and give 
additional insight into the application.

### Destroy resources

Destroy resources by running the script with the `destroy-stack` flag at a command 
prompt.

```
python app_cfg.py destroy-stack
``` 

### structure

The contains the following files.

**lambda_websocket.py**

Shows how to implement an AWS Lambda function as part of a websocket chat application.
The function handles messages from an Amazon API Gateway websocket API and uses an
Amazon DynamoDB table or DDBB to track active connections by taking the following actions. 

* A `$connect` request adds a connection ID and the associated user name to the
DB.
* A `sendmessage` request scans the table for connections and uses the API 
Gateway Management API to post the message to all other connections.
* A `$disconnect` request removes the connection record from the table.

**app_cfg.py**

Shows how to use API Gateway V2 to create a websocket API that is backed by a 
Lambda function. The `usage_demo` and `chat_demo` scripts in this file show how to 
accomplish the following actions.

1. Create a websocket API served by API Gateway.
1. Add resources to the websocket API that represent websocket connections and 
chat messages.
1. Add integration methods so the websocket API uses a Lambda function to handle 
incoming requests. 
1. Use the Websockets package to connect users to the chat application and send 
messages to other chat participants.

**setup.yaml**

Contains a CloudFormation script that is used to create the resources needed. Pass the `deploy` or `destroy-stack` flag to the `app_cfg.py` script to 
create or remove these resources:  

* A DynamoDB table
* A Lambda function 
* An IAM role

The `setup.yaml` file was built from the 
[AWS Cloud Development Kit (AWS CDK)](https://docs.aws.amazon.com/cdk/) 
source script here: 
[/resources/cdk/python_example_code_apigateway_websocket/setup.ts](https://github.com/awsdocs/aws-doc-sdk-examples/blob/master/resources/cdk/python_example_code_apigateway_websocket/setup.ts). 

## Running the tests

The unit tests in this module use the botocore Stubber. The Stubber captures requests 
before they are sent to AWS, and returns a mocked response. To run all of the tests, 
run the following command in your 
[GitHub root]/python/example_code/apigateway/websocket folder.

```    
python -m pytest
```

## Additional information

- [Boto3 Amazon API Gateway V2 service reference](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/apigatewayv2.html)
- [Boto3 Amazon API Gateway Management API service reference](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/apigatewaymanagementapi.html)
- [Amazon API Gateway documentation](https://docs.aws.amazon.com/apigateway/)
- [AWS Lambda documentation](https://docs.aws.amazon.com/lambda/)

"# apigateway_websocket_aws" 
