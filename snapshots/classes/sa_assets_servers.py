from classes.calldb import CallDB

import logging
import re
import pprint
pp = pprint.PrettyPrinter(indent=4)


class SAAssetsServers(object):

    p_sql_cmd = '''
        select name, s.cog_admin, s.property_id as pi, s.hostname, s.domain, device_name, ip_address
           from servers as s, servers_contacts as sc, servers_ip_address_hostname as siah
           where
           	s.`id` = sc.`id__servers`
           	and (s.property_id LIKE 'GOV%' or s.property_id LIKE 'EC%')
           	and s.hostname_ip_address_id = siah.id
           ;
           '''

    def __init__(self, env, **kwargs):
        self._env = env
        logging.basicConfig(filename='/var/tmp/aws-tools.log',level=logging.INFO,format='%(asctime)s %(message)s')
        m_calldb = CallDB(self._env, SAAssetsServers.p_sql_cmd)
        m_rows = m_calldb.get_rows()
        m_sa_assets_servers = {}
        for m_r in m_rows:
            m = re.search('.+?\-([iI]\-.*)', m_r['pi'])
            m_aws_acct_type = re.search('(.+?)\-[iI]\-.*', m_r['pi']).group(1)
            m_sa_assets_servers[m.group(1).lower()] = {
                'name': m_r['name'],
                'cog_admin': m_r['cog_admin'],
                'hostname': m_r['hostname'],
                'domain': m_r['domain'],
                'device_name': m_r['device_name'],
                'ip_address': m_r['ip_address'],
                'aws_acct_type': m_aws_acct_type
            }
        self._sa_assets_servers = m_sa_assets_servers
        #logging.info(self._owners)
        #exit()

    def get_saserver_details(self):
        return self._sa_assets_servers
