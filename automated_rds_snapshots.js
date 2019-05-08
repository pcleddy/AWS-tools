#!/usr/bin/env node

var aws = require('aws-sdk');
var _ = require('underscore');
var moment = require('moment');
var winston = require('winston');

winston.remove(winston.transports.Console);
winston.add(winston.transports.File, { filename: '/var/tmp/automated_rds_snapshots.log' });

aws.config.update({
    region: 'us-east-1',
    //logger: process.stdout
})
var now = moment().format("YYYY-MM-DD-HH");

winston.info('START')

var rds = new aws.RDS();
var rds_instances = [
    {
        name: 'dwh-metadata',
        frequency: 'daily',
        keep_days: '14'
    }
]

function delete_snapshots(snapshots) {
    _.each(snapshots, function (snapshot) {
        var params = { DBSnapshotIdentifier: snapshot.DBSnapshotIdentifier };
        rds.deleteDBSnapshot(params, function(err, data) {
            if (err) winston.info(err, err.stack);
            else { winston.info('Deleting expired snapshot: ', snapshot.DBSnapshotIdentifier) }
        });
    })
}

function delete_expired_snapshots(inst) {
    var expire_time = moment().subtract(inst.keep_days, 'minutes').toISOString()
    var params = { DBInstanceIdentifier: inst.name, SnapshotType: 'manual' };    // config to find expired snapshots
    rds.describeDBSnapshots(
        params,
        function(err, snapshots) {
            if (err) winston.info(err, err.stack);
            else {
                var expired = _.filter(snapshots.DBSnapshots, function(snapshot){ return moment(snapshot.SnapshotCreateTime).isBefore(moment().subtract(inst.keep_days, 'days')); });
                delete_snapshots(expired)
            }
        }
    );
}
function create_snapshot(inst) {
    var params = { DBInstanceIdentifier: inst.name, DBSnapshotIdentifier: inst.name + '-' + moment().format("YYYY-MM-DD-HH-mm") };
    rds.createDBSnapshot(params, function(err, data) {
        if (err) winston.info(err, err.stack);
        else { winston.info(data.DBSnapshot.DBSnapshotIdentifier); }
    });
}

function create_daily_snapshot(inst) {
    // find snapshots less than 1 day old, and if none exist, create new, daily snapshot
    var params = { DBInstanceIdentifier: inst.name, SnapshotType: 'manual' };
    //console.log(params)
    rds.describeDBSnapshots(
        params,
        function(err, snapshots) {
            if (err) winston.info(err, err.stack);
            else {
                var dailies = _.filter(snapshots.DBSnapshots, function(snapshot){ return moment(snapshot.SnapshotCreateTime).isAfter(moment().subtract(1, 'days')); });
                // no daily backup, so make one 
                if ( dailies == 0 ) {
                    winston.info('No daily backup')
                    create_snapshot(inst)
                // daily backup exists, so list
                } else {
                    winston.info('Found daily backup')
                    _.each(dailies, function (snapshot) {
                        winston.info('id: ' + snapshot.DBSnapshotIdentifier + ', created: ' + moment(snapshot.SnapshotCreateTime).format('YYYY-MM-DD HH:mm'))
                    })
                }
            }
        }
    );
}


/* find and delete expired snapshots */

_.each(
    rds_instances,
    function (inst) {
        delete_expired_snapshots(inst)
        create_daily_snapshot(inst)
    }
)
