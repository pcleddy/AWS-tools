#!/usr/bin/env node

var aws = require('aws-sdk');
var _ = require('underscore');
var moment = require('moment');
var winston = require('winston');

winston.remove(winston.transports.Console);
winston.add(winston.transports.File, { filename: '/var/tmp/automated_redshift_snapshots.log' });

aws.config.update({
    region: 'us-east-1',
    //logger: process.stdout
})
var now = moment().format("YYYY-MM-DD-HH");

winston.info('START')

var redshift = new aws.Redshift();
var redshift_clusters = [
    {
        name: 'slice-dwh-poc',
        frequency: 'daily',
        keep_days: '14'
    }
]

function delete_snapshots(snapshots) {
    _.each(snapshots.Snapshots, function (snapshot) {
        var params = { SnapshotIdentifier: snapshot.SnapshotIdentifier, SnapshotClusterIdentifier: snapshot.ClusterIdentifier };
        redshift.deleteClusterSnapshot(params, function(err, data) {
            if (err) winston.info(err, err.stack);
            else { winston.info('Deleting expired snapshot: ', snapshot.SnapshotIdentifier) }
        });
    })
}

function delete_expired_snapshots(cluster) {
    var expire_time = moment().subtract(cluster.keep_days, 'days').toISOString()
    var params = { ClusterIdentifier: cluster.name, EndTime: expire_time, SnapshotType: 'manual' };    // config to find expired snapshots
    redshift.describeClusterSnapshots(
        params,
        function(err, snapshots) {
            if (err) winston.info(err, err.stack);
            else delete_snapshots(snapshots)
        }
    );
}

function create_snapshot(cluster) {
    var params = { ClusterIdentifier: cluster.name, SnapshotIdentifier: cluster.name + '-' + moment().format("YYYY-MM-DD-HH") };
    redshift.createClusterSnapshot(params, function(err, data) {
        if (err) winston.info(err, err.stack);
        else { winston.info(data.Snapshot.SnapshotIdentifier); }
    });
}

function create_daily_snapshot(cluster) {
    // find snapshots less than 1 day old, and if none exist, create new, daily snapshot
    creation_date = moment().subtract(1, 'days').toISOString()
    var params = { ClusterIdentifier: cluster.name, StartTime: creation_date, SnapshotType: 'manual' };
    redshift.describeClusterSnapshots(
        params,
        function(err, snapshots) {
            if (err) winston.info(err, err.stack);
            else {
                // no daily backup, so make one
                if ( snapshots.Snapshots.length == 0 ) {
                    winston.info('No daily backup')
                    create_snapshot(cluster)
                // daily backup exists, so list
                } else {
                    winston.info('Found daily backup')
                    _.each(snapshots.Snapshots, function (snapshot) {
                        winston.info('id: ' + snapshot.SnapshotIdentifier + ', created: ' + moment(snapshot.SnapshotCreateTime).format('YYYY-MM-DD HH:mm'))
                    })
                }
            }
        }
    );
}


/* find and delete expired snapshots */

_.each(
    redshift_clusters,
    function (cluster) {
        delete_expired_snapshots(cluster)
        create_daily_snapshot(cluster)
    }
)
