#!/usr/local/rvm/gems/ruby-2.1.5/wrappers/ruby

require 'cgi'
require 'aws-sdk'
require 'inifile'
require 'pp'
require 'logger'

Aws.use_bundled_cert!

def fetch_info(m_profile, m_region, m_vpc_id, m_live)

  #return
  m_creds_file = '/opt/operations/cred/credentials_ops_readonly_robot'

  m_ini = IniFile.load(m_creds_file)
  Aws.config[:credentials] = Aws::Credentials.new(m_ini[m_profile]['aws_access_key_id'], m_ini[m_profile]['aws_secret_access_key'])

  # get security groups ingress and egress

  m_names = {}
  m_entities = Hash.new { |h, k| h[k] = Hash.new(&h.default_proc) }  # ruby freakshow to allow hashes to generate multiple levels of keys that don't exist prior to trying to set them

  begin
    my_ec2_client = Aws::EC2::Client.new(region: m_region, profile: m_profile)
    m_storage_filename = '/tmp/resp_sgs_encoded_' + m_profile + '.txt'
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
  return m_entities
  #exit
end

def make_lit(m_entity)
  #=begin
  m_out = ''
  m_entities_h = m_entity
  m_entities_h.keys.each do |m_type|
    m_out += '<table border=0><tr><td colspan=4>'
    m_out += m_type
    m_type_h = m_entities_h[m_type]
    m_type_h.keys.each do |m_src_key|
      m_out += '<tr><td>&nbsp;<td colspan=3 bgcolor="#bbb">'
      m_out += m_src_key[0..80]
      m_src_h = m_type_h[m_src_key]
      m_src_h.keys.each do |m_target_key|
        m_out += '<tr><td>&nbsp;<td>&nbsp;<td colspan=2 bgcolor="#eee">'
        m_out += m_target_key[0..80]
  #      pp m_src_h[m_target_key]
        m_src_h[m_target_key].keys.each do |m_src_key|
          m_src_h[m_target_key][m_src_key]['port'].each do |m_port|
            m_out += '<tr><td>&nbsp;<td>&nbsp;<td>&nbsp;<td>'
            m_out += m_src_key
            m_out += ':'
            m_out += m_port.to_s
  #          puts
          end
        end
      end
    end
    m_out += '</table>'
  end
  #=end
  return m_out
end


#### MAIN

#### logging

m_logger = Logger.new('/tmp/sg_access.log')
m_logger.debug 'START'


# INIT
m_config_vpcs = {
  "vpc-cc01bda9" => {name: 'prod-us-east',region: 'us-east-1', profile: 'slice-prod', },
  "vpc-8748cfe2" => {name: 'prod-jp1', region: 'ap-northeast-1', profile: 'slice-jp', },
}
m_cgi = CGI.new("html4")
m_live = false


if ( m_cgi.params.has_key?('vpc_id') )
  m_vpc_id = m_cgi['vpc_id']
  if ( m_cgi['cached'] == 'false' )
    m_live = true
  end
  m_logger.debug m_live.to_s
  m_logger.debug m_vpc_id
end

m_content =
  m_cgi.form{
    m_cgi.hr +
    m_cgi.popup_menu("vpc_id", ["vpc-cc01bda9", "US prod", true], ["vpc-8748cfe2", "JP prod"]) +
    m_cgi.popup_menu("cached", ["true", "Cached", true], ["false", "Live"]) +
    m_cgi.br +
    m_cgi.submit
  }

m_out_ent = ''
if ( m_vpc_id )
  m_entities = fetch_info(m_config_vpcs[m_vpc_id][:profile], m_config_vpcs[m_vpc_id][:region], m_vpc_id, m_live)
  m_out_ent = make_lit(m_entities['outgoing'])
end

m_cgi.out{
   m_cgi.html{
      m_cgi.head{ "\n" + m_cgi.title{"Access"} } +
      m_cgi.body{
        m_content +
        "\n" +
        "<p>" +
        m_out_ent
      }
   }
}

exit
