import boto3
from classes.email import Email
from classes.calldb import CallDB
from classes.status_event import StatusEvent
from lib.servers import get_server_index
from classes.emailv2 import Emailv2
import re
import pickle
import os.path

import pprint
pp = pprint.PrettyPrinter(indent=4)

# init

m_storage_path = '/var/tmp/'
m_tmp_db_filename = 'status_events.pkl'

m_dryrun = False
m_debug = True
m_env = 'dev'
m_env = 'prod-portforward'
#m_env = 'prod'
m_profiles = ['test'] if (m_env == 'dev') else ['public1', 'public2']

m_server_index = get_server_index(m_env)

if ( os.path.isfile(m_storage_path + m_tmp_db_filename) ):
    m_filehandle = open(m_storage_path + m_tmp_db_filename, 'rb')
    m_status_events_lastrun = pickle.load(m_filehandle)
    m_filehandle.close()
else:
    m_status_events_lastrun = []

m_status_events = []
for m_profile_name in m_profiles:
    m_session_ec2 = boto3.Session(profile_name = m_profile_name)
    m_client_ec2 = m_session_ec2.client('ec2')
    m_response = m_client_ec2.describe_instance_status(
        Filters=[
            {
                'Name': 'event.code',
                'Values': [ 'instance-reboot', 'system-reboot', 'system-maintenance', 'instance-retirement', 'instance-stop' ]
            },
        ],
    )
    if m_response['InstanceStatuses']:
        for m_inst_status in m_response['InstanceStatuses']:
            for se in m_inst_status['Events']:
                m_status_event = StatusEvent(
                    m_profile_name = m_profile_name,
                    m_server = m_server_index[m_inst_status['InstanceId']],
                    m_desc = se['Description'],
                    m_not_before_date = se['NotBefore'],
                    m_not_after_date = se['NotAfter'],
                )
                m_status_events.append(m_status_event)

m_lastrun_digests = []
for se in m_status_events_lastrun: m_lastrun_digests.append(se.get_digest())

for se in [se for se in m_status_events if ( se.get_digest() not in m_lastrun_digests ) ]:
    se.set_customer_notified(False)

for se in [se for se in m_status_events if ( se.is_complete() ) ]:
    se.set_complete()

m_filehandle = open(m_storage_path + m_tmp_db_filename, 'wb')
pickle.dump(m_status_events, m_filehandle)
m_filehandle.close()

for se in m_status_events:
    if ( not se.get_customer_notified() ):
        print('Send notification')
    se.dump()


# send report

if (m_env == 'dev' or m_env == 'prod-portforward'):
    m_email_from = 'paul@mydomain'
    m_email_to = ['paul@mydomain']
    m_ses_profile = 'test-east'
    m_email_type = 'ses'
else:
    m_email_from = 'root@mydomain'
    if (m_dryrun or m_debug):
        m_email_to = ['paul@mydomain']
    else:
        m_email_to = ['paul@mydomain', 'bob@mydomain']
    m_ses_profile = 'public1'
    m_email_type = 'localhost'

m_subject = 'Maintenance report'
m_html = ''
m_text = ''

m_email_attrs = {
    'ses_profile': m_ses_profile,
    'email_type': m_email_type,
    'email_from': m_email_from,
    'email_to': m_email_to,
    'subject': m_subject,
    'html': m_html,
    'text': m_text
}
#Email(m_ses_profile, m_subject, m_html, {}, m_email_from, m_email_to)
Emailv2(email_attrs = m_email_attrs, email_type = m_email_type)
