from .aws_profile import AWSProfile
from .notification import Notification

import logging
import socket
import pprint
pp = pprint.PrettyPrinter(indent=4)


class AWSProfiles(object):

    def __init__(self, **kwargs):
        logging.basicConfig(filename='/var/tmp/aws-tools.log',level=logging.INFO,format='%(asctime)s %(message)s')
        self._profile_defs = kwargs['profiles_defs']
        self._profiles = []
        self.generate_profiles()
        self._snippets = []
        logging.info('AWSProfiles: ' + str(self._profiles))

    def generate_profiles(self):
        for p_profile_def in self._profile_defs:
            self._profiles.append( AWSProfile( p_profile_def['profile_name'], p_profile_def['profile_region'], ) )
            pp.pprint(p_profile_def)

    def send_notifications_for_new_events(self):
        for profile in self._profiles:
            profile.send_notifications_for_new_events()
        logging.info('AWSProfiles: sent notifications for new events')

    def send_sa_report(self):
        logging.info('AWSProfiles: ' + str(self._snippets))
        p_subject='Instance Status Event Report'
        if ( not self.on_prod() ):
            p_email_attrs = {
                'email_type': 'ses',
                'email_to': ['paul.leddy@mydomain'],
                'email_from': 'paul.leddy@mydomain',
                'subject': p_subject,
                'html': self.get_html_report(),
                'text': self.get_text_report()
            }
        else:
            p_email_attrs = {
                'email_to': ['paul.leddy@mydomain', 'ryan.frost@mydomain'],
                'email_from': 'root@mydomain',
                'subject': p_subject,
                'html': self.get_html_report(),
                'text': self.get_text_report()
            }
        Notification('email', p_email_attrs)
        logging.info('AWSProfiles: sent report')

    def get_html_report(self):
        report = ''
        for profile in self._profiles:
            report += profile.get_sa_report_snippet()
        return report

    def get_text_report(self):
        return 'N/A'

    def set_events_saserver_details(self, servers):
        for profile in self._profiles:
            profile.set_events_saserver_details(servers)
        logging.info('AWSProfiles: set events SA server details')

    def set_if_events_new(self, digests):
        for profile in self._profiles:
            profile.set_if_events_new(digests)
        logging.info('AWSProfiles: set if events new')

    def get_current_run_digests(self):
        current_digests = []
        for profile in self._profiles:
            p_digests = profile.get_current_run_digests()
            if p_digests:
                current_digests.extend(p_digests)
        return current_digests

    def on_prod(self):
        on_prod_flag = 'admin' in socket.gethostname()
        logging.info('AWSProfiles: on_prod: ' + str(on_prod_flag))
        return on_prod_flag

# END
