from classes.aws_profiles import AWSProfiles
from classes.sa_assets_servers import SAAssetsServers
from classes.digests import Digests
from classes.config import Config
import socket
import logging
import pprint
pp = pprint.PrettyPrinter(indent=4)

m_config = Config().get_config()
logging.basicConfig(filename=m_config['logging']['path'],level=logging.INFO,format='%(asctime)s %(message)s')
logging.info("\n\n\n>>>>>>>>>>>>>> START")
p_profiles_defs = m_config['profile_defs']

p_sa_assests_servers = SAAssetsServers()
p_digests = Digests()

p_aws_profiles = AWSProfiles(profiles_defs=p_profiles_defs)
p_aws_profiles.set_events_saserver_details(p_sa_assests_servers)
p_aws_profiles.set_if_events_new(p_digests)
if ( m_config['general']['owner_notifications'] ): p_aws_profiles.send_notifications_for_new_events()
if ( m_config['general']['send_report'] ): p_aws_profiles.send_sa_report()

p_digests.save_current_run_digests(p_aws_profiles.get_current_run_digests())

logging.info(">>>>>>>>>>>>>> END\n\n")





# END
