from classes.aws_profiles import AWSProfiles
from classes.sa_assets_servers import SAAssetsServers
from classes.digests import Digests
from classes.config import Config

import socket
import logging
import pprint
pp = pprint.PrettyPrinter(indent=4)

config = Config().get_config()
logging.basicConfig(filename=config['logging']['system-maintenance'],level=logging.INFO,format='%(asctime)s %(message)s')
logging.info("\n\n\n>>>>>>>>>>>>>> START")
profiles_defs = config['profile_defs']

sa_assests_servers = SAAssetsServers()
digests = Digests()

aws_profiles = AWSProfiles(profiles_defs=p_profiles_defs)
aws_profiles.set_events_saserver_details(p_sa_assests_servers)
aws_profiles.set_if_events_new(p_digests)
if ( config['general']['owner_notifications'] ): aws_profiles.send_notifications_for_new_events()
if ( config['general']['send_report'] ): aws_profiles.send_sa_report()

digests.save_current_run_digests(p_aws_profiles.get_current_run_digests())

logging.info(">>>>>>>>>>>>>> END\n\n")





# END
