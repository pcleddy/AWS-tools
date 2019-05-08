#!/usr/local/rvm/gems/ruby-2.1.5/wrappers/ruby

require 'cgi'
require 'aws-sdk'
require 'inifile'
require 'pp'
require 'logger'

Aws.use_bundled_cert!

def fetch_info(profile, region, vpc_id, live)

  #return
  creds_file = '/opt/operations/cred/credentials_ops_readonly_robot'

  ini = IniFile.load(creds_file)
  Aws.config[:credentials] = Aws::Credentials.new(ini[profile]['aws_access_key_id'], ini[profile]['aws_secret_access_key'])

  # get security groups ingress and egress

  names = {}
  entities = Hash.new { |h, k| h[k] = Hash.new(&h.default_proc) }  # ruby freakshow to allow hashes to generate multiple levels of keys that don't exist prior to trying to set them

  begin
    my_ec2_client = Aws::EC2::Client.new(region: region, profile: profile)
    storage_filename = '/tmp/resp_sgs_encoded_' + profile + '.txt'
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
  return entities
  #exit
end

def make_lit(entity)
  #=begin
  out = ''
  entities_h = entity
  entities_h.keys.each do |type|
    out += '<table border=0><tr><td colspan=4>'
    out += type
    type_h = entities_h[type]
    type_h.keys.each do |src_key|
      out += '<tr><td>&nbsp;<td colspan=3 bgcolor="#bbb">'
      out += src_key[0..80]
      src_h = type_h[src_key]
      src_h.keys.each do |target_key|
        out += '<tr><td>&nbsp;<td>&nbsp;<td colspan=2 bgcolor="#eee">'
        out += target_key[0..80]
  #      pp src_h[target_key]
        src_h[target_key].keys.each do |src_key|
          src_h[target_key][src_key]['port'].each do |port|
            out += '<tr><td>&nbsp;<td>&nbsp;<td>&nbsp;<td>'
            out += src_key
            out += ':'
            out += port.to_s
  #          puts
          end
        end
      end
    end
    out += '</table>'
  end
  #=end
  return out
end


#### MAIN

#### logging

logger = Logger.new('/tmp/sg_access.log')
logger.debug 'START'


# INIT
config_vpcs = {
  "vpc-cc01bda9" => {name: 'prod-us-east',region: 'us-east-1', profile: 'slice-prod', },
  "vpc-8748cfe2" => {name: 'prod-jp1', region: 'ap-northeast-1', profile: 'slice-jp', },
}
cgi = CGI.new("html4")
live = false


if ( cgi.params.has_key?('vpc_id') )
  vpc_id = cgi['vpc_id']
  if ( cgi['cached'] == 'false' )
    live = true
  end
  logger.debug live.to_s
  logger.debug vpc_id
end

content =
  cgi.form{
    cgi.hr +
    cgi.popup_menu("vpc_id", ["vpc-cc01bda9", "US prod", true], ["vpc-8748cfe2", "JP prod"]) +
    cgi.popup_menu("cached", ["true", "Cached", true], ["false", "Live"]) +
    cgi.br +
    cgi.submit
  }

out_ent = ''
if ( vpc_id )
  entities = fetch_info(config_vpcs[vpc_id][:profile], config_vpcs[vpc_id][:region], vpc_id, live)
  out_ent = make_lit(entities['outgoing'])
end

cgi.out{
   cgi.html{
      cgi.head{ "\n" + cgi.title{"Access"} } +
      cgi.body{
        content +
        "\n" +
        "<p>" +
        out_ent
      }
   }
}

exit
