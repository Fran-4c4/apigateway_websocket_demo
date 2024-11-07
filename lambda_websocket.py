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
import logging
import os
from lib import SocketHandleConnections


logger = logging.getLogger()
logger.setLevel(logging.INFO)
debug_mode=False

def lambda_handler(event, context):
    """
    handles lambda invocation

    :param event: A dict that contains request data, query string parameters, and
                  other data sent by API Gateway.
    :param context: Context around the request.
    :return: A response dict that contains an HTTP status code that indicates the
             result of handling the event.
    """
    environment = os.environ['environment']
    if environment is not None:
        logger.setLevel(os.environ.get('LOG_LEVEL', logging.INFO))
                        
    logger.debug('Event: %s', event)
    if not debug_mode:
        logger.debug('context.invoked_function_arn: %s context.aws_request_id: %s', context.invoked_function_arn, context.aws_request_id)
    
    bl=SocketHandleConnections()
    ret= bl.lambda_handler(event=event,context=context)
    return ret    

def test_lambda():
    """test lambda. We use an event dict for this.
    """    
    event=""

if __name__ == '__main__':
    for x in range(1):
        test_lambda()