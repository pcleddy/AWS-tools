from classes.config import Config
from classes.calldb import CallDB
import re
import pprint
pp = pprint.PrettyPrinter(indent=4)

class SAAssetsServers(object):

    def __init__(self, **kwargs):
        self._config = Config().get_config()
        calldb = CallDB(self._config['sql'])
        rows = calldb.get_rows()
        sa_assets_servers = {}
        for r in rows:

            m = re.search('.+?\-([iI]\-.*)', r['pi'])
            aws_acct_type = re.search('(.+?)\-[iI]\-.*', r['pi']).group(1)

            # if the server already exists, just add the additional owner to the list of owners
            if (m.group(1).lower() in sa_assets_servers):
                sa_assets_servers[m.group(1).lower()]['owners'].append(r['name'])
            # if server does not exist yet, create it, along with all the details
            else:
                sa_assets_servers[m.group(1).lower()] = {
                    'owners': [r['name']],
                    'cog_admin': r['cog_admin'],
                    'hostname': r['hostname'],
                    'domain': r['domain'],
                    'device_name': r['device_name'],
                    'ip_address': r['ip_address'],
                    'aws_acct_type': aws_acct_type
                }
        self._sa_assets_servers = sa_assets_servers

    def get_saserver_details(self):
        return self._sa_assets_servers
