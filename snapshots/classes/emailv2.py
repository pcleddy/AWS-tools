import boto3
import smtplib
from mailer import Mailer
from mailer import Message

import pprint
pp = pprint.PrettyPrinter(indent=4)

class Emailv2:

    debug = False

    #def __init__(self, ses_profile, subject, html, text, email_from, email_to):
    def __init__(self, email_attrs, email_type = ''):

        #pp.pprint(email_attrs)
        #exit()

        self.email_type = email_type
        self.attrs = email_attrs
        if ( self.email_type is 'ses' ):
            self.send_email_via_ses()
        else:
            self.send_email_via_localhost()

    def send_email_via_ses(self):
        self.body = {}
        if 'html' in self.attrs:
            self.body.update({'Html': { 'Charset': 'UTF-8', 'Data': self.attrs['html'], }})
        if 'text' in self.attrs:
            self.body.update({'Text': { 'Charset': 'UTF-8', 'Data': self.attrs['text'], }})

        session = boto3.Session(profile_name = self.attrs['ses_profile'])
        client = session.client('ses')

        response = client.send_email(
            Source = self.attrs['email_from'],
            Destination = { 'ToAddresses': self.attrs['email_to'] },
            Message = {
                'Subject': { 'Data': self.attrs['subject'], },
                'Body': self.body,
            }
        )

    def send_email_via_localhost(self):
        message = Message(
            From = self.attrs['email_from'],
            To = self.attrs['email_to'],
            charset = "utf-8"
        )
        message.Subject = self.attrs['subject']
        if 'html' in self.attrs:
            message.Html = self.attrs['html']
        if 'text' in self.attrs:
            message.Body = self.attrs['text']

        smtp_server = self.attrs['smtp_server'] if ('smtp_server' in self.attrs) else 'localhost'
        if 'smtp_port' in self.attrs: smtp_server = smtp_server + ':' + self.attrs['smtp_port']

        sender = Mailer(smtp_server)
        try:
            sender.send(message)
        except:
            print('Failed to send email, check smtp server and port')
