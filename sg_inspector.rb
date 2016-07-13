#!/usr/bin/env ruby -W0

require 'aws-sdk'
require 'inifile'
require 'logger'
require 'pp'

# INIT
#m_instance_id = 'i-1f84979e' # prod
m_instance_id = 'i-d8614d7d' # new JP

m_config = [ 
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
m_instance = Hash.new { |h, k| h[k] = Hash.new(&h.default_proc) } 
m_config.each do |m_aws_location|
  m_aws_location[:instances ].each do |m_instance_tmp|
    if ( m_instance_id == m_instance_tmp[:id] )
      m_instance = m_instance_tmp
      m_instance[:location] = m_aws_location
      m_instance[:location].delete(:instances)
    end
  end
end

#pp m_instance
#exit

# AWS CREDS
m_creds_file = '/Users/pleddy/.aws/credentials'
m_region = m_instance[:location][:region]
m_aws_profile = m_instance[:location][:profile]
m_vpc_id = m_instance[:location][:vpc_id]

m_ini = IniFile.load(m_creds_file)
Aws.config[:credentials] = Aws::Credentials.new(m_ini[m_aws_profile]['aws_access_key_id'], m_ini[m_aws_profile]['aws_secret_access_key'])

# get instance security group and networks

begin
  my_ec2_client = Aws::EC2::Client.new(region: m_region, profile: m_aws_profile)
  m_live = false
  m_storage_filename = '/tmp/resp_instance_encoded.txt'
  if ( m_live == true )
    m_resp = my_ec2_client.describe_instances({dry_run: false, filters: [{name: "instance-id", values: [m_instance_id] }, ] })
    m_data = Marshal.dump(m_resp.data)
    File.write(m_storage_filename, m_data)
  else
    m_resp_restore = File.read(m_storage_filename)
    m_resp = Marshal.load(m_resp_restore)
  end
  m_inst_sgs = []
  m_inst_groups_read = m_resp.reservations[0].instances[0].security_groups
  m_inst_groups_read.each do |m_group|
    #pp m_group
    m_inst_sgs << m_group['group_name']
  end
  m_inst_ip = m_resp.reservations[0].instances[0].private_ip_address
rescue Aws::EC2::Errors::ServiceError => error
  puts "Error calling EC2 API: #{error.message}"
end

m_inst_networks = [ m_inst_ip.concat('/32'), m_inst_ip.match(/\d+\.\d+\.\d+\./)[0].concat('0/22'), m_inst_ip.match(/\d+\.\d+\./)[0].concat('0.0/16')]
#puts
#pp m_inst_networks
#pp m_inst_sgs

# get security groups ingress and egress

m_names = {}
m_entities = Hash.new { |h, k| h[k] = Hash.new(&h.default_proc) }  # ruby freakshow to allow hashes to generate multiple levels of keys that don't exist prior to trying to set them

begin
  my_ec2_client = Aws::EC2::Client.new(region: m_region, profile: m_aws_profile)
  m_live = false
  m_storage_filename = '/tmp/resp_sgs_encoded.txt'
  if ( m_live == true )
    m_resp = my_ec2_client.describe_security_groups({dry_run: false, filters: [{name: "vpc-id", values: [m_vpc_id] }, ] })
    m_data = Marshal.dump(m_resp.data)
    File.write(m_storage_filename, m_data)
  else
    m_resp_restore = File.read(m_storage_filename)
    m_resp = Marshal.load(m_resp_restore)
  end
  m_resp.security_groups.each do |m_sg|
    m_names[m_sg.group_id] = m_sg.group_name
  end
  m_resp.security_groups.each do |m_sg|
    if m_sg.respond_to?(:ip_permissions)
      m_sg.ip_permissions.each do |m_ip_perm|
        m_ip_perm.user_id_group_pairs.each do |m_group|
          m_entities['outgoing']['sgs'][m_names[m_group.group_id]][m_names[m_sg.group_id]][m_ip_perm.ip_protocol]['port'] = [] if ! m_entities['outgoing']['sgs'][m_names[m_group.group_id]][m_names[m_sg.group_id]][m_ip_perm.ip_protocol].has_key? 'port'
          m_entities['outgoing']['sgs'][m_names[m_group.group_id]][m_names[m_sg.group_id]][m_ip_perm.ip_protocol]['port'] << m_ip_perm.to_port
        end
        m_ip_perm.ip_ranges.each do |m_range|
          m_entities['outgoing']['ips'][m_range.cidr_ip][m_names[m_sg.group_id]][m_ip_perm.ip_protocol]['port'] = [] if ! m_entities['outgoing']['ips'][m_range.cidr_ip][m_names[m_sg.group_id]][m_ip_perm.ip_protocol].has_key? 'port'
          m_entities['outgoing']['ips'][m_range.cidr_ip][m_names[m_sg.group_id]][m_ip_perm.ip_protocol]['port'] << m_ip_perm.to_port
        end
      end
      m_sg.ip_permissions.each do |m_ip_perm|
        m_ip_perm.user_id_group_pairs.each do |m_group|
          m_entities['incoming']['sgs'][m_names[m_sg.group_id]][m_names[m_group.group_id]][m_ip_perm.ip_protocol]['port'] = [] if ! m_entities['incoming']['sgs'][m_names[m_sg.group_id]][m_names[m_group.group_id]][m_ip_perm.ip_protocol].has_key? 'port'
          m_entities['incoming']['sgs'][m_names[m_sg.group_id]][m_names[m_group.group_id]][m_ip_perm.ip_protocol]['port'] << m_ip_perm.to_port
        end
        m_ip_perm.ip_ranges.each do |m_range|
          m_entities['incoming']['ips'][m_names[m_sg.group_id]][m_range.cidr_ip][m_ip_perm.ip_protocol]['port'] = [] if ! m_entities['incoming']['ips'][m_names[m_sg.group_id]][m_range.cidr_ip][m_ip_perm.ip_protocol].has_key? 'port'
          m_entities['incoming']['ips'][m_names[m_sg.group_id]][m_range.cidr_ip][m_ip_perm.ip_protocol]['port'] << m_ip_perm.to_port
        end
      end
    end
  end
rescue Aws::EC2::Errors::ServiceError => error
  puts "Error calling EC2 API: #{error.message}"
end

#pp m_entities
#exit

m_entities_h = m_entities['outgoing']
m_entities_h.keys.each do |m_type|
  p m_type
  m_type_h = m_entities_h[m_type]
  m_type_h.keys.each do |m_src_key|
    print "\t"
    p m_src_key
    m_src_h = m_type_h[m_src_key]
    m_src_h.keys.each do |m_target_key|
      print "\t\t"
      p m_target_key
#      pp m_src_h[m_target_key]
      m_src_h[m_target_key].keys.each do |m_src_key|
        m_src_h[m_target_key][m_src_key]['port'].each do |m_port|
          print "\t\t\t"
          print m_src_key
          print ':'
          print m_port
          puts
        end
      end
    end
  end
end

exit

