from classes.config import Config
from .aws_instance_status_event import AWSInstanceStatusEvent
import logging
import boto3
import pprint
pp = pprint.PrettyPrinter(indent=4)
from lib import HTML

class AWSProfile(object):

    def __init__(self, profile_name, profile_region='us-west-1'):
        self._config = Config().get_config()
        self._profile_name = profile_name
        self._profile_region = profile_region
        self.set_profile_aws_session()
        self.set_profile_aws_ec2_client()
        self.set_instance_statuses()
        self.set_events()
        logging.info('AWSProfile init: ' + str(self._instance_statuses))

    def set_profile_aws_session(self):
        self._aws_session = boto3.Session(profile_name = self._profile_name, region_name = self._profile_region)

    def set_profile_aws_ec2_client(self):
        self._aws_client = self._aws_session.client('ec2')

    def set_instance_statuses(self):
        if self._config['general']['use_test_data']:
            import datetime
            import pytz
            self._instance_statuses = [
                { 'Events':
                    [ { 'Code': 'system-maintenance', 'Description': 'desc abcdefg', 'NotAfter': pytz.utc.localize(datetime.datetime.utcnow()), 'NotBefore': pytz.utc.localize(datetime.datetime.utcnow()) }, ], 'InstanceId': 'i-abcdefg', },
                { 'Events':
                    [ { 'Code': 'system-maintenance', 'Description': 'desc xxxxxxxx', 'NotAfter': pytz.utc.localize(datetime.datetime.utcnow()), 'NotBefore': pytz.utc.localize(datetime.datetime.utcnow()) }, ], 'InstanceId': 'i-xxxxxxxx', },
            ]
        else:
            self._instance_statuses = self._aws_client.describe_instance_status( Filters=[ { 'Name': 'event.code', 'Values': [ 'instance-reboot', 'system-reboot', 'system-maintenance', 'instance-retirement', 'instance-stop' ] }, ], )['InstanceStatuses']

    def get_instance_name_tag(self, instance_id):
        response = self._aws_client.describe_tags( Filters=[ { 'Name': 'resource-id', 'Values': [ instance_id, ], }, ], )
        for tags in response['Tags']:
            if tags['Key'] == 'Name':
                return tags['Value']
        return 'Unavailable'

    def set_events(self):
        events = []
        for instance_status in self._instance_statuses:
            for event in instance_status['Events']:
                instance_id = instance_status['InstanceId']
                event_instance = AWSInstanceStatusEvent(instance_id, event)
                event_instance.set_name(self.get_instance_name_tag(instance_id))
                if ( not event_instance.is_complete() ):
                    events.append(event_instance)
        self._events = events

    def set_events_saserver_details(self, servers):
        for event in self._events:
            event.set_event_saserver_details(servers)

    def set_if_events_new(self, digests):
        for event in self._events:
            event.set_is_new(digests)

    def get_current_run_digests(self):
        current_digests = []
        for event in self._events:
            p_digest = event.get_digest()
            if p_digest:
                current_digests.append(p_digest)
        return current_digests

    def send_notifications_for_new_events(self):
        for event in self._events:
            if ( event.is_new() ):
                event.send_notification_to_owners()
        logging.info('AWSProfile: sent notifications for new events')

    def get_sa_report_snippet(self):
        event_sa_report_snippets = []
        for event in self._events:
            event_sa_report_snippets.append(event.get_sa_report_row())
        logging.info('AWSProfile get_sa_report_snippet: ' +  str(event_sa_report_snippets))
        if ( event_sa_report_snippets ):
            table = HTML.table(event_sa_report_snippets, header_row=['VM', 'CA', 'Instance', 'Description', 'Not Before', 'Not After', 'Owners'])
            return '<h3>' + self._profile_name + ': ' + self._profile_region + '</h3>' + str(table)
        else:
            return '<h3>' + self._profile_name + ': ' + self._profile_region + '</h3>' + '<p>' + 'No instance status events.'










# END
