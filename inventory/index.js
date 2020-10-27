const config = require('./config');

const AWS = require('aws-sdk');
const AwsService = require('./classes/aws_classes').AwsService
const ELKClient = require('./classes/elk_classes').ELKClient

const debug = false

const accts = config.accts;
const regions = config.regions;

aws_services = [];

for (let region of regions) {

  console.log('Processing: ', region.name)

  for (let acct of accts) {

    let attrs = {'aws_acct_id': acct.id, 'profile': acct.name, 'region': region};

    attrs.service = 'ec2';
    ec2_inventory = new AwsService(attrs);
    aws_services.push(ec2_inventory)

    attrs.service = 'rds';
    rds_inventory = new AwsService(attrs);
    aws_services.push(rds_inventory)

    attrs.service = 'dynamodb';
    dynamodb_inventory = new AwsService(attrs);
    aws_services.push(dynamodb_inventory)

    attrs.service = 'ecs';
    ecs_inventory = new AwsService(attrs);
    aws_services.push(ecs_inventory)

    attrs.service = 'elasticache';
    elasticache_inventory = new AwsService(attrs);
    aws_services.push(elasticache_inventory)

    attrs.service = 'redshift';
    redshift_inventory = new AwsService(attrs);
    aws_services.push(redshift_inventory)

    attrs.service = 'sns';
    sns_inventory = new AwsService(attrs);
    aws_services.push(sns_inventory)

    attrs.service = 's3';
    s3_inventory = new AwsService(attrs);
    aws_services.push(s3_inventory)

    attrs.service = 'lambda';
    lambda_inventory = new AwsService(attrs);
    aws_services.push(lambda_inventory)

    attrs.service = 'cloudfront';
    cloudfront_inventory = new AwsService(attrs);
    aws_services.push(cloudfront_inventory)

  }
}

console.log('Number of service objects: ', aws_services.length)

let all_items = []

Promise.all(aws_services.map( svc => svc.get_resources() ))
.then( data => {
  const elk_client = new ELKClient()
  data.map( items => { if (items.length) { elk_client.send({ json_docs: items }) } });
})

console.log('END - index')
