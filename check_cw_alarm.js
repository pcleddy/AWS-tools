#!/usr/bin/env node

'use strict';

var AWS = require('aws-sdk');

AWS.config.update({
    region: 'us-east-1',
    //logger: process.stdout
})

var cloudwatch = new AWS.CloudWatch();
var params = {AlarmNames: ['vpcprod-elb_500s_high', ], };
cloudwatch.describeAlarms(params, function(err, data) {
  if (err) console.log(err, err.stack); // an error occurred
  else {
    var state = data.MetricAlarms[0].StateValue;
    //state = 'INSUFFICIENT_DATA';
    if ( state == 'ALARM' ) {
        console.log("ALARM TRIGGERED");
        process.exit(2);
    } else if ( state == 'INSUFFICIENT_DATA' ) {
        console.log("INSUFFICIENT DATA");
        process.exit(3);
    } else {
        console.log("OK");
        process.exit(0);
    }
  }  
});
