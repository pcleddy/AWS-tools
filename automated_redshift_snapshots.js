#!/usr/bin/env node

var m_aws = require('aws-sdk');
var _ = require('underscore');
var m_moment = require('moment');
var m_winston = require('winston');

m_winston.remove(m_winston.transports.Console);
m_winston.add(m_winston.transports.File, { filename: '/var/tmp/automated_redshift_snapshots.log' });

m_aws.config.update({
    region: 'us-east-1',
    //logger: process.stdout
})
var m_now = m_moment().format("YYYY-MM-DD-HH");

m_winston.info('START')

var m_redshift = new m_aws.Redshift();
var m_redshift_clusters = [
    {
        name: 'slice-dwh-poc',
        frequency: 'daily',
        keep_days: '14'
    }
]

function f_delete_snapshots(m_snapshots) {
    _.each(m_snapshots.Snapshots, function (m_snapshot) {
        var m_params = { SnapshotIdentifier: m_snapshot.SnapshotIdentifier, SnapshotClusterIdentifier: m_snapshot.ClusterIdentifier };
        m_redshift.deleteClusterSnapshot(m_params, function(m_err, m_data) {
            if (m_err) m_winston.info(m_err, m_err.stack);
            else { m_winston.info('Deleting expired snapshot: ', m_snapshot.SnapshotIdentifier) }
        });
    })
}

function f_delete_expired_snapshots(m_cluster) {
    var m_expire_time = m_moment().subtract(m_cluster.keep_days, 'days').toISOString()
    var m_params = { ClusterIdentifier: m_cluster.name, EndTime: m_expire_time, SnapshotType: 'manual' };    // config to find expired snapshots
    m_redshift.describeClusterSnapshots(
        m_params,
        function(m_err, m_snapshots) {
            if (m_err) m_winston.info(m_err, m_err.stack);
            else f_delete_snapshots(m_snapshots)
        }
    );
}

function f_create_snapshot(m_cluster) {
    var m_params = { ClusterIdentifier: m_cluster.name, SnapshotIdentifier: m_cluster.name + '-' + m_moment().format("YYYY-MM-DD-HH") };
    m_redshift.createClusterSnapshot(m_params, function(m_err, m_data) {
        if (m_err) m_winston.info(m_err, m_err.stack);
        else { m_winston.info(m_data.Snapshot.SnapshotIdentifier); }
    });
}

function f_create_daily_snapshot(m_cluster) {
    // find snapshots less than 1 day old, and if none exist, create new, daily snapshot
    m_creation_date = m_moment().subtract(1, 'days').toISOString()
    var m_params = { ClusterIdentifier: m_cluster.name, StartTime: m_creation_date, SnapshotType: 'manual' };
    m_redshift.describeClusterSnapshots(
        m_params,
        function(m_err, m_snapshots) {
            if (m_err) m_winston.info(m_err, m_err.stack);
            else {
                // no daily backup, so make one
                if ( m_snapshots.Snapshots.length == 0 ) {
                    m_winston.info('No daily backup')
                    f_create_snapshot(m_cluster)
                // daily backup exists, so list
                } else {
                    m_winston.info('Found daily backup')
                    _.each(m_snapshots.Snapshots, function (m_snapshot) {
                        m_winston.info('id: ' + m_snapshot.SnapshotIdentifier + ', created: ' + m_moment(m_snapshot.SnapshotCreateTime).format('YYYY-MM-DD HH:mm'))
                    })
                }
            }
        }
    );
}


/* find and delete expired snapshots */

_.each(
    m_redshift_clusters,
    function (m_cluster) {
        f_delete_expired_snapshots(m_cluster)
        f_create_daily_snapshot(m_cluster)
    }
)
