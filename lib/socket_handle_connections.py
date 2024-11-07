"""
@author: Francisco R. Moreno Santana franrms@gmail.com
@copyright: (c) 2022 Francisco R. Moreno Santana franrms@gmail.com
@contact: franrms@gmail.com
@summary:   AWS Lambda function as part of a websocket application.
            The function handles messages from an Amazon API Gateway websocket API and uses an
            Amazon DynamoDB OR POSTGRES table to track active connections. When a message is sent by any
            participant or the , it is posted to all other active connections by using the Amazon
            API Gateway Management API.
@todo: 
@note: Logs written by this handler can be found in Amazon CloudWatch.
"""


import json
import logging
import os
import boto3
from botocore.exceptions import ClientError
import jwt
import datetime as dt
from lib import DBHelper
from lib.di_db_helper import DIDBHelper


logger = logging.getLogger()
logger.setLevel(logging.INFO)
debug_mode=False


class SocketHandleConnections:
    
    def __init__(self):
        """
        Initializes a new instance of HandleConnections with default values.

        Attributes:
            
            log (logger): Logger
            event (dict or None): Initializes to None, set to the event passed by lambda later later.
            event (str): Initializes to "PUBLIC". Public is the default space.
        """     
        self.log = logging.getLogger(__name__)          
        self.event=None # event dict
        self.space="PUBLIC"
        
        
    def get_db_handler(self):
        return DIDBHelper.get_instance().resolve()
        

    def handle_connect_by_token(self,token,socket_id, space=None):
        """Handles new connections validating token by adding the connection ID and participant_id to the  store table.

        Args:
            token (str): token fo the user. Must include id_user and expiry date
            socket_id (any): The websocket connection ID of the new connection.
            space (str, optional): space. Defaults to None.

        Returns:
            int: An HTTP status code that indicates the result of adding the connection
                to the DynamoDB table.
        """        
        try:
            if space is None:
                space=self.space
            payload=self.decode_jwt_token(token)
            participant_id=payload['id_user']
            if (participant_id is None):
                return 401
            exp_date=payload['exp']
            now=dt.datetime.now(dt.timezone.utc)         
            token_expiration_date =dt.datetime.fromtimestamp(exp_date)
            
            if token_expiration_date<now:
                logger.exception("Couldn't add connection date expired for token %s %s %s", token ,token_expiration_date,now)
                return 401        
        except Exception:
            logger.exception(
                "Couldn't add connection  for token %s", token)
            return 401

        return self.handle_connect(participant_id=participant_id,socket_id=socket_id,space=space)


    def handle_connect(self,participant_id,socket_id,space="PUBLIC"):
        """Handles new connections adding the connection ID and participant_id to the  store table.

        Args:
            participant_id (str): id_user used 
            socket_id (any): The websocket connection ID of the new connection.
            space (str, optional): space. Defaults to None.

        Returns:
            int: An HTTP status code that indicates the result of adding the connection
                to the DynamoDB table.
        """ 
        status_code = 200
        try:   
            db=self.get_db_handler()
            db.insert_connection(participant_id=str(participant_id),socket_id=socket_id,space=space)
            logger.debug(
                "Added connection %s for %s. ", socket_id, participant_id)
        except ClientError:
            logger.exception(
                "Couldn't add connection %s for %s.", socket_id, participant_id)
            status_code = 503
        return status_code


    def handle_disconnect(self,socket_id):
        """
        Handles disconnections by removing the connection record from the table.
        :param socket_id: The websocket connection ID of the connection to remove.
        :return: An HTTP status code that indicates the result of removing the connection
                from the DynamoDB table.
        """
        status_code = 200
        logger.debug("Trying to disconnect %s.", socket_id)
        try:
            db=self.get_db_handler()
            db.delete_connection_by_socket(socket_id=socket_id)
            logger.debug("Disconnected connection %s.", socket_id)
        except ClientError:
            logger.exception("Couldn't disconnect connection %s.", socket_id)
            status_code = 503
        return status_code

    def get_connections_by_participant(self,participant_id,space="PUBLIC"):
        db=self.get_db_handler()
        connections=db.select_connections_by_participant(participant_id=str(participant_id),space=space)
        return connections


    def handle_message(self,event_body, apig_management_client):
        """
        Handles messages sent by a participant. Looks up all connections
        currently tracked in the DynamoDB table, and uses the API Gateway Management API
        to post the message to each other connection.

        When posting to a connection results in a GoneException, the connection is
        considered disconnected and is removed from the table. This is necessary
        because disconnect messages are not always sent when a client disconnects.

        :param event_body: The body of the message sent from API Gateway. This is a
                        dict with a `msg` field that contains the message to send.
        :param apig_management_client: A Boto3 API Gateway Management API client.
        :return: An HTTP status code that indicates the result of posting the message
                to all active connections.
        """
        status_code = 200
        participant_id = event_body['participant_id']
        space = event_body['space']

        logger.debug("search for participant %s.", participant_id)
        sockets=[]
        try:
            connections = self.get_connections_by_participant(participant_id= str(participant_id),space=space)
            for conn in connections:
                socket_id=conn.get("socket_id")
                if socket_id:                
                    sockets.append(socket_id) 
        except Exception as ex:
            logger.exception("handle_message() Couldn't find participant using %s %s", participant_id , str(ex))
            return 404

        if len(sockets)==0:
            logger.exception("There are no sockets available.")
            return 404

        message = {"participant_id": participant_id, "message": event_body['msg'] }
        message = json.dumps(message)
        logger.debug("Message: %s", str(message))
        # for each socket send a message
        for participant_socket in sockets:
            try:        
                send_response = apig_management_client.post_to_connection(
                    Data=message, ConnectionId=participant_socket)
                logger.debug(
                    "Posted message to connection %s, got response %s.", participant_id, send_response)
            except ClientError as ex:
                logger.exception("Couldn't post to connection %s. Error: %s", participant_socket,str(ex))
            except apig_management_client.exceptions.GoneException:
                logger.info("Connection %s is gone, removing.", participant_socket)
                try:
                    db=self.get_db_handler()
                    db.delete_connection_by_socket(socket_id=participant_socket)
                except ClientError:
                    logger.exception("Couldn't remove connection %s.", participant_socket)

        return status_code

    def broadcast(self,table,space,event_body,apig_management_client,broadcastby="ADMIN"):
        socket_ids = []
        try:
            scan_response = table.scan(ProjectionExpression='socket_id')
            socket_ids = [item['socket_id'] for item in scan_response['Items']]
            logger.info("Found %s active connections.", len(socket_ids))
        except ClientError:
            logger.exception("Couldn't get connections.")
            status_code = 404

        message = f"{broadcastby}: {event_body['msg']}".encode('utf-8')
        logger.info("Message: %s", message)

        for other_conn_id in socket_ids:
            try:
                send_response = apig_management_client.post_to_connection(
                    Data=message, ConnectionId=other_conn_id)
                logger.info(
                    "Posted message to connection %s, got response %s.",
                    other_conn_id, send_response)
            except ClientError:
                logger.exception("Couldn't post to connection %s.", other_conn_id)
            except apig_management_client.exceptions.GoneException:
                logger.info("Connection %s is gone, removing.", other_conn_id)
                try:
                    table.delete_item(Key={'socket_id': other_conn_id})
                except ClientError:
                    logger.exception("Couldn't remove connection %s.", other_conn_id)

    def decode_jwt_token(self,token,secret_key=None,algorithm=None):
        """decodes the token passed

        Args:
            token (jwt): token

        Returns:
            dict: payload
        """        
        # Decodes the jwt token into a payload
        if secret_key is None:
            secret_key=os.environ.get("secret_key")
        if secret_key is None:
            raise Exception("secrect_key was not provided in environment")
        algorithm=os.environ.get("algorithm","HS256")

        payload=None
        try:
            payload = jwt.decode(jwt=token, 
                                key=secret_key,
                                algorithms=[algorithm]
                                )
        except Exception:
            logger.exception("Couldn't read  token %s ", token)

        return payload

    def filter_route_key(self,event):
        """filter by route key. There are some origins, HTTP,Socket and SQS

        Args:
            event (dict): A dict that contains request data, query string parameters

        Returns:
            _type_: _description_
        """        
        socket_id=None
        route_key = event.get('requestContext',{}).get('routeKey')
        body=None
        caller_type=None

        if route_key is not None:
            #WEBSOCKET URI
            socket_id = event.get('requestContext', {}).get('connectionId')
            body=event.get('body')
            body = json.loads(body if body is not None else '{"msg": ""}')
            caller_type="WEBSOCKET"
            return "OK",route_key,socket_id,body,caller_type

        elif route_key is None:
            #check POST in this case we check resourcePath and validate 
            route_key = event.get('requestContext', {}).get('resourcePath')
            if route_key=='/{participant_id+}':
                route_key='sendmessage'
                socket_id="00000"
                body=event.get('body')
                body = json.loads(body if body is not None else '{"msg": ""}')
                caller_type="REST"
                return "OK",route_key,socket_id,body,caller_type

            else:
                #TRY SQS URI
                records = event.get('Records')
                if records is not None and len(records)>0:
                    #we configured SQS to send only one message
                    message=records[0]
                    eventSource = message.get('eventSource')
                    if eventSource=="aws:sqs":
                        body=message.get('body') #BODY FOR EACH MESSAGE
                        body = json.loads(body if body is not None else '{"msg": ""}')
                        route_key=body["action"]
                        socket_id="00000"
                        caller_type="SQS"
                        return "OK",route_key,socket_id,body,caller_type
                    
        # if we can handle the request
        return "ERROR",route_key,socket_id,body,caller_type




    def lambda_handler(self,event, context):
        """
        This function handles three routes: $connect, $disconnect, and sendmessage. Any
        other route results in a 404 status code.

        The $connect route accepts a query string `participant_id` parameter that is the id of
        the participant that originated the connection and space

        :param event: A dict that contains request data, query string parameters, and
                    other data sent by API Gateway.
        :param context: Context around the request.
        :return: A response dict that contains an HTTP status code that indicates the
                result of handling the event.
        """

        
        self.event=event    
        logger.info('Event: %s', event)
        if not debug_mode:
            logger.info('context.invoked_function_arn: %s context.aws_request_id: %s', context.invoked_function_arn, context.aws_request_id)

        route_key = event.get('requestContext', {}).get('routeKey')
        socket_id = event.get('requestContext', {}).get('connectionId')

        result,route_key,socket_id,body,caller_type=self.filter_route_key(event)
        logger.info('route_key: %s', route_key)
        
        if result!="OK":
            return {'statusCode': 400}

        if route_key is None or socket_id is None:
            return {'statusCode': 400}
        
        response = {'statusCode': 200}

        if route_key == '$connect':
            participant_token = event.get('queryStringParameters', {'participant_id': 'guest'}).get('participant_id')
            space = event.get('queryStringParameters', {'space': 'public'}).get('space')
            response['statusCode'] = self.handle_connect_by_token(token= participant_token, socket_id=socket_id,space=space)

        elif route_key == '$disconnect':
            participant_token = event.get('queryStringParameters', {'participant_id': 'guest'}).get('participant_id')
            response['statusCode'] = self.handle_disconnect(socket_id)

        elif route_key == 'sendmessage':      
            response['statusCode'] = self.handle_send_message(event=event,caller_type=caller_type,body=body)      
        else:
            response['statusCode'] = 404

        return response
    
    def handle_send_message(self,event,caller_type,body):
        response = {'statusCode': 200}
        socket_domain=None
        socket_domain=os.environ.get('socket_domain')
        if socket_domain is None:
            logger.exception("Socket domain must be set in environment") 
            response['statusCode'] = 500
            response['body'] = "Socket domain must be set in environment"
            return response
        
        stage=os.environ.get('stage',"latest")
        
        mydomain=socket_domain
        
        if caller_type=='WEBSOCKET':
            domain = event.get('requestContext', {}).get('domainName')
            stage = event.get('requestContext', {}).get('stage')
            if domain is None or stage is None:
                logger.warning(
                    "Couldn't send message. Bad endpoint in request: domain '%s', "
                    "stage '%s'", domain, stage)
                response['statusCode'] = 400
            else:
                #by sqs or similar
                logger.debug("endpoint_url %s.", f'https://{domain}/{stage}')
                mydomain=f'https://{domain}/{stage}'                
            
        apig_management_client = boto3.client(
                    'apigatewaymanagementapi', endpoint_url=mydomain)
        response['statusCode'] = self.handle_message(body, apig_management_client)
        logger.debug('lambda_handler sent body: %s', body)   
        return response
