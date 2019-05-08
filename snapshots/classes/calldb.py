from classes.config import Config
import logging
import pymysql.cursors
import json
from classes.config import Config

import pprint
pp = pprint.PrettyPrinter(indent=4)

class CallDB():

    def __init__(self, cmd):
        self._config = Config().get_config()
        self._cmd = cmd
        self._rows = self.fetch_rows()

    def fetch_rows(self):
        connection = None
        try:
            connection = pymysql.connect(
                host=self._config['database']['hostname'], user=self._config['database']['user'],
                password=self._config['database']['password'], db=self._config['database']['db'],
                port=int(self._config['database']['port']),
                charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor
            )
            with connection.cursor() as cursor:
                cursor.execute(self._cmd)
                self._rows = []
                for row in cursor:
                    self._rows.append(row),
            return self._rows
        except:
            logging.info('CallDB: database unavailable or SQL error, exiting')
            print('Database unavailable or SQL error, exiting')
            exit()

    def get_rows(self):
        return self._rows
