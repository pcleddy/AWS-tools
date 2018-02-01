from classes.config import Config
import pymysql.cursors
import pprint
from os.path import expanduser
import json

m_home = expanduser("~")
pp = pprint.PrettyPrinter(indent=4)

class ManagedVolumeDB():

    def __init__(self):
        self._config = Config().get_config()
        self.volume_index = self.get_volume_info()

    def get_volume_info(self):
        m_volume_index = {}

        m_connection = pymysql.connect(
            host=self._config['database']['hostname'], user=self._config['database']['user'],
            password=self._config['database']['password'], db=self._config['database']['db'],
            port=int(self._config['database']['port']),
            charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor
        )

        try:
            with m_connection.cursor() as m_cursor:
                m_sql = 'SELECT volume_id, snapshot_schedule FROM assets.ec2_snapshot_schedules'
                m_cursor.execute(m_sql)
                for m_row in m_cursor:
                    m_volume_index[m_row['volume_id']] = self._config['backup_sets'][m_row['snapshot_schedule']]
        finally:
            m_connection.close()

        return m_volume_index

    def get_snapshot_expiration_in_days(self, m_volume_id):
        if self.is_managed(m_volume_id):
            return self._config['backup_sets'][self.volume_index[m_volume_id]['backup_set_name']]['snapshots expire in days']
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
