#!/usr/bin/env node

var m_aws = require('aws-sdk');
var _ = require('underscore');
var m_moment = require('moment');
var m_winston = require('winston');

m_winston.remove(m_winston.transports.Console);
m_winston.add(m_winston.transports.File, { filename: '/var/tmp/automated_ami_snapshots.log' });
m_aws.config.update({
    region: 'us-east-1',
    //logger: process.stdout
})
var m_now = m_moment().format("YYYY-MM-DD-HH");

m_winston.info('START')

var m_ec2 = new m_aws.EC2();
var m_instances = [
    {
        name: 'slice-dwh-poc-admin-002',
        id: 'i-6a969cf2',
        frequency: 'daily',
        keep_days: '14'
    }
]
//m_winston.info (m_instances)

function f_delete_ami_snapshot(m_image_id) {
    // delete image
    var m_params = { ImageId: m_image_id, DryRun: false };
    m_ec2.deregisterImage(
        m_params,
        function(m_err, m_data) {
            if (m_err) winston.info(m_err, m_err.stack);
            else { winston.info(m_data); }
        }
    );
}

function f_create_ami_snapshot(m_id, m_name) {
    var m_params = { InstanceId: m_id, Name: m_name + '_' + m_now, DryRun: false, NoReboot: true };
    m_ec2.createImage(
        m_params,
        function(m_err, m_data) {
            if (m_err) {
                m_winston.info(m_err, m_err.stack);
            }
            else { m_winston.info(m_data); }
        }
    )
}

_.each(
    m_instances,
    function (m_inst) {

        var params = {
            DryRun: false,
            Filters: [ {Name: 'name', Values: [ m_inst.name + '_*' ] } ]
        };
        m_daily_done = false
        m_ec2.describeImages(
            params,
            function(m_err, m_data) {
                if (m_err) m_winston.info(m_err, m_err.stack);
                else {
                    _.each(
                        m_data.Images,
                        function (m_image) {
                            if ( m_moment(m_image.CreationDate).isAfter(m_moment().subtract(1, 'days')) ) {
                                m_daily_done = true
                                m_winston.info('Found daily backup: ', m_moment(m_image.CreationDate).format('YYYY-MM-DD HH:mm'))
                            }
                            var m_expired = m_moment(m_image.CreationDate).isBefore(m_moment().subtract(m_inst.keep_days, 'days'))
                            if ( m_expired ) {
                                // delete image
                                f_delete_ami_snapshot(m_image.ImageId)
                            }
                        }
                    )
                    //m_winston.info(m_images)
                }
                // do backup
                if ( m_daily_done == false) {
                    f_create_ami_snapshot(m_inst.id, m_inst.name)
                }
            }
        );

    }
)

