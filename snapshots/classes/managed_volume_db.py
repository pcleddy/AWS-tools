from classes.config import Config
import pymysql.cursors
import pprint
from os.path import expanduser
import json

home = expanduser("~")
pp = pprint.PrettyPrinter(indent=4)

class ManagedVolumeDB():

    def __init__(self):
        self._config = Config().get_config()
        self.volume_index = self.get_volume_info()

    def get_volume_info(self):
        volume_index = {}

        connection = pymysql.connect(
            host=self._config['database']['hostname'], user=self._config['database']['user'],
            password=self._config['database']['password'], db=self._config['database']['db'],
            port=int(self._config['database']['port']),
            charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor
        )

        try:
            with connection.cursor() as cursor:
                sql = 'SELECT volume_id, snapshot_schedule FROM assets.ec2_snapshot_schedules'
                cursor.execute(sql)
                for row in cursor:
                    volume_index[row['volume_id']] = self._config['backup_sets'][row['snapshot_schedule']]
        finally:
            connection.close()

        return volume_index

    def get_snapshot_expiration_in_days(self, volume_id):
        if self.is_managed(volume_id):
            return self._config['backup_sets'][self.volume_index[volume_id]['backup_set_name']]['snapshots expire in days']
        else:
            return None

    def is_managed(self, volume_id):
        return ( volume_id in self.volume_index )

    def get_backup_set(self, volume_id):
        if volume_id in self.volume_index:
            return self.volume_index[volume_id]
        else:
            return None

    def is_snapshot_waived(self, volume_id):
        if volume_id in self.volume_index:
            if ( self.volume_index[volume_id]['name'] == 'waive' ):
                return True
            else:
                return False
        else:
            return None
