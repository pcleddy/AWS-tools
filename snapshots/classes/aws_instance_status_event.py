from classes.config import Config
from .notification import Notification
from jinja2 import Template
from pytz import timezone
import socket
import logging
import boto3
import hashlib
from lib import HTML

class AWSInstanceStatusEvent(object):

    def __init__(self, instance_id, event):
        self._config = Config().get_config()
        self._instance_id = instance_id
        self._event = event
        self.set_digest()

    def is_complete(self):
        if "Completed" in self._event['Description']: self._completed = True
        else: self._completed = False
        return self._completed

    def set_event_saserver_details(self, servers):
        logging.info('START: set_event_saserver_details')
        server_details = servers.get_saserver_details()
        if ( self._instance_id in server_details.keys() ):
            self._server = server_details[self._instance_id]
            logging.info('AWSInstanceStatusEvent: set_event_saserver_details: Found server: ' + str(self._server))
        else:
            self._server = None
        logging.info('AWSInstanceStatusEvent: set_event_saserver_details: Has server: ' + str(self.has_server()))

    def has_server(self):
        return True if ( self._server ) else False

    def set_digest(self):
        self._digest = hashlib.sha224(
            self._instance_id.encode('utf-8')
            + self._event['Code'].encode('utf-8')
        ).hexdigest()
        logging.info('AWSInstanceStatusEvent: digest: ' + str(self._digest))

    def get_digest(self):
        return self._digest

    def set_is_new(self, digests):
        last_run_digests = digests.get_last_run_digests()
        if ( self._digest in last_run_digests ):
            self._new_event = False
        else:
            self._new_event = True
        logging.info('AWSInstanceStatusEvent: Is new: ' + str(self._new_event))

    def is_new(self):
        return self._new_event

    def get_owners(self):
        if ( self._server is None ):
            return []
        else:
            return self._server['owners']

    def get_owners_str(self):
        if ( self._server is None ):
            return 'N/A'
        else:
            return ', '.join(self.get_owners())

    def get_owners_email_addrs(self):
        if ( self._server is None ):
            return ['paul.leddy@jpl.nasa.gov']
        else:
            return map(lambda x: x + '@jpl.nasa.gov', self._server['owners'])

    def get_owners_email_addrs_str(self):
        return ', '.join(self.get_owners_email_addrs())

    def get_cog_admin(self):
        if ( self._server is None ):
            return 'N/A'
        else:
            return self._server['cog_admin']

    def get_html_message_to_owners(self):
        return self.get_html_template()

    def get_text_message_to_owners(self):
        return 'You got mail: ' + self._instance_id + '. STOP.'

    def get_not_before_date_str(self):
        return self._event['NotBefore'].astimezone(timezone('US/Pacific')).strftime("%Y-%m-%d %H:%M %Z") if ( 'NotBefore' in self._event ) else 'N/A'

    def get_not_after_date_str(self):
        return self._event['NotAfter'].astimezone(timezone('US/Pacific')).strftime("%Y-%m-%d %H:%M %Z") if ( 'NotAfter' in self._event ) else 'N/A'

    def set_name(self, name):
        self._name = name

    def get_vname(self):
        if ( self._server is None ):
            return self._instance_id
        if ( self._server['hostname'] is not None and self._server['domain'] is not None ):
            return self._server['hostname'] + '.' + self._server['domain']
        elif ( ( self._server['hostname'] is None or self._server['domain'] is None) and self._server['device_name'] is not None ):
            return self._server['device_name']
        elif ( self._server['aws_acct_type'] is 'GOV' and self._server['ip_address'] is not None):
             return self._server['ip_address']
        elif ( self._server['device_name'] is None and self._server['aws_acct_type'] is 'EC2' and self._server['ip_address'] is not None ):
            return self._server['ip_address']
        elif ( self._name is not None ):
            return self._name
        else:
            return self._instance_id

    def send_notification_to_owners(self):
        subject='Instance Status Event Notification: ' + self.get_vname()
        email_to = self._config['general']['sa_recipients'] if ( self._config['general']['POC'] ) else self.get_owners_email_addrs()
        email_attrs = {
            'email_type': self._config['general']['email_type'],
            'email_to': email_to,
            'email_from': self._config['general']['email_from'],
            'subject': subject,
            'html': self.get_html_message_to_owners(),
            'text': self.get_text_message_to_owners()
        }
        Notification('email', email_attrs)

    def get_html_template(self):
        template_raw = '''
            <h1>DEV PHASE</h1>
            <p>To: {{ owners_email_addrs_str }}

            <p>Hello,

            <p>Your Amazon VM, {{ vname }}, is scheduled for maintenance by Amazon.  An outage will be incurred during the maintenance window below.  Please reply to this email if you would like to resolve the maintenance at a time before the scheduled maintenance window.  Resolving the maintenance requirement ahead of time will involve powering down your VM, and powering it back on, or merely a reboot, depending on the maintenance type.

            <p>Maintenance Details:

            <ul>
                <li>VM: {{ vname }}
                <li>Instance: {{ instance_id }}
                <li>Description: {{ maintenance_desc }}
                <li>Maintenance window start time: {{ not_before }}
                <li>Maintenance window end time: {{ not_after }}
                <li>Owners: {{ owners_str }}
            </ul>

            <p>Thank you,<br />
            Infrastructure SA Team<br />
            jplis-sa@jpl.nasa.gov

            '''

        template = Template(p_template_raw)
        html = template.render(
            owners_email_addrs_str = self.get_owners_email_addrs_str(),
            vname = self.get_vname(),
            instance_id = self._instance_id,
            not_before = self.get_not_before_date_str(),
            not_after = self.get_not_after_date_str(),
            maintenance_desc = self._event['Description'],
            owners_str = self.get_owners_str(),
        )

        return html

    def get_sa_report_row(self):
        return [self._name, self.get_cog_admin(), self._instance_id, self._event['Description'], self.get_not_before_date_str(), self.get_not_after_date_str(), self.get_owners_str()]

# END
