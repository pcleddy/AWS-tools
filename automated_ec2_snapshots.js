#!/usr/bin/env node

var aws = require('aws-sdk');
var _ = require('underscore');
var moment = require('moment');
var winston = require('winston');

winston.remove(winston.transports.Console);
winston.add(winston.transports.File, { filename: '/var/tmp/automated_ami_snapshots.log' });
aws.config.update({
    region: 'us-east-1',
    //logger: process.stdout
})
var now = moment().format("YYYY-MM-DD-HH");

winston.info('START')

var ec2 = new aws.EC2();
var instances = [
    {
        name: 'slice-dwh-poc-admin-002',
        id: 'i-6a969cf2',
        frequency: 'daily',
        keep_days: '14'
    }
]
//winston.info (instances)

function f_delete_ami_snapshot(image_id) {
    // delete image
    var params = { ImageId: image_id, DryRun: false };
    ec2.deregisterImage(
        params,
        function(err, data) {
            if (err) winston.info(err, err.stack);
            else { winston.info(data); }
        }
    );
}

function f_create_ami_snapshot(id, name) {
    var params = { InstanceId: id, Name: name + '_' + now, DryRun: false, NoReboot: true };
    ec2.createImage(
        params,
        function(err, data) {
            if (err) {
                winston.info(err, err.stack);
            }
            else { winston.info(data); }
        }
    )
}

_.each(
    instances,
    function (inst) {

        var params = {
            DryRun: false,
            Filters: [ {Name: 'name', Values: [ inst.name + '_*' ] } ]
        };
        daily_done = false
        ec2.describeImages(
            params,
            function(err, data) {
                if (err) winston.info(err, err.stack);
                else {
                    _.each(
                        data.Images,
                        function (image) {
                            if ( moment(image.CreationDate).isAfter(moment().subtract(1, 'days')) ) {
                                daily_done = true
                                winston.info('Found daily backup: ', moment(image.CreationDate).format('YYYY-MM-DD HH:mm'))
                            }
                            var expired = moment(image.CreationDate).isBefore(moment().subtract(inst.keep_days, 'days'))
                            if ( expired ) {
                                // delete image
                                f_delete_ami_snapshot(image.ImageId)
                            }
                        }
                    )
                    //winston.info(images)
                }
                // do backup
                if ( daily_done == false) {
                    f_create_ami_snapshot(inst.id, inst.name)
                }
            }
        );

    }
)

