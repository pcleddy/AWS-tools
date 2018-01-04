import pymysql.cursors
import pprint
from os.path import expanduser
import json

m_home = expanduser("~")
pp = pprint.PrettyPrinter(indent=4)

class ManagedVolumeDB():

    backup_sets = {
        'weekly': {
            'name': 'weekly', 'tag': 'JPLISSA-WEEKLY-KEEP1MONTH',
            'snapshot frequency': 'every 1 week', 'snapshot frequency in days': 7,
            'snapshots expire': '1 month', 'snapshots expire in days': 31
        },
        'daily': {
            'name': 'daily', 'tag': 'JPLISSA-DAILY-KEEP1WEEK',
            'snapshot frequency': 'every 1 day', 'snapshot frequency in days': 1,
            'snapshots expire': '1 week', 'snapshots expire in days': 7
        },
        'daily_keep2w': {
            'name': 'daily2wks', 'tag': 'JPLISSA-DAILY-KEEP2WEEKS',
            'snapshot frequency': 'every 1 day', 'snapshot frequency in days': 1,
            'snapshots expire': '2 weeks', 'snapshots expire in days': 14
        },
        'daily_keep4w': {
            'name': 'daily4wks', 'tag': 'JPLISSA-DAILY-KEEP4WEEKS',
            'snapshot frequency': 'every 1 day', 'snapshot frequency in days': 1,
            'snapshots expire': '4 weeks', 'snapshots expire in days': 28
        },
        'daily_keep12w': {
            'name': 'daily12wks', 'tag': 'JPLISSA-DAILY-KEEP12WEEKS',
            'snapshot frequency': 'every 1 day', 'snapshot frequency in days': 1,
            'snapshots expire': '12 weeks', 'snapshots expire in days': 84
        },
        'waive': {
            'name': 'waive', 'tag': 'JPLISSA-WAIVE',
        }
    }

    def __init__(self, m_env):
        self.volume_index = self.get_volume_info(m_env)

    def get_config(self, m_env):
        if (m_env == 'dev'):
            m_dir_config = m_home + '/.ec2-snapshots/config.json'
        elif (m_env == 'prod-portforward'):
            m_dir_config = m_home + '/.ec2-snapshots/prod-pf-config.json'
        else:
             m_dir_config = '/opt/aws/ec2-snapshots/config_v2.json'

        with open(m_dir_config) as m_data_file:
            return json.load(m_data_file)

    def get_volume_info(self, m_env):
        m_config = self.get_config(m_env)
        m_volume_index = {}


        m_connection = pymysql.connect(
            host=m_config['database']['hostname'], user=m_config['database']['user'],
            password=m_config['database']['password'], db=m_config['database']['db'],
            port=int(m_config['database']['port']),
            charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor
        )

        try:
            with m_connection.cursor() as m_cursor:
                m_sql = 'SELECT volume_id, snapshot_schedule FROM assets.ec2_snapshot_schedules'
                m_cursor.execute(m_sql)
                for m_row in m_cursor:
                    m_volume_index[m_row['volume_id']] = ManagedVolumeDB.backup_sets[m_row['snapshot_schedule']]
        finally:
            m_connection.close()

        return m_volume_index

    def get_snapshot_expiration_in_days(self, m_volume_id):
        if self.is_managed(m_volume_id):
            return ManagedVolumeDB.backup_sets[self.volume_index[m_volume_id]['backup_set_name']]['snapshots expire in days']
        else:
            return None

    def is_managed(self, m_volume_id):
        return ( m_volume_id in self.volume_index )

    def get_backup_set(self, m_volume_id):
        if m_volume_id in self.volume_index:
            return self.volume_index[m_volume_id]
        else:
            return None

    def is_snapshot_waived(self, m_volume_id):
        if m_volume_id in self.volume_index:
            if ( self.volume_index[m_volume_id]['name'] == 'waive' ):
                return True
            else:
                return False
        else:
            return None
