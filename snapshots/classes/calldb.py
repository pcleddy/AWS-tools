import pymysql.cursors
import pprint
from os.path import expanduser
import json

m_home = expanduser("~")
pp = pprint.PrettyPrinter(indent=4)

class CallDB():

    def __init__(self, m_env, m_cmd):
        self.cmd = m_cmd
        self.config = self.get_config(m_env)
        self.rows = self.fetch_rows()

    def get_config(self, m_env):
        if (m_env == 'dev'):
            m_dir_config = m_home + '/.ec2-snapshots/config.json'
        elif (m_env == 'prod-portforward'):
            m_dir_config = m_home + '/.ec2-snapshots/prod-pf-config.json'
        else:
             m_dir_config = '/opt/aws/ec2-snapshots/config_v2.json'

        with open(m_dir_config) as m_data_file:
            return json.load(m_data_file)

    def fetch_rows(self):
        m_connection = pymysql.connect(
            host=self.config['database']['hostname'], user=self.config['database']['user'],
            password=self.config['database']['password'], db=self.config['database']['db'],
            port=int(self.config['database']['port']),
            charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor
        )

        try:
            with m_connection.cursor() as m_cursor:
                m_sql = self.cmd
                m_cursor.execute(m_sql)
                self.rows = []
                for m_row in m_cursor:
                    self.rows.append(m_row)
        finally:
            m_connection.close()

        return self.rows

    def get_rows(self):
        return self.rows
