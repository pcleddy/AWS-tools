from .notification import Notification
from jinja2 import Template

from pytz import timezone
import socket
import logging
import boto3
import hashlib
import pprint
pp = pprint.PrettyPrinter(indent=4)

class AWSInstanceStatusEvent(object):

    POC_flag = True

    def __init__(self, instance_id, event):
        logging.basicConfig(filename='/var/tmp/aws-tools.log',level=logging.INFO,format='%(asctime)s %(message)s')
        self._instance_id = instance_id
        self._event = event
        self.set_digest()

    def is_complete(self):
        if "Completed" in self._event['Description']: self._completed = True
        else: self._completed = False
        return self._completed

    def set_event_saserver_details(self, servers):
        logging.info('START: set_event_saserver_details')
        p_server_details = servers.get_saserver_details()
        if ( self._instance_id in p_server_details.keys() ):
            self._server = p_server_details[self._instance_id]
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
        p_last_run_digests = digests.get_last_run_digests()
        if ( self._digest in p_last_run_digests ):
            self._new_event = False
        else:
            self._new_event = True
        logging.info('AWSInstanceStatusEvent: Is new: ' + str(self._new_event))

    def is_new(self):
        return self._new_event

    def get_owner(self):
        if ( self._server is None ):
            return 'N/A'
        else:
            return self._server['name'] + '@mydomain'

    def get_owner_email_addr(self):
        if ( self._server is None ):
            return 'paul.leddy@mydomain'
        else:
            return self._server['name'] + '@mydomain'

    def get_cog_admin(self):
        if ( self._server is None ):
            return 'N/A'
        else:
            return self._server['cog_admin']

    def get_html_message_to_owner(self):
        return self.get_html_template()

    def get_text_message_to_owner(self):
        return 'You got mail: ' + self._instance_id + '. STOP.'

    def get_not_before_date_str(self):
        return self._event['NotBefore'].astimezone(timezone('US/Pacific')).strftime("%Y-%m-%d %H:%M %Z") if ( 'NotBefore' in self._event ) else 'N/A'

    def get_not_after_date_str(self):
        return self._event['NotAfter'].astimezone(timezone('US/Pacific')).strftime("%Y-%m-%d %H:%M %Z") if ( 'NotAfter' in self._event ) else 'N/A'

    def set_name(self, name):
        self._name = name

    def get_vm_name(self):
        if ( self._server is None ):
            return self._instance_id
        # VM Maintenance: fqdn.mydomin (if hostname != null and domain != null)
        if ( self._server['hostname'] is not None and self._server['domain'] is not None ):
            return self._server['hostname'] + '.' + self._server['domain']
        # VM Maintenance: device_name (if hostname == null, or domain == null)
        elif ( ( self._server['hostname'] is None or self._server['domain'] is None) and self._server['device_name'] is not None ):
            return self._server['device_name']
        # VM Maintenance: private IP  (if device_name == null, and if govcloud region)
        elif ( self._server['aws_acct_type'] is 'GOV' and self._server['ip_address'] is not None):
             return self._server['ip_address']
        # VM Maintenance: public IP / private IP  (if device_name == null, and if public region)
        elif ( self._server['device_name'] is None and self._server['aws_acct_type'] is 'EC2' and self._server['ip_address'] is not None ):
            return self._server['ip_address']
        elif ( self._name is not None ):
            return self._name
        else:
            return self._instance_id

    def send_notification_to_owner(self):
        if ( not self.on_prod() ):
            p_subject='Instance Status Event Notification: ' + self.get_vm_name()
            p_email_attrs = {
                'email_type': 'ses',
                'email_to': ['paul.leddy@mydomain'],
                'email_from': 'paul.leddy@mydomain',
                'subject': p_subject,
                'html': self.get_html_message_to_owner(),
                'text': self.get_text_message_to_owner()
            }
            Notification( 'email', p_email_attrs)
        else:
            p_subject='Instance Status Event Notification: ' + self.get_vm_name()
            p_email_to = ['paul.leddy@mydomain', 'ryan.frost@mydomain'] if ( AWSInstanceStatusEvent.POC_flag ) else self.get_owner_email_addr()
            p_email_attrs = {
                'email_to': p_email_to,
                'email_from': 'root@mydomain',
                'subject': p_subject,
                'html': self.get_html_message_to_owner(),
                'text': self.get_text_message_to_owner()
            }
            Notification('email', p_email_attrs)

    def get_html_template(self):
        p_template_raw = '''
            <h1>DEV PHASE</h1>
            <p>To: {{ owner_email }}

            <p>Hello,

            <p>Your Amazon VM, {{ vm_name }}, is scheduled for maintenance by Amazon.  An outage will be incurred during the maintenance window below.  Please reply to this email if you would like to resolve the maintenance at a time before the scheduled maintenance window.  Resolving the maintenance requirement ahead of time will involve powering down your VM, and powering it back on.

            <p>Maintenance Details:

            <ul>
                <li>VM: {{ vm_name }}
                <li>Instance: {{ instance_id }}
                <li>Description: {{ maintenance_desc }}
                <li>Maintenance window start time: {{ not_before }}
                <li>Maintenance window end time: {{ not_after }}
                <li>Owner: {{ owner }}
            </ul>

            <p>Thank you,<br />
            Infrastructure Team<br />
            admin@mydomain

            '''

        p_template = Template(p_template_raw)
        p_html = p_template.render(
            owner_email = self.get_owner_email_addr(),
            vm_name = self.get_vm_name(),
            instance_id = self._instance_id,
            not_before = self.get_not_before_date_str(),
            not_after = self.get_not_after_date_str(),
            maintenance_desc = self._event['Description'],
            owner = self.get_owner(),
        )

        return p_html

    def get_sa_report_snippet(self):
        html_snippet = '<td>'
        html_snippet += self._name
        html_snippet += '<td>'
        html_snippet += self.get_cog_admin()
        html_snippet += '<td>'
        html_snippet += self._instance_id
        html_snippet += '<td>'
        html_snippet += self._event['Description']
        #m_html += "Code: " + e['Code'] + "\n"
        html_snippet += '<td>'
        html_snippet += self.get_not_before_date_str()
        html_snippet += '<td>'
        html_snippet += self.get_not_after_date_str()
        html_snippet += '<td>'
        html_snippet += self.get_owner()
        return html_snippet

    def on_prod(self):
        on_prod_flag = 'admin' in socket.gethostname()
        logging.info('AWSInstanceStatusEvent: on_prod: ' + str(on_prod_flag))
        return on_prod_flag

# END
