import datetime
import pytz
import boto3
from botocore.exceptions import ClientError
import time
import logging

logger = logging.getLogger('ec2-snapshots')


class Snapshot():

    def __init__(self, m_id, m_volume_id, m_creation_date, m_client_ec2):
        self.id = m_id
        self.volume_id = m_volume_id
        self.creation_date = m_creation_date
        self.expired = False
        self.client_ec2 = m_client_ec2
        self.expiration_in_days = None
        self.snapschedule_tag_flag = False

    def set_expiration_in_days(self, m_days):
        self.expiration_in_days = m_days

    def is_expired(self):
        if self.waived == True:
            self.expired = True
        elif self.expiration_in_days:
            m_age =  datetime.datetime.now(tz=pytz.utc) - self.creation_date
            self.old_days = m_age.days
            m_old_seconds = m_age.seconds
            self.old_hours = round(m_old_seconds / 3600)
            m_hours_expires = self.expiration_in_days * 24
            self.expired = ( m_age > datetime.timedelta(hours=m_hours_expires) )
        return self.expired

    def set_snapschedule_tag_flag(self, m_flag):
        self.snapschedule_tag_flag = m_flag

    def has_snapschedule_tag_flag(self):
        return self.snapschedule_tag_flag

    def set_has_volume_flag(self, m_flag):
        self.has_volume = m_flag

    def has_volume_flag(self):
        return self.has_volume

    def set_managed(self, m_flag):
        self.managed = m_flag

    def is_managed(self):
        if not self.managed:
            return False
        return self.managed

    def set_waived(self, m_flag):
        self.waived = m_flag

    def is_waived(self):
        return self.waived

    def delete(self, m_dryrun):
        if m_dryrun:
            logger.info("Dry run, not deleting snapshot: %s", self.id)
        elif ( self.snapschedule_tag_flag ):
            try:
                m_response = self.client_ec2.delete_snapshot( SnapshotId = self.id )
                time.sleep(.3)
            except ClientError as e:
                m_response = e.response
                if m_response['Error']['Code'] == 'InvalidSnapshot.InUse':
                    logger.warning(m_response['Error']['Message'] )
                else:
                    logger.error( "Unexpected error: %s" % e)
                    exit()
        else:
            logger.warning("Does not have SnapSchedule tag, not deleting snapshot: %s", self.id)
