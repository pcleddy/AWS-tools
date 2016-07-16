#!/usr/bin/env node

var m_aws = require('aws-sdk');
var _ = require('underscore');
var m_async = require('async')
var m_jsdiff = require('diff');
var m_moment = require('moment');

var m_s3 = new m_aws.S3();


m_aws.config.update({ region: 'us-east-1', logger: process.stdout })


m_buckets = {
    vpcprod_rs: { name: 'my_s3_bucket', prefix: 'override.groovy' } 
}

for (var m_bucket_key in m_buckets) {
    var m_bucket = m_buckets[m_bucket_key]
    var m_params = {
        Bucket: m_bucket.name,
        Prefix: m_bucket.prefix,
    };
    m_s3.listObjectVersions(m_params, function(err, m_versions) {
        if (err) console.log(err, err.stack); // an error occurred
        else  {
            m_data = [];
            m_async.each(m_versions.Versions,
                function(m_version, m_callback) {
                    m_s3.getObject({Bucket: m_bucket.name, Key: m_bucket.prefix, VersionId: m_version.VersionId }, 
                        function(err, data) {
                            if (err) {
                                console.log('Does not exist:', m_version.VersionId);  
                                m_callback(null);
                                return
                            } else {
                                m_data.push(data)
                                m_callback(null);
                                return
                             }
                        }
                    );
                },
                function(err) {
                    if( err ) {
                          console.log('FAIL');
                    } else {
                        m_data.sort(function (left, right) {
                            return m_moment(new Date(left.LastModified)).diff(m_moment(new Date(right.LastModified)))
                        });
                        var m_last_piece = m_data[0];
                        m_data.forEach(
                            function(m_piece) {
                                var m_str_new = m_piece.Body.toString('utf8')
                                var m_str_old = m_last_piece.Body.toString('utf8')
                                console.log('PIECE');
                                var m_diff = m_jsdiff.createTwoFilesPatch(m_last_piece.LastModified, m_piece.LastModified, m_str_old, m_str_new, '', '')
                                console.log(m_diff);
                                m_last_piece = m_piece;
                            }
                        )
                    }
                }
            )
        }
    })
}

