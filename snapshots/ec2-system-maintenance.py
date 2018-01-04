from classes.aws_profiles import AWSProfiles
from classes.sa_assets_servers import SAAssetsServers
from classes.digests import Digests

import socket
import logging

### INIT

logging.basicConfig(filename='/var/tmp/aws-tools.log',level=logging.INFO,format='%(asctime)s %(message)s')

if ('admin' in socket.gethostname()):
    p_env = 'prod'
else:
    #p_env = 'dev'
    p_env = 'prod-portforward'

p_profiles_defs = [
    { 'profile_name': 'my-public', 'profile_region': 'us-west-1' },
    { 'profile_name': 'my-public', 'profile_region': 'us-west-2' },
]

p_sa_assests_servers = SAAssetsServers(p_env)
p_digests = Digests()

p_aws_profiles = AWSProfiles(profiles_defs=p_profiles_defs)
p_aws_profiles.set_events_saserver_details(p_sa_assests_servers)
p_aws_profiles.set_if_events_new(p_digests)
p_aws_profiles.send_notifications_for_new_events()
p_aws_profiles.send_sa_report()

p_digests.save_current_run_digests(p_aws_profiles.get_current_run_digests())

logging.info(">>>>>>>>>>>>>> END\n\n\n\n")





# END
