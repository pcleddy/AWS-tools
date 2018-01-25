from classes.config import Config
from .email import Email
import logging
import boto3
import hashlib
import pprint
pp = pprint.PrettyPrinter(indent=4)

class Notification(object):

    def __init__(self, notification_type, msg_attrs, **kwargs):
        self._config = Config().get_config()
        self._msg_attr = msg_attrs
        if ( notification_type == 'email' ):
            self.send_email()
        else:
            self.send_no_protocol()

    def send_email(self):
        Email(self._msg_attr)
        logging.info('Notification: sent email.')

    def send_no_protocol(self):
        logging.info('Notification: no protocol given, sent nothing.')
