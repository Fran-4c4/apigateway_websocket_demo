

import boto3
from botocore.exceptions import ClientError
import logging
import uuid
import json
import datetime as dt

count=0

class QueueHelper:

    def __init__(self, queueName=None):
        self.log = logging.getLogger(__name__)
        # Get the service resource
        self.sqs = boto3.resource('sqs')
        self.queueName = queueName

    def send_message(self, queueName=None, messageBody=None, messageGroupId=None,messageDeduplicationId=None):

        sqs = self.sqs
        if queueName is None:
            queueName = self.queueName
        if messageDeduplicationId is None:
            messageDeduplicationId=str(uuid.uuid4())
        # Get the queue. This returns an SQS.Queue instance
        queue = sqs.get_queue_by_name(QueueName=queueName)
        # You can now access identifiers and attributes
        print(queue.url)
        print(queue.attributes.get('DelaySeconds'))

        # Create a new message
        response = queue.send_message(MessageBody=messageBody,MessageGroupId=messageGroupId,MessageDeduplicationId=messageDeduplicationId)
        # The response is NOT a resource, but gives you a message ID and MD5
        print(response.get('MessageId'))
        print(response.get('MD5OfMessageBody'))


def test_notification():
    queueName = "TEST-queue.fifo"
    q = QueueHelper(queueName)
    id=uuid.uuid4()
    participant_id="32ab0bd2-4090-11ea-9075-509a4c837ab7"
    space="TEST"
    global count
    count+=1
    date=str(dt.datetime.now())

    msgj={"id": str(id), "type": "NOTIFICATION", "message": "test py" + str(count), "date": str(date)}
    msg = {"participant_id": participant_id
        , "space": space, "action": "sendmessage",
           "msg": msgj
           }
    msg_str= json.dumps(msg)
    messageGroupId='TEST'
    q.send_message(messageBody=msg_str,messageGroupId=messageGroupId,messageDeduplicationId=str(id) )

def test_operation():
    queueName = "TEST-queue.fifo"
    q = QueueHelper(queueName)
    participant_id="32ab0bd2-4090-11ea-9075-509a4c837ab7"
    space="TEST"
    global count
    count+=1
    date=str(dt.datetime.now())
    msg_uniqueid=uuid.uuid4()
    msg_type="OPERATION"
    report_id="4cfd42b8-eb36-11ec-8ea9-02cd0f368927"
    msg_body= {"operation":"REPORT_UPDATED","id":report_id}
    
    sqs_app_msg={"id": str(msg_uniqueid), "type":msg_type ,"date": str(date), "message": msg_body }
    sqs_message = {"participant_id": participant_id
        , "space": space
        , "action": "sendmessage"
        , "msg": sqs_app_msg
           }
    sqs_msg_str= json.dumps(sqs_message)
    messageGroupId='TEST'
    q.send_message(messageBody=sqs_msg_str,messageGroupId=messageGroupId,messageDeduplicationId=str(msg_uniqueid) )

def test_notification():
    queueName = "TEST-queue.fifo"
    q = QueueHelper(queueName)
    participant_id="32ab0bd2-4090-11ea-9075-509a4c837ab7"
    space="TEST"
    #space="TEST"
    global count
    count+=1
    date=str(dt.datetime.now())
    msg_uniqueid=uuid.uuid4()
    msg_type="NOTIFICATION"
    report_id="d577cfc4-e734-11ec-b63a-02cd0f368927"
    msg_body= {"operation":"NOTIFICATION", "type_level":"SUCCESS", "message": "This is a server notification test.", "messageTitle":"Server test", "action":"linktoreport", "closeable":"true" }
    
    sqs_app_msg={"id": str(msg_uniqueid), "type":msg_type ,"date": str(date), "message": msg_body }
    sqs_message = {"participant_id": participant_id
        , "space": space
        , "action": "sendmessage"
        , "msg": sqs_app_msg
           }
    sqs_msg_str= json.dumps(sqs_message)
    messageGroupId='TEST'
    q.send_message(messageBody=sqs_msg_str,messageGroupId=messageGroupId,messageDeduplicationId=str(msg_uniqueid) )
    
if __name__ == '__main__':
    for x in range(1):
        test_notification()    
        #test_operation()