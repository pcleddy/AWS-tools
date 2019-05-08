#!/usr/bin/env ruby
require 'aws-sdk'
require 'inifile'
require 'logger'
require 'micro-optparse'
require 'pp'

# LOGGER
logger = Logger.new('/tmp/sqs_check.log')
logger.debug 'START'

# INPUTS: queue name, thresholds: warning/critical
options = Parser.new do |p|
  p.option :queue, "queue name", :default => 'myqueue' 
  p.option :warning, "warning threshold", :default => 50
  p.option :critical, "critical threshold", :default => 100
end.process!

logger.debug options

# AWS CREDS
aws_profile = 'slice-prod'
#my_creds_file = '/var/spool/nagios/.aws/credentials'
creds_file = '/Users/pleddy/.aws/credentials'
region = 'us-east-1'

ini = IniFile.load(creds_file)
Aws.config[:credentials] = Aws::Credentials.new(ini[aws_profile]['aws_access_key_id'], ini[aws_profile]['aws_secret_access_key'])

# SQS calls
begin
  sqs = Aws::SQS::Client.new(region: region )
  resp = sqs.get_queue_url({queue_name: options[:queue] })
  logger.debug resp.queue_url
  resp = sqs.get_queue_attributes({queue_url: resp.queue_url, attribute_names: ["ApproximateNumberOfMessages"], })
#  logger.debug resp.attributes['ApproximateNumberOfMessages']
rescue Aws::SQS::Errors::ServiceError
  puts "AWS SQS call(s) FAILED"
  exit(4)
end

numessages = resp.attributes['ApproximateNumberOfMessages'].to_i
if ( numessages > options[:critical].to_i ) 
  puts 'CRITICAL - messages very high: ' + numessages.to_s
  exit(1)
elsif ( numessages > options[:warning].to_i ) 
  puts 'WARN - messages above norm: ' + numessages.to_s
  exit(2)
else 
  puts 'OK - messages normal: ' + numessages.to_s
  exit(0)
end
