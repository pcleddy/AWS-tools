#!/usr/bin/env ruby -W0

require 'aws-sdk'
require 'inifile'
require 'logger'
require 'pp'

# INIT
#instance_id = 'i-1f84979e' # prod
instance_id = 'i-d8614d7d' # new JP

config = [ 
  {name: 'prod-us-east',region: 'us-east-1', profile: 'slice-prod', vpc_id: 'vpc-8748cfe2',
    instances: [
      {id: 'i-1f84979e', name: 'VPCPROD mailproc DB1', ip: '172.30.144.44', },
      {id: 'i-9d40632e', name: 'zk-9d40632e.prod.slicetest.com', ip: '172.30.73.136', }
    ] },
  {name: 'prod-jp1', region: 'ap-northeast-1', profile: 'slice-jp', vpc_id: 'vpc-8748cfe2',
    instances: [
      {id: 'i-d8614d7d', name: 'ACM #3', ip: '172.27.9.250', },
    ] },
  {name: 'prod-jp', region: 'ap-northeast-1', profile: 'slice-jp', vpc_id: 'vpc-701d5818',
    instances: [
    ] },
]

# find instance and its location
instance = Hash.new { |h, k| h[k] = Hash.new(&h.default_proc) } 
config.each do |aws_location|
  aws_location[:instances ].each do |instance_tmp|
    if ( instance_id == instance_tmp[:id] )
      instance = instance_tmp
      instance[:location] = aws_location
      instance[:location].delete(:instances)
    end
  end
end

#pp instance
#exit

# AWS CREDS
creds_file = '/Users/pleddy/.aws/credentials'
region = instance[:location][:region]
aws_profile = instance[:location][:profile]
vpc_id = instance[:location][:vpc_id]

ini = IniFile.load(creds_file)
Aws.config[:credentials] = Aws::Credentials.new(ini[aws_profile]['aws_access_key_id'], ini[aws_profile]['aws_secret_access_key'])

# get instance security group and networks

begin
  my_ec2_client = Aws::EC2::Client.new(region: region, profile: aws_profile)
  live = false
  storage_filename = '/tmp/resp_instance_encoded.txt'
  if ( live == true )
    resp = my_ec2_client.describe_instances({dry_run: false, filters: [{name: "instance-id", values: [instance_id] }, ] })
    data = Marshal.dump(resp.data)
    File.write(storage_filename, data)
  else
    resp_restore = File.read(storage_filename)
    resp = Marshal.load(resp_restore)
  end
  inst_sgs = []
  inst_groups_read = resp.reservations[0].instances[0].security_groups
  inst_groups_read.each do |group|
    #pp group
    inst_sgs << group['group_name']
  end
  inst_ip = resp.reservations[0].instances[0].private_ip_address
rescue Aws::EC2::Errors::ServiceError => error
  puts "Error calling EC2 API: #{error.message}"
end

inst_networks = [ inst_ip.concat('/32'), inst_ip.match(/\d+\.\d+\.\d+\./)[0].concat('0/22'), inst_ip.match(/\d+\.\d+\./)[0].concat('0.0/16')]
#puts
#pp inst_networks
#pp inst_sgs

# get security groups ingress and egress

names = {}
entities = Hash.new { |h, k| h[k] = Hash.new(&h.default_proc) }  # ruby freakshow to allow hashes to generate multiple levels of keys that don't exist prior to trying to set them

begin
  my_ec2_client = Aws::EC2::Client.new(region: region, profile: aws_profile)
  live = false
  storage_filename = '/tmp/resp_sgs_encoded.txt'
  if ( live == true )
    resp = my_ec2_client.describe_security_groups({dry_run: false, filters: [{name: "vpc-id", values: [vpc_id] }, ] })
    data = Marshal.dump(resp.data)
    File.write(storage_filename, data)
  else
    resp_restore = File.read(storage_filename)
    resp = Marshal.load(resp_restore)
  end
  resp.security_groups.each do |sg|
    names[sg.group_id] = sg.group_name
  end
  resp.security_groups.each do |sg|
    if sg.respond_to?(:ip_permissions)
      sg.ip_permissions.each do |ip_perm|
        ip_perm.user_id_group_pairs.each do |group|
          entities['outgoing']['sgs'][names[group.group_id]][names[sg.group_id]][ip_perm.ip_protocol]['port'] = [] if ! entities['outgoing']['sgs'][names[group.group_id]][names[sg.group_id]][ip_perm.ip_protocol].has_key? 'port'
          entities['outgoing']['sgs'][names[group.group_id]][names[sg.group_id]][ip_perm.ip_protocol]['port'] << ip_perm.to_port
        end
        ip_perm.ip_ranges.each do |range|
          entities['outgoing']['ips'][range.cidr_ip][names[sg.group_id]][ip_perm.ip_protocol]['port'] = [] if ! entities['outgoing']['ips'][range.cidr_ip][names[sg.group_id]][ip_perm.ip_protocol].has_key? 'port'
          entities['outgoing']['ips'][range.cidr_ip][names[sg.group_id]][ip_perm.ip_protocol]['port'] << ip_perm.to_port
        end
      end
      sg.ip_permissions.each do |ip_perm|
        ip_perm.user_id_group_pairs.each do |group|
          entities['incoming']['sgs'][names[sg.group_id]][names[group.group_id]][ip_perm.ip_protocol]['port'] = [] if ! entities['incoming']['sgs'][names[sg.group_id]][names[group.group_id]][ip_perm.ip_protocol].has_key? 'port'
          entities['incoming']['sgs'][names[sg.group_id]][names[group.group_id]][ip_perm.ip_protocol]['port'] << ip_perm.to_port
        end
        ip_perm.ip_ranges.each do |range|
          entities['incoming']['ips'][names[sg.group_id]][range.cidr_ip][ip_perm.ip_protocol]['port'] = [] if ! entities['incoming']['ips'][names[sg.group_id]][range.cidr_ip][ip_perm.ip_protocol].has_key? 'port'
          entities['incoming']['ips'][names[sg.group_id]][range.cidr_ip][ip_perm.ip_protocol]['port'] << ip_perm.to_port
        end
      end
    end
  end
rescue Aws::EC2::Errors::ServiceError => error
  puts "Error calling EC2 API: #{error.message}"
end

#pp entities
#exit

entities_h = entities['outgoing']
entities_h.keys.each do |type|
  p type
  type_h = entities_h[type]
  type_h.keys.each do |src_key|
    print "\t"
    p src_key
    src_h = type_h[src_key]
    src_h.keys.each do |target_key|
      print "\t\t"
      p target_key
#      pp src_h[target_key]
      src_h[target_key].keys.each do |src_key|
        src_h[target_key][src_key]['port'].each do |port|
          print "\t\t\t"
          print src_key
          print ':'
          print port
          puts
        end
      end
    end
  end
end

exit

