import logging
import boto3
import pickle
import os.path
import pprint
pp = pprint.PrettyPrinter(indent=4)


class Digests(object):

    p_storage_path = '/var/tmp/'
    p_tmp_db_filename = 'events.pkl'

    def __init__(self):
        logging.basicConfig(filename='/var/tmp/aws-tools.log',level=logging.INFO,format='%(asctime)s %(message)s')
        self.set_last_run_digests()

    def set_last_run_digests(self):
        self.load()

    def load(self):
        p_fullpath = Digests.p_storage_path + Digests.p_tmp_db_filename
        if ( os.path.isfile(p_fullpath) ):
            p_filehandle = open(p_fullpath, 'rb')
            p_last_run_digests = pickle.load(p_filehandle)
            p_filehandle.close()
        else:
            p_last_run_digests = []
        self._last_run_digests = p_last_run_digests
        logging.info('DIGESTS: last run digests: ' + str(self._last_run_digests))

    def get_last_run_digests(self):
        return self._last_run_digests

    def save_current_run_digests(self, current_digests):
        self.save(current_digests)

    def save(self, current_digests):
        p_filehandle = open(Digests.p_storage_path + Digests.p_tmp_db_filename, 'wb')
        pickle.dump(current_digests, p_filehandle)
        p_filehandle.close()
