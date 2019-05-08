from classes.config import Config
from .aws_profile import AWSProfile
from .notification import Notification
import logging
import socket
import pprint
pp = pprint.PrettyPrinter(indent=4)


class AWSProfiles(object):

    def __init__(self, **kwargs):
        self._config = Config().get_config()
        self._profile_defs = kwargs['profiles_defs']
        self._profiles = []
        self.generate_profiles()
        self._snippets = []
        logging.info('AWSProfiles: ' + str(self._profiles))

    def generate_profiles(self):
        for profile_def in self._profile_defs:
            self._profiles.append( AWSProfile( profile_def['profile_name'], profile_def['profile_region'], ) )
            pp.pprint(p_profile_def)

    def send_notifications_for_new_events(self):
        for profile in self._profiles:
            profile.send_notifications_for_new_events()
        logging.info('AWSProfiles: sent notifications for new events')

    def send_sa_report(self):
        logging.info('AWSProfiles: ' + str(self._snippets))
        subject='Instance Status Event Report'
        email_attrs = {
            'email_type': self._config['general']['email_type'],
            'email_to': self._config['general']['sa_recipients'],
            'email_from': self._config['general']['email_from'],
            'subject': subject,
            'html': self.get_html_report(),
            'text': self.get_text_report()
        }
        Notification('email', email_attrs)
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
            digests = profile.get_current_run_digests()
            if digests:
                current_digests.extend(p_digests)
        return current_digests

# END
