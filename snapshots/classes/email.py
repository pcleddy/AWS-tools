from classes.config import Config
import boto3
import smtplib
from mailer import Mailer
from mailer import Message
import logging
import pprint
pp = pprint.PrettyPrinter(indent=4)

class Email(object):

    def __init__(self, email_attrs):
        self._config = Config().get_config()
        self._attrs = email_attrs
        if ( ( 'email_type' in self._attrs ) and ( self._attrs['email_type'] == 'ses' ) ):
            self.send_email_via_ses()
        else:
            self.send_email_via_localhost()

    def send_email_via_ses(self):
        self._body = {}
        if not 'ses_profile' in self._attrs:
            self._attrs['ses_profile'] = self._config['general']['ses_profile']
        if 'html' in self._attrs:
            self._body.update({'Html': { 'Charset': 'UTF-8', 'Data': self._attrs['html'], }})
        if 'text' in self._attrs:
            self._body.update({'Text': { 'Charset': 'UTF-8', 'Data': self._attrs['text'], }})

        m_session = boto3.Session(profile_name = self._attrs['ses_profile'])
        m_client = m_session.client('ses')

        logging.info('Email: body: ' + str(self._body))
        m_response = m_client.send_email(
            Source = self._attrs['email_from'],
            Destination = { 'ToAddresses': self._attrs['email_to'] },
            Message = {
                'Subject': { 'Data': self._attrs['subject'], },
                'Body': self._body,
            }
        )

    def send_email_via_localhost(self):
        message = Message(
            From = self._attrs['email_from'],
            To = self._attrs['email_to'],
            charset = "utf-8"
        )
        message.Subject = self._attrs['subject']
        if 'html' in self._attrs:
            message.Html = self._attrs['html']
        if 'text' in self._attrs:
            message.Body = self._attrs['text']

        m_smtp_server = self._attrs['smtp_server'] if ('smtp_server' in self._attrs) else 'localhost'
        if 'smtp_port' in self._attrs: m_smtp_server = m_smtp_server + ':' + self._attrs['smtp_port']

        sender = Mailer(m_smtp_server)
        try:
            sender.send(message)
        except:
            print('Failed to send email, check smtp server and port')
            logging.warning('Failed to send email, check smtp server and port')
