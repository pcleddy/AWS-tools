import boto3
import pprint
import datetime
import pytz
import logging
import time
from lib.json2elk import send_json2elk
import json

logger = logging.getLogger('ec2-snapshots')

pp = pprint.PrettyPrinter(indent=4)

class Volume():

    m_debug = True
    m_make_snapshots = True

    def __init__(self, m_id, m_backup_set, m_client_ec2, m_profile_name):
        self.id = m_id
        self.fresh_tags = False
        self.backup_set = m_backup_set
        self.tags = {}
        self.client_ec2 = m_client_ec2
        self.profile = m_profile_name
        self.snapshots = []

    def get_id(self):
        return self.m_id

    def fetch_tags(self):
        if self.fresh_tags == True: return

        m_response = self.client_ec2.describe_tags( Filters=[ { 'Name': 'resource-id', 'Values': [ self.id, ], }, ], )
        for m_tag in m_response['Tags']:
            self.tags.update({m_tag['Key']: m_tag['Value']})
        self.fresh_tags = True

    def get_tags_array(self):
        m_tags_array = []
        for k,v in self.tags.items():
            m_tags_array.append({ 'Key': k, 'Value': v })
        self.tags_array = m_tags_array
        return m_tags_array

    def needs_snapshot(self):
        if ( not self.is_managed() or self.is_waived() ):
            self.needs_snapshot_flag = False
            return False
        else:
            if not self.has_snapshots():
                self.needs_snapshot_flag = True
                return True
            elif self.is_daily():
                return True
            else:
                m_most_current_snapshot = self.get_most_current_snapshot()
                m_backup_threshold = datetime.datetime.now(tz=pytz.utc) - datetime.timedelta(days=self.get_snapshot_freq_in_days()) + datetime.timedelta(hours=1)
                m_needs_snapshot = ( m_backup_threshold > m_most_current_snapshot.creation_date )
                self.latest_snapshot = m_most_current_snapshot.creation_date.strftime("%Y-%m-%d %H:%M:%S")
                self.needs_snapshot_flag = m_needs_snapshot
                return m_needs_snapshot

    def is_daily(self):
        if self.backup_set['name'].startswith('daily'):
            return True
        else:
            return False

    def is_managed(self):
        if self.backup_set is None:
            self.managed = False
            return False
        else:
            self.managed = True
            return True

    def is_waived(self):
        if not self.is_managed():
            return None
        else:
            if ( self.backup_set['name'] == 'waive' ):
                self.waived = True
                return True
            else:
                self.waived = False
                return False

    def has_snapshots(self):
        if not self.snapshots: return False
        else: return True

    def get_most_current_snapshot(self):
        if not self.snapshots:
            return None
        else:
            m_current = None
            for m_snapshot in self.snapshots:
                if not m_current:
                    m_current = m_snapshot
                    continue
                if ( m_snapshot.creation_date > m_current.creation_date ):
                    m_current = m_snapshot

            self.current = m_current
            return m_current

    def take_snapshot(self, m_dryrun):
        if not Volume.m_make_snapshots:
            logger.info('Snapshots turned off at volume level')
            return
        self.fetch_tags()
        if ( ( 'SnapSchedule' not in self.tags ) or ( self.tags['SnapSchedule'] != self.backup_set['tag'] ) ):
            self.set_tag('SnapSchedule', self.backup_set['tag'])
            if 'SnapSchedule' in self.tags:
                logger.info("SnapSchedule tag changed for {}: {} -> {}".format(self.id, self.tags['SnapSchedule'], self.backup_set['tag']))
            else:
                logger.info("SnapSchedule tag added to {}: new tag {}".format(self.id, self.backup_set['tag']))
        m_tags_array = self.get_tags_array()
        if m_dryrun:
            logger.info('Dry run, not taking snapshot')
            self.new_snapshot_id = 'i-fake123'
        else:
            m_response = self.client_ec2.create_snapshot( VolumeId = self.id )
            time.sleep(.3)    # create snapshot broke once because of rate of calls
            m_snapshot_id = m_response['SnapshotId']
            self.new_snapshot_id = m_snapshot_id

            m_response['StartTime'] = m_response['StartTime'].isoformat()
            m_response.pop('ResponseMetadata', None)
            m_response['AWSAccountName'] = self.profile
            m_response['FrequencyInDays'] = self.get_snapshot_freq_in_days()
            m_result = send_json2elk(json.dumps(m_response), 'snapshots', 'snapshot', str(m_snapshot_id))

            m_response = self.client_ec2.create_tags(
                Resources = [ m_snapshot_id ],
                Tags= m_tags_array
            )

    def is_snapshot_completed(self, m_dryrun):
        if m_dryrun: return True
        m_response = self.client_ec2.describe_snapshots(
            SnapshotIds=[ self.new_snapshot_id ],
            Filters=[
                {
                    'Name': 'status',
                    'Values': [ 'pending', ]
                },
            ],
        )
        time.sleep(.3)
        if m_response['Snapshots']:
            #pp.pprint(m_response)
            self.set_new_snapshot_state(m_response['Snapshots'][0]['State'])
            return False
        else:
            self.fetch_new_snapshot_state()
            return True

    def set_new_snapshot_state(self, m_state):
        self.new_snapshot_state = m_state

    def fetch_new_snapshot_state(self):
        m_response = self.client_ec2.describe_snapshots( SnapshotIds=[ self.new_snapshot_id ], )
        time.sleep(.3)
        self.new_snapshot_state = m_response['Snapshots'][0]['State']
        return self.new_snapshot_state

    def get_new_snapshot_state(self, m_dryrun):
        if m_dryrun:
            self.new_snapshot_state = 'completed'
            return self.new_snapshot_state
        return self.new_snapshot_state

    def get_snapshot_freq_in_days(self):
        if ( not self.is_managed() or self.is_waived() ):
            return None
        return self.backup_set['snapshot frequency in days']

    def add_snapshot(self, m_snapshot):
        m_managed = self.is_managed()
        m_snapshot.set_managed(m_managed)
        if m_managed:
            if not self.is_waived():
                m_snapshot.set_expiration_in_days(self.backup_set['snapshots expire in days'])
            self.snapshots.append(m_snapshot)
            return True
        else:
            return False

    def dump(self):
        pp.pprint(self.__dict__)
        for m_snapshot in self.snapshots:
            pp.pprint(m_snapshot.__dict__)

    def set_tag(self, tag_key, tag_value):
        m_response = self.client_ec2.create_tags( Resources = [ self.id ], Tags= [ {'Key': tag_key, 'Value': tag_value} ] )

    def fetch_instance_id(self):
        m_response = self.client_ec2.describe_volumes( VolumeIds=[ self.id ], )
        time.sleep(.3)
        self.attachments = m_response['Volumes'][0]['Attachments']
        if self.attachments:
            self.instance_id = self.attachments[0]['InstanceId']
        else:
            self.instance_id = 'No associated instance'
        return self.instance_id
