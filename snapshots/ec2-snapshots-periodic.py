import boto3
import pickle
import datetime
from jinja2 import Template
import time

from classes.volume import Volume
from classes.snapshot import Snapshot
from classes.managed_volume_db import ManagedVolumeDB
from classes.emailv2 import Emailv2
from classes.plot import Plot

import pprint
pp = pprint.PrettyPrinter(indent=4)

import logging
import sys

logger = logging.getLogger('ec2-snapshots')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

m_debug = False
m_dryrun = False
m_do_stats_and_email = True
m_live = True
#m_env = 'dev'
#m_env = 'prod-portforward'
m_env = 'prod'
m_profiles = ['test'] if (m_env == 'dev') else ['public1', 'public2']

# get frequencies

m_managed_volume_db = ManagedVolumeDB(m_env)


# for each profile, get volumes and snapshots

m_volumes = []
m_volume_index = {}
m_snapshots = []
m_snapshot_index = {}


m_expired_snapshots = []

for m_profile_name in m_profiles:

    m_session_ec2 = boto3.Session(profile_name = m_profile_name)
    m_client_ec2 = m_session_ec2.client('ec2')


    # fetch

    m_storage_path = '/tmp/'

    if (m_live):

        m_volumes_fetched = m_client_ec2.describe_volumes()
        m_snapshots_fetched = m_client_ec2.describe_snapshots(OwnerIds=['self'])

        # save
        m_filehandle = open(m_storage_path + m_profile_name + '_vols.pkl', 'wb')
        pickle.dump(m_volumes_fetched, m_filehandle)
        m_filehandle.close()

        m_filehandle = open(m_storage_path + m_profile_name + '_snaps.pkl', 'wb')
        pickle.dump(m_snapshots_fetched, m_filehandle)
        m_filehandle.close()

    else:

        m_filehandle = open(m_storage_path + m_profile_name + '_vols.pkl', 'rb')
        m_volumes_fetched = pickle.load(m_filehandle)
        m_filehandle.close()

        m_filehandle = open(m_storage_path + m_profile_name + '_snaps.pkl', 'rb')
        m_snapshots_fetched = pickle.load(m_filehandle)
        m_filehandle.close()


    # volumes returned from AWS API
    for m_volume_fetched in m_volumes_fetched['Volumes']:
        m_volume_id = m_volume_fetched['VolumeId']
        m_volume = Volume(
            m_volume_id,
            m_managed_volume_db.get_backup_set(m_volume_id),
            m_client_ec2,
            m_profile_name
        )
        m_volumes.append(m_volume)
        m_volume_index.update({m_volume.id: m_volume})

    for m_snapshot_fetched in m_snapshots_fetched['Snapshots']:
        m_volume_id = m_snapshot_fetched['VolumeId']
        m_snapshot = Snapshot(
            m_snapshot_fetched['SnapshotId'],
            m_volume_id,
            m_snapshot_fetched['StartTime'],
            m_client_ec2
        )
        m_snapshots.append(m_snapshot)
        m_snapshot_index.update({m_snapshot.id: m_snapshot})
        if m_volume_id in m_volume_index:
            m_volume_index[m_volume_id].add_snapshot(m_snapshot)
            m_snapshot.set_has_volume_flag(True)
        else:
            m_snapshot.set_has_volume_flag(False)
        m_snapshot.set_waived(m_managed_volume_db.is_snapshot_waived(m_volume_id))

    m_results = m_client_ec2.describe_snapshots( OwnerIds=['self'], Filters=[ { 'Name': 'tag-key', 'Values': [ 'SnapSchedule', ] }, ], )
    for s in m_results['Snapshots']:
        m_snapshot_index[s['SnapshotId']].set_snapschedule_tag_flag(True)

m_volumes_needing_snapshot = [ m_volume for m_volume in m_volumes if m_volume.needs_snapshot() ]
for m_volume in m_volumes_needing_snapshot:
    logger.info("Snapshotting: %s", m_volume.id)
    m_volume.take_snapshot(m_dryrun)

# delete expired and tagged snapshots
m_expired_and_tagged_managed = [
    m_snapshot for m_snapshot in m_snapshots if (
        m_snapshot.is_expired()
        and m_snapshot.has_snapschedule_tag_flag()
        and m_snapshot.is_managed()
    )
]

for m_snapshot in m_expired_and_tagged_managed:
    logger.info("Deleting snapshot: %s of %s", m_snapshot.id, m_snapshot.volume_id)
    if ( not m_snapshot.is_waived() ):
        logger.info("Age: %s days, %s hours; expiration in days: %s", m_snapshot.old_days, m_snapshot.old_hours, m_snapshot.expiration_in_days)
    m_snapshot.delete(m_dryrun)

# Clean up tagged snapshots with no associated volume
snapshots_no_volume_tagged = [ m_snapshot for m_snapshot in m_snapshots if ( (not m_snapshot.has_volume_flag()) and m_snapshot.has_snapschedule_tag_flag() ) ]
for m_snapshot in snapshots_no_volume_tagged:
    logger.info("Deleting tagged snapshot with no associated volume: %s", m_snapshot.id)
    m_snapshot.delete(m_dryrun)

if m_debug:

    print('Volumes')
    for v in m_volumes:
        v.dump()
        print('-----------')

    print('Snapshots')
    for s in m_snapshots:
        pp.pprint(s.__dict__)
        print('-----------')

    print('Volumes Needing Snapshot')
    for v in m_volumes_needing_snapshot:
        pp.pprint(v.__dict__)

    print('Snapshots Expired, Tagged and Managed')
    for s in m_expired_and_tagged_managed:
        pp.pprint(s.__dict__)

if m_dryrun :
    print('This was a dry run')

for m_volume in m_volumes_needing_snapshot:
    m_multiplier = 1
    while True:
        if m_volume.is_snapshot_completed(m_dryrun):
            logger.debug("Snapshot complete: %s of volume %s)", m_volume.new_snapshot_id, m_volume.id)
            break
        else:
            logger.info("Sleeping: %s for volume %s is pending (multiplier: %s)", m_volume.new_snapshot_id, m_volume.id, m_multiplier)
            time.sleep(.1 * m_multiplier)
            m_multiplier *= 2
            if (m_multiplier > 2**15):
                logger.info("Snapshot pending long time, skipping")
                break

if not m_do_stats_and_email:
    exit()

m_tmp_text =''
for m_profile_name in m_profiles:

    # stats for volumes
    m_v_snapshots_total = [v for v in m_volumes_needing_snapshot
        if ( v.profile == m_profile_name ) ]
    m_v_snapshots_complete = [v for v in m_volumes_needing_snapshot
        if ( v.get_new_snapshot_state(m_dryrun) == 'completed' and v.profile == m_profile_name ) ]
    m_v_snapshots_pending = [v for v in m_volumes_needing_snapshot
        if (v.get_new_snapshot_state(m_dryrun) == 'pending' and v.profile == m_profile_name )]
    m_v_snapshots_error = [v for v in m_volumes_needing_snapshot
        if (v.get_new_snapshot_state(m_dryrun) == 'error' and v.profile == m_profile_name )]

    m_tmp_text += '<h2>' + m_profile_name + '</h2>' + "\n"

    m_tmp_text += "Volumes backed up: {}/{} <br />\n".format(len(m_v_snapshots_complete), (len(m_v_snapshots_total)))
    m_tmp_text += "Volumes pending: {} <br />\n".format(len(m_v_snapshots_pending))
    m_tmp_text += "Volumes failed: {} <br />\n".format((len(m_v_snapshots_error)))

    for v in m_v_snapshots_error:
        m_tmp_text += "{} | {} | Snapshot failed.    <br />\n".format(v.fetch_instance_id(), v.id)

    m_tmp_text += "\n\n\n\n"

m_s3_profile = 'test' if (m_env == 'dev') else 'public1'

# send email report

m_text = ''
if m_dryrun: m_text += '<h1>DRY RUN!</h1>'
m_text += '<p>' + m_tmp_text + '<br />'

m_subject = 'Volumes/Snapshot report'

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

m_template_raw = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Volume/Snapshot Report</title>
</head>
<body>
    <h1>Volume/Snapshot Report</h1>
    {{ m_string }}
</body>
</html>'''

m_template = Template(m_template_raw)
m_html = m_template.render(m_string = m_text)


logger.info("Sending email report")

m_email_attrs = {
    'ses_profile': m_ses_profile,
    'email_type': m_email_type,
    'email_from': m_email_from,
    'email_to': m_email_to,
    'subject': m_subject,
    'html': m_html,
    'text': m_text
}
Emailv2(email_attrs = m_email_attrs, email_type = m_email_type)




# END
