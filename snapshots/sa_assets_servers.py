from classes.config import Config
from classes.calldb import CallDB
import re
import pprint
pp = pprint.PrettyPrinter(indent=4)

class SAAssetsServers(object):

    def __init__(self, **kwargs):
        self._config = Config().get_config()
        m_calldb = CallDB(self._config['sql'])
        m_rows = m_calldb.get_rows()
        m_sa_assets_servers = {}
        for m_r in m_rows:

            m = re.search('.+?\-([iI]\-.*)', m_r['pi'])
            m_aws_acct_type = re.search('(.+?)\-[iI]\-.*', m_r['pi']).group(1)

            # if the server already exists, just add the additional owner to the list of owners
            if (m.group(1).lower() in m_sa_assets_servers):
                m_sa_assets_servers[m.group(1).lower()]['owners'].append(m_r['name'])
            # if server does not exist yet, create it, along with all the details
            else:
                m_sa_assets_servers[m.group(1).lower()] = {
                    'owners': [m_r['name']],
                    'cog_admin': m_r['cog_admin'],
                    'hostname': m_r['hostname'],
                    'domain': m_r['domain'],
                    'device_name': m_r['device_name'],
                    'ip_address': m_r['ip_address'],
                    'aws_acct_type': m_aws_acct_type
                }
        self._sa_assets_servers = m_sa_assets_servers

    def get_saserver_details(self):
        return self._sa_assets_servers
