const config = require('./config');

const AWS = require('aws-sdk');
const AwsService = require('./classes/aws_classes').AwsService

const debug = false

const accts = config.accts;
const regions = config.regions;

for (let region of regions) {

  for (let acct of accts) {

    let attrs = {'aws_acct_id': acct.id, 'profile': acct.name, 'region': region};

    attrs.service = 'ec2';
    ec2_inventory = new AwsService(attrs);

    attrs.service = 'rds';
    rds_inventory = new AwsService(attrs);

    attrs.service = 'lambda';
    rds_inventory = new AwsService(attrs);

    attrs.service = 'dynamodb';
    dynamodb_inventory = new AwsService(attrs);

    attrs.service = 'ecs';
    ecs_inventory = new AwsService(attrs);

    attrs.service = 'elasticache';
    elasticache_inventory = new AwsService(attrs);

  }
}
