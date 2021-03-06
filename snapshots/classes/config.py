import socket
import yaml
import os.path
home = os.path.expanduser("~")

class Config(object):

    def __init__(self):
        if ( self.on_prod() and os.path.isfile('/opt/aws/ec2-snapshots/config.yml') ):
             dir_config = '/opt/aws/ec2-snapshots/config.yml'
        elif ( os.path.isfile(home + '/.ec2-snapshots/config.yml') ):
            dir_config = home + '/.ec2-snapshots/config.yml'
        else:
            print('ERROR: No config file found, exiting')
            exit()

        with open(dir_config, 'r') as ymlfile:
            self._config = yaml.load(ymlfile)


    def on_prod(self):
        on_prod_flag = 'jplis-sa-wfe' in socket.gethostname()
        return on_prod_flag

    def get_env(self):
        return self._env

    def get_config(self):
        return self._config
