import boto3
import pprint
import datetime
import pytz
import logging
import time
import json

logger = logging.getLogger('ec2-snapshots')

pp = pprint.PrettyPrinter(indent=4)

class Volume():

    debug = True
    make_snapshots = True

    def __init__(self, id, backup_set, client_ec2, profile_name):
        self.id = id
        self.fresh_tags = False
        self.backup_set = backup_set
        self.tags = {}
        self.client_ec2 = client_ec2
        self.profile = profile_name
        self.snapshots = []

    def get_id(self):
        return self.id

    def fetch_tags(self):
        if self.fresh_tags == True: return

        response = self.client_ec2.describe_tags( Filters=[ { 'Name': 'resource-id', 'Values': [ self.id, ], }, ], )
        for tag in response['Tags']:
            self.tags.update({tag['Key']: tag['Value']})
        self.fresh_tags = True

    def get_tags_array(self):
        tags_array = []
        for k,v in self.tags.items():
            tags_array.append({ 'Key': k, 'Value': v })
        self.tags_array = tags_array
        return tags_array

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
                most_current_snapshot = self.get_most_current_snapshot()
                backup_threshold = datetime.datetime.now(tz=pytz.utc) - datetime.timedelta(days=self.get_snapshot_freq_in_days()) + datetime.timedelta(hours=1)
                needs_snapshot = ( backup_threshold > most_current_snapshot.creation_date )
                self.latest_snapshot = most_current_snapshot.creation_date.strftime("%Y-%m-%d %H:%M:%S")
                self.needs_snapshot_flag = needs_snapshot
                return needs_snapshot

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
            current = None
            for snapshot in self.snapshots:
                if not current:
                    current = snapshot
                    continue
                if ( snapshot.creation_date > current.creation_date ):
                    current = snapshot

            self.current = current
            return current

    def take_snapshot(self, dryrun):
        if not Volume.make_snapshots:
            logger.info('Snapshots turned off at volume level')
            return
        self.fetch_tags()
        if ( ( 'SnapSchedule' not in self.tags ) or ( self.tags['SnapSchedule'] != self.backup_set['tag'] ) ):
            self.set_tag('SnapSchedule', self.backup_set['tag'])
            if 'SnapSchedule' in self.tags:
                logger.info("SnapSchedule tag changed for {}: {} -> {}".format(self.id, self.tags['SnapSchedule'], self.backup_set['tag']))
            else:
                logger.info("SnapSchedule tag added to {}: new tag {}".format(self.id, self.backup_set['tag']))
        tags_array = self.get_tags_array()
        if dryrun:
            logger.info('Dry run, not taking snapshot')
            self.new_snapshot_id = 'i-fake123'
        else:
            response = self.client_ec2.create_snapshot( VolumeId = self.id )
            time.sleep(.3)    # create snapshot broke once because of rate of calls
            snapshot_id = response['SnapshotId']
            self.new_snapshot_id = snapshot_id

            response['StartTime'] = response['StartTime'].isoformat()
            response.pop('ResponseMetadata', None)
            response['AWSAccountName'] = self.profile
            response['FrequencyInDays'] = self.get_snapshot_freq_in_days()
            # was sending data to elk stack, but turning off until can send to splunk instead
            #result = send_json2elk(json.dumps(response), 'snapshots', 'snapshot', str(snapshot_id))

            response = self.client_ec2.create_tags(
                Resources = [ snapshot_id ],
                Tags= tags_array
            )

    def is_snapshot_completed(self, dryrun):
        if dryrun: return True
        response = self.client_ec2.describe_snapshots(
            SnapshotIds=[ self.new_snapshot_id ],
            Filters=[
                {
                    'Name': 'status',
                    'Values': [ 'pending', ]
                },
            ],
        )
        time.sleep(.3)
        if response['Snapshots']:
            #pp.pprint(response)
            self.set_new_snapshot_state(response['Snapshots'][0]['State'])
            return False
        else:
            self.fetch_new_snapshot_state()
            return True

    def set_new_snapshot_state(self, state):
        self.new_snapshot_state = state

    def fetch_new_snapshot_state(self):
        response = self.client_ec2.describe_snapshots( SnapshotIds=[ self.new_snapshot_id ], )
        time.sleep(.3)
        self.new_snapshot_state = response['Snapshots'][0]['State']
        return self.new_snapshot_state

    def get_new_snapshot_state(self, dryrun):
        if dryrun:
            self.new_snapshot_state = 'completed'
            return self.new_snapshot_state
        return self.new_snapshot_state

    def get_snapshot_freq_in_days(self):
        if ( not self.is_managed() or self.is_waived() ):
            return None
        return self.backup_set['snapshot frequency in days']

    def add_snapshot(self, snapshot):
        managed = self.is_managed()
        snapshot.set_managed(managed)
        if managed:
            if not self.is_waived():
                snapshot.set_expiration_in_days(self.backup_set['snapshots expire in days'])
            self.snapshots.append(snapshot)
            return True
        else:
            return False

    def dump(self):
        pp.pprint(self.__dict__)
        for snapshot in self.snapshots:
            pp.pprint(snapshot.__dict__)

    def set_tag(self, tag_key, tag_value):
        response = self.client_ec2.create_tags( Resources = [ self.id ], Tags= [ {'Key': tag_key, 'Value': tag_value} ] )

    def fetch_instance_id(self):
        response = self.client_ec2.describe_volumes( VolumeIds=[ self.id ], )
        time.sleep(.3)
        self.attachments = response['Volumes'][0]['Attachments']
        if self.attachments:
            self.instance_id = self.attachments[0]['InstanceId']
        else:
            self.instance_id = 'No associated instance'
        return self.instance_id
