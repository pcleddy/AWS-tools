const config = {

  'elk': {
      'host': 'elastic.me',
      'port': '9200',
      'push_to_elk': true,
      'local': false,
  },

  'service_map': {
    'lambda': 'Lambda',
    'dynamodb': 'DynamoDB',
    'elasticache': 'ElastiCache',
  },

  'accts': [
    { 'id': '032222211111', 'name': 'me-a' },
    { 'id': '032222211112', 'name': 'me-b' },
  ],

  'regions': [
    'ap-south-1',
    'eu-west-3',
    'eu-north-1',
    'eu-west-2',
    'eu-west-1',
    'ap-northeast-2',
    'ap-northeast-1',
    'sa-east-1',
    'ca-central-1',
    'ap-southeast-1',
    'ap-southeast-2',
    'eu-central-1',
    'us-east-2',
    'us-west-1',
  ]

};

module.exports = config;
