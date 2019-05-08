#!/usr/bin/env node

var aws = require('aws-sdk');
var _ = require('underscore');
var async = require('async')
var jsdiff = require('diff');
var moment = require('moment');

var s3 = new aws.S3();


aws.config.update({ region: 'us-east-1', logger: process.stdout })


buckets = {
    vpcprod_rs: { name: 'my_s3_bucket', prefix: 'override.groovy' } 
}

for (var bucket_key in buckets) {
    var bucket = buckets[bucket_key]
    var params = {
        Bucket: bucket.name,
        Prefix: bucket.prefix,
    };
    s3.listObjectVersions(params, function(err, versions) {
        if (err) console.log(err, err.stack); // an error occurred
        else  {
            data = [];
            async.each(versions.Versions,
                function(version, callback) {
                    s3.getObject({Bucket: bucket.name, Key: bucket.prefix, VersionId: version.VersionId }, 
                        function(err, data) {
                            if (err) {
                                console.log('Does not exist:', version.VersionId);  
                                callback(null);
                                return
                            } else {
                                data.push(data)
                                callback(null);
                                return
                             }
                        }
                    );
                },
                function(err) {
                    if( err ) {
                          console.log('FAIL');
                    } else {
                        data.sort(function (left, right) {
                            return moment(new Date(left.LastModified)).diff(moment(new Date(right.LastModified)))
                        });
                        var last_piece = data[0];
                        data.forEach(
                            function(piece) {
                                var str_new = piece.Body.toString('utf8')
                                var str_old = last_piece.Body.toString('utf8')
                                console.log('PIECE');
                                var diff = jsdiff.createTwoFilesPatch(last_piece.LastModified, piece.LastModified, str_old, str_new, '', '')
                                console.log(diff);
                                last_piece = piece;
                            }
                        )
                    }
                }
            )
        }
    })
}

