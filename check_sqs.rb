#!/usr/bin/env ruby
require 'aws-sdk'
require 'inifile'
require 'logger'
require 'micro-optparse'
require 'pp'

# LOGGER
m_logger = Logger.new('/tmp/sqs_check.log')
m_logger.debug 'START'

# INPUTS: queue name, thresholds: warning/critical
options = Parser.new do |p|
  p.option :queue, "queue name", :default => 'myqueue' 
  p.option :warning, "warning threshold", :default => 50
  p.option :critical, "critical threshold", :default => 100
end.process!

m_logger.debug options

# AWS CREDS
m_aws_profile = 'slice-prod'
#my_creds_file = '/var/spool/nagios/.aws/credentials'
m_creds_file = '/Users/pleddy/.aws/credentials'
m_region = 'us-east-1'

m_ini = IniFile.load(m_creds_file)
Aws.config[:credentials] = Aws::Credentials.new(m_ini[m_aws_profile]['aws_access_key_id'], m_ini[m_aws_profile]['aws_secret_access_key'])

# SQS calls
begin
  m_sqs = Aws::SQS::Client.new(region: m_region )
  resp = m_sqs.get_queue_url({queue_name: options[:queue] })
  m_logger.debug resp.queue_url
  resp = m_sqs.get_queue_attributes({queue_url: resp.queue_url, attribute_names: ["ApproximateNumberOfMessages"], })
#  m_logger.debug resp.attributes['ApproximateNumberOfMessages']
rescue Aws::SQS::Errors::ServiceError
  puts "AWS SQS call(s) FAILED"
  exit(4)
end

m_num_messages = resp.attributes['ApproximateNumberOfMessages'].to_i
if ( m_num_messages > options[:critical].to_i ) 
  puts 'CRITICAL - messages very high: ' + m_num_messages.to_s
  exit(1)
elsif ( m_num_messages > options[:warning].to_i ) 
  puts 'WARN - messages above norm: ' + m_num_messages.to_s
  exit(2)
else 
  puts 'OK - messages normal: ' + m_num_messages.to_s
  exit(0)
end
