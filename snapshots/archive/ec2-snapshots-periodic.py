import boto3
import pickle
import datetime
from jinja2 import Template
import time
import logging
import sys

from classes.volume import Volume
from classes.snapshot import Snapshot
from classes.managed_volume_db import ManagedVolumeDB
from classes.emailv2 import Emailv2
from classes.config import Config
from classes.notification import Notification

import pprint
pp = pprint.PrettyPrinter(indent=4)

config = Config().get_config()
logging.basicConfig(filename=config['snapshots']['logging'],level=logging.INFO,format='%(asctime)s %(message)s')

logging.info("\n\n\n>>>>>>>>>>>>>> START")

debug = config['snapshots']['debug']
dryrun = config['snapshots']['dryrun']
send_email = config['snapshots']['email']
live = config['snapshots']['live']
profiles = config['snapshots']['snapshot_aws_profiles']

# get frequencies

managed_volume_db = ManagedVolumeDB()

# for each profile, get volumes and snapshots

volumes = []
volume_index = {}
snapshots = []
snapshot_index = {}

expired_snapshots = []

for profile_name in profiles:

    session_ec2 = boto3.Session(profile_name = profile_name)
    client_ec2 = session_ec2.client('ec2')

    if (live):

        logging.info('Live: fetching live data')

        volumes_fetched = client_ec2.describe_volumes()
        snapshots_fetched = client_ec2.describe_snapshots(OwnerIds=['self'])

        # save
        filehandle = open(config['snapshots']['storage']['path'] + '/' + profile_name + config['snapshots']['storage']['volumes_suffix'], 'wb')
        pickle.dump(volumes_fetched, filehandle)
        filehandle.close()

        filehandle = open(config['snapshots']['storage']['path'] + '/' + profile_name + config['snapshots']['storage']['snapshots_suffix'], 'wb')
        pickle.dump(snapshots_fetched, filehandle)
        filehandle.close()

    else:

        logging.info('Not live: reading stored data')

        filehandle = open(config['snapshots']['storage']['path'] + '/' + profile_name + config['snapshots']['storage']['volumes_suffix'], 'rb')
        volumes_fetched = pickle.load(filehandle)
        filehandle.close()

        filehandle = open(config['snapshots']['storage']['path'] + '/' + profile_name + config['snapshots']['storage']['snapshots_suffix'], 'rb')
        snapshots_fetched = pickle.load(filehandle)
        filehandle.close()

    volumes_fetched = client_ec2.describe_volumes()
    snapshots_fetched = client_ec2.describe_snapshots(OwnerIds=['self'])

    # volumes returned from AWS API
    for volume_fetched in volumes_fetched['Volumes']:
        volume_id = volume_fetched['VolumeId']
        volume = Volume(
            volume_id,
            managed_volume_db.get_backup_set(volume_id),
            client_ec2,
            profile_name
        )
        volumes.append(volume)
        volume_index.update({volume.id: volume})

    for snapshot_fetched in snapshots_fetched['Snapshots']:
        volume_id = snapshot_fetched['VolumeId']
        snapshot = Snapshot(
            snapshot_fetched['SnapshotId'],
            volume_id,
            snapshot_fetched['StartTime'],
            client_ec2
        )
        snapshots.append(snapshot)
        snapshot_index.update({snapshot.id: snapshot})
        if volume_id in volume_index:
            volume_index[volume_id].add_snapshot(snapshot)
            snapshot.set_has_volume_flag(True)
        else:
            snapshot.set_has_volume_flag(False)
        snapshot.set_waived(managed_volume_db.is_snapshot_waived(volume_id))

    results = client_ec2.describe_snapshots( OwnerIds=['self'], Filters=[ { 'Name': 'tag-key', 'Values': [ 'SnapSchedule', ] }, ], )
    for s in results['Snapshots']:
        snapshot_index[s['SnapshotId']].set_snapschedule_tag_flag(True)

volumes_needing_snapshot = [ volume for volume in volumes if volume.needs_snapshot() ]
for volume in volumes_needing_snapshot:
    logging.info("Snapshotting: %s", volume.id)
    volume.take_snapshot(dryrun)

# delete expired and tagged snapshots
expired_and_tagged_managed = [
    snapshot for snapshot in snapshots if (
        snapshot.is_expired()
        and snapshot.has_snapschedule_tag_flag()
        and snapshot.is_managed()
    )
]

for snapshot in expired_and_tagged_managed:
    logging.info("Deleting snapshot: %s of %s", snapshot.id, snapshot.volume_id)
    if ( not snapshot.is_waived() ):
        logging.info("Age: %s days, %s hours; expiration in days: %s", snapshot.old_days, snapshot.old_hours, snapshot.expiration_in_days)
    snapshot.delete(dryrun)

# Clean up tagged snapshots with no associated volume
snapshots_no_volume_tagged = [ snapshot for snapshot in snapshots if ( (not snapshot.has_volume_flag()) and snapshot.has_snapschedule_tag_flag() ) ]
for snapshot in snapshots_no_volume_tagged:
    logging.info("Deleting tagged snapshot with no associated volume: %s", snapshot.id)
    snapshot.delete(dryrun)

if debug:

    print('Volumes')
    for v in volumes:
        v.dump()
        print('-----------')

    print('Snapshots')
    for s in snapshots:
        pp.pprint(s.__dict__)
        print('-----------')

    print('Volumes Needing Snapshot')
    for v in volumes_needing_snapshot:
        pp.pprint(v.__dict__)

    print('Snapshots Expired, Tagged and Managed')
    for s in expired_and_tagged_managed:
        pp.pprint(s.__dict__)

if dryrun :
    print('This was a dry run')

for volume in volumes_needing_snapshot:
    multiplier = 1
    while True:
        if volume.is_snapshot_completed(dryrun):
            logging.debug("Snapshot complete: %s of volume %s)", volume.new_snapshot_id, volume.id)
            break
        else:
            logging.info("Sleeping: %s for volume %s is pending (multiplier: %s)", volume.new_snapshot_id, volume.id, multiplier)
            time.sleep(.1 * multiplier)
            multiplier *= 2
            if (multiplier > 2**15):
                logging.info("Snapshot pending long time, skipping")
                break

if not send_email:
    exit()

tmp_text =''
for profile_name in profiles:

    # stats for volumes
    v_snapshots_total = [v for v in volumes_needing_snapshot
        if ( v.profile == profile_name ) ]
    v_snapshots_complete = [v for v in volumes_needing_snapshot
        if ( v.get_new_snapshot_state(dryrun) == 'completed' and v.profile == profile_name ) ]
    v_snapshots_pending = [v for v in volumes_needing_snapshot
        if (v.get_new_snapshot_state(dryrun) == 'pending' and v.profile == profile_name )]
    v_snapshots_error = [v for v in volumes_needing_snapshot
        if (v.get_new_snapshot_state(dryrun) == 'error' and v.profile == profile_name )]

    tmp_text += '<h2>' + profile_name + '</h2>' + "\n"

    tmp_text += "Volumes backed up: {}/{} <br />\n".format(len(v_snapshots_complete), (len(v_snapshots_total)))
    tmp_text += "Volumes pending: {} <br />\n".format(len(v_snapshots_pending))
    tmp_text += "Volumes failed: {} <br />\n".format((len(v_snapshots_error)))

    for v in v_snapshots_error:
        tmp_text += "{} | {} | Snapshot failed.    <br />\n".format(v.fetch_instance_id(), v.id)

    tmp_text += "\n\n\n\n"

# send email report

text = ''
if dryrun: text += '<h1>DRY RUN!</h1>'
text += '<p>' + tmp_text + '<br />'

template_raw = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Volume/Snapshot Report</title>
</head>
<body>
    <h1>Volume/Snapshot Report</h1>
    {{ string }}
</body>
</html>'''

template = Template(template_raw)
html = template.render(string = text)


logging.info("Sending email report")

p_subject = 'Volumes/Snapshot report'
p_email_attrs = {
    'email_type': config['general']['email_type'],
    'email_to': config['general']['sa_recipients'],
    'email_from': config['general']['email_from'],
    'subject': p_subject,
    'html': html,
    'text': text,
}
Notification('email', p_email_attrs)


# END
