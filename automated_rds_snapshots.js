#!/usr/bin/env node

var m_aws = require('aws-sdk');
var _ = require('underscore');
var m_moment = require('moment');
var m_winston = require('winston');

m_winston.remove(m_winston.transports.Console);
m_winston.add(m_winston.transports.File, { filename: '/var/tmp/automated_rds_snapshots.log' });

m_aws.config.update({
    region: 'us-east-1',
    //logger: process.stdout
})
var m_now = m_moment().format("YYYY-MM-DD-HH");

m_winston.info('START')

var m_rds = new m_aws.RDS();
var m_rds_instances = [
    {
        name: 'dwh-metadata',
        frequency: 'daily',
        keep_days: '14'
    }
]

function f_delete_snapshots(m_snapshots) {
    _.each(m_snapshots, function (m_snapshot) {
        var m_params = { DBSnapshotIdentifier: m_snapshot.DBSnapshotIdentifier };
        m_rds.deleteDBSnapshot(m_params, function(m_err, m_data) {
            if (m_err) m_winston.info(m_err, m_err.stack);
            else { m_winston.info('Deleting expired snapshot: ', m_snapshot.DBSnapshotIdentifier) }
        });
    })
}

function f_delete_expired_snapshots(m_inst) {
    var m_expire_time = m_moment().subtract(m_inst.keep_days, 'minutes').toISOString()
    var m_params = { DBInstanceIdentifier: m_inst.name, SnapshotType: 'manual' };    // config to find expired snapshots
    m_rds.describeDBSnapshots(
        m_params,
        function(m_err, m_snapshots) {
            if (m_err) m_winston.info(m_err, m_err.stack);
            else {
                var m_expired = _.filter(m_snapshots.DBSnapshots, function(m_snapshot){ return m_moment(m_snapshot.SnapshotCreateTime).isBefore(m_moment().subtract(m_inst.keep_days, 'days')); });
                f_delete_snapshots(m_expired)
            }
        }
    );
}
function f_create_snapshot(m_inst) {
    var m_params = { DBInstanceIdentifier: m_inst.name, DBSnapshotIdentifier: m_inst.name + '-' + m_moment().format("YYYY-MM-DD-HH-mm") };
    m_rds.createDBSnapshot(m_params, function(m_err, m_data) {
        if (m_err) m_winston.info(m_err, m_err.stack);
        else { m_winston.info(m_data.DBSnapshot.DBSnapshotIdentifier); }
    });
}

function f_create_daily_snapshot(m_inst) {
    // find snapshots less than 1 day old, and if none exist, create new, daily snapshot
    var m_params = { DBInstanceIdentifier: m_inst.name, SnapshotType: 'manual' };
    //console.log(m_params)
    m_rds.describeDBSnapshots(
        m_params,
        function(m_err, m_snapshots) {
            if (m_err) m_winston.info(m_err, m_err.stack);
            else {
                var m_dailies = _.filter(m_snapshots.DBSnapshots, function(m_snapshot){ return m_moment(m_snapshot.SnapshotCreateTime).isAfter(m_moment().subtract(1, 'days')); });
                // no daily backup, so make one 
                if ( m_dailies == 0 ) {
                    m_winston.info('No daily backup')
                    f_create_snapshot(m_inst)
                // daily backup exists, so list
                } else {
                    m_winston.info('Found daily backup')
                    _.each(m_dailies, function (m_snapshot) {
                        m_winston.info('id: ' + m_snapshot.DBSnapshotIdentifier + ', created: ' + m_moment(m_snapshot.SnapshotCreateTime).format('YYYY-MM-DD HH:mm'))
                    })
                }
            }
        }
    );
}


/* find and delete expired snapshots */

_.each(
    m_rds_instances,
    function (m_inst) {
        f_delete_expired_snapshots(m_inst)
        f_create_daily_snapshot(m_inst)
    }
)
