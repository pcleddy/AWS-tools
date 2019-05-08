import datetime
import pytz
import boto3
from botocore.exceptions import ClientError
import time
import logging

logger = logging.getLogger('ec2-snapshots')


class Snapshot():

    def __init__(self, id, volume_id, creation_date, client_ec2):
        self.id = id
        self.volume_id = volume_id
        self.creation_date = creation_date
        self.expired = False
        self.client_ec2 = client_ec2
        self.expiration_in_days = None
        self.snapschedule_tag_flag = False

    def set_expiration_in_days(self, days):
        self.expiration_in_days = days

    def is_expired(self):
        if self.waived == True:
            self.expired = True
        elif self.expiration_in_days:
            age =  datetime.datetime.now(tz=pytz.utc) - self.creation_date
            self.old_days = age.days
            old_seconds = age.seconds
            self.old_hours = round(old_seconds / 3600)
            hours_expires = self.expiration_in_days * 24
            self.expired = ( age > datetime.timedelta(hours=hours_expires) )
        return self.expired

    def set_snapschedule_tag_flag(self, flag):
        self.snapschedule_tag_flag = flag

    def has_snapschedule_tag_flag(self):
        return self.snapschedule_tag_flag

    def set_has_volume_flag(self, flag):
        self.has_volume = flag

    def has_volume_flag(self):
        return self.has_volume

    def set_managed(self, flag):
        self.managed = flag

    def is_managed(self):
        if not self.managed:
            return False
        return self.managed

    def set_waived(self, flag):
        self.waived = flag

    def is_waived(self):
        return self.waived

    def delete(self, dryrun):
        if dryrun:
            logger.info("Dry run, not deleting snapshot: %s", self.id)
        elif ( self.snapschedule_tag_flag ):
            try:
                response = self.client_ec2.delete_snapshot( SnapshotId = self.id )
                time.sleep(.3)
            except ClientError as e:
                response = e.response
                if response['Error']['Code'] == 'InvalidSnapshot.InUse':
                    logger.warning(response['Error']['Message'] )
                else:
                    logger.error( "Unexpected error: %s" % e)
                    exit()
        else:
            logger.warning("Does not have SnapSchedule tag, not deleting snapshot: %s", self.id)
