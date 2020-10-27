const config = require('../config');
const AWS = require('aws-sdk');

class AwsService {
  constructor(attrs) {
    this.debug = true;
    this.show_ids = true;
    this.service = attrs.service;
    this.profile = attrs.profile;
    this.region = {};
    this.region.name = attrs.region.name;
    this.region.type = attrs.region.type;
    this.aws_acct_id = attrs.aws_acct_id;
    this.inventory = [];
    this.set_client();
    this.set_service_config();
  }

  set_client() {
    AWS.config.credentials = new AWS.SharedIniFileCredentials({profile: this.profile, filename: './aws_creds'});
    let service_op = this.service.toUpperCase()  // covers most cases
    if ( config.service_map[this.service] ) { service_op = config.service_map[this.service] }
    this.client = new AWS[service_op]({profile: this.profile, region: this.region.name});
  }

  async call_api(client, call, args, fetch) {
    const resp = await client[call](args).promise()
    const data = await fetch(resp);
    return data;
  }

  async get_resources() {
    for (let resource_type of this.resource_types) {
      await this.call_api(this.client, resource_type.api_method, resource_type.args, resource_type.fetch)
      .then(
        data => {
          for (let item of data) {
            if ( resource_type.default && item[resource_type.default] == 'default' ) {
              continue;
            }
            if (resource_type.id_field) {
              item.id = item[resource_type.id_field];
            } else {
              item = { 'id': item }
            }
            item.index = resource_type.index + '-' + this.region.type;
            item.LastSeenInAWS = new Date().toISOString();
            item.AwsAcctId = this.aws_acct_id;
            item.AwsProfile = this.profile;
            item.AwsRegion = this.region.name;
            item.AwsRegionType = this.region.type;
            item.AwsService = this.service;
            item.AwsResourceType = resource_type.type;
            this.inventory.push(item);
          }
        }
      )
    }
    return this.inventory;
  }

  set_service_config() {
    switch (this.service) {
      case 'ec2':
        this.resource_types = [
          {
            'type': 'instance',
            'api_method': 'describeInstances',
            'id_field': 'InstanceId',
            'index': 'aws-ec2-instance',
            'args': {},
            fetch(data) {
              let instances = []
              for (let reservation of data.Reservations) {
                for (let instance of reservation.Instances) {
                  instances.push(instance)
                }
              }
              return instances
            }
          },
          {
            'type': 'gateway',
            'api_method': 'describeInternetGateways',
            'id_field': 'InternetGatewayId',
            'index': 'aws-ec2-gateway',
            'args': {},
            fetch(data) { return data.InternetGateways }
          },
          {
            'type': 'image',
            'api_method': 'describeImages',
            'id_field': 'ImageId',
            'index': 'aws-ec2-image',
            'args': {'Owners': ['self'] },
            fetch(data) { return data.Images }
          },
          {
            'type': 'volume',
            'api_method': 'describeVolumes',
            'id_field': 'VolumeId',
            'index': 'aws-ec2-volume',
            'args': {},
            fetch(data) { return data.Volumes }
          },
          {
            'type': 'vpc',
            'api_method': 'describeVpcs',
            'id_field': 'VpcId',
            'index': 'aws-ec2-vpc',
            'args': {},
            fetch(data) { return data.Vpcs }
          },
          {
            'type': 'eni',
            'api_method': 'describeNetworkInterfaces',
            'id_field': 'NetworkInterfaceId',
            'index': 'aws-ec2-eni',
            'args': {},
            fetch(data) { return data.NetworkInterfaces }
          },
          {
            'type': 'ipaddr',
            'api_method': 'describeAddresses',
            'id_field': 'PublicIp',
            'index': 'aws-ec2-ipaddr',
            'args': {},
            fetch(data) { return data.Addresses }
          },
          {
            'type': 'nat-gateway',
            'api_method': 'describeNatGateways',
            'id_field': 'NatGatewayId',
            'index': 'aws-ec2-natgateway',
            'args': {},
            fetch(data) { return data.NatGateways }
          },
        ];
        break;
      case 'rds':
        this.resource_types = [
          {
            'type': 'instance',
            'api_method': 'describeDBInstances',
            'id_field': 'DBInstanceIdentifier',
            'index': 'aws-rds-db-instance',
            'args': {},
            fetch(data) { return data.DBInstances }
          }
        ]
        break;
      case 'lambda':
        this.resource_types = [
          {
            'type': 'function',
            'api_method': 'listFunctions',
            'id_field': 'FunctionArn',
            'index': 'aws-lambda-function',
            'args': {},
            fetch(data) { return data.Functions }
          }
        ]
        break;
      case 'dynamodb':
        this.resource_types = [
          {
            'type': 'table',
            'api_method': 'listTables',
            'id_field': undefined,  // array of table names is returned, not array of table objects
            'index': 'aws-dynamodb-table',
            'args': {},
            fetch(data) { return data.TableNames }
          }
        ]
        break;
      case 'ecs':
        this.resource_types = [
          {
            'type': 'cluster',
            'api_method': 'describeClusters',
            'id_field': 'clusterArn',
            'index': 'aws-ecs-cluster',
            'args': {},
            fetch(data) { return data.clusters },
            'default': 'clusterName'
          },
        ]
        break;
      case 'elasticache':
        this.resource_types = [
          {
            'type': 'cluster',
            'api_method': 'describeCacheClusters',
            'id_field': 'CacheClusterId',
            'index': 'aws-elasticache-cluster',
            'args': {},
            fetch(data) { return data.CacheClusters },
          },
        ]
        break;
      case 'sns':
        this.resource_types = [
          {
            'type': 'subscriptions',
            'api_method': 'listSubscriptions',
            'id_field': 'SubscriptionArn',
            'index': 'aws-sns-subscriptions',
            'args': {},
            fetch(data) { return data.Subscriptions },
          },
        ]
        break;
      case 'redshift':
        this.resource_types = [
          {
            'type': 'cluster',
            'api_method': 'describeClusters',
            'id_field': 'ClusterIdentifier',
            'index': 'aws-redshift-cluster',
            'args': {},
            fetch(data) { return data.Clusters },
          },
        ]
        break;
      case 's3':
        this.resource_types = [
          {
            'type': 'bucket',
            'api_method': 'listBuckets',
            'id_field': 'Name',
            'index': 'aws-s3-bucket',
            'args': {},
            fetch(data) { return data.Buckets },
          },
        ]
        break;
      case 'cloudfront':
        this.resource_types = [
          {
            'type': 'item',
            'api_method': 'listDistributions',
            'id_field': 'Id',
            'index': 'aws-cloudfront-item',
            'args': {},
            fetch(data) { return data.DistributionList.Items },
          },
        ]
        break;

    }
  }
}

module.exports = { AwsService:AwsService }
