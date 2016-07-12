#!/var/lib/nagios/.rvm/wrappers/ruby-2.3.1/ruby

require 'aws-sdk'
require 'pp'
require 'erb'


# INIT I5

m_region = 'us-east-1'
m_all_instances = []
m_live = true
m_storage_filename = '/tmp/resp_encoded'
m_config = {'out_path' => '/etc/nagios/conf.d/slice/'}

my_ec2_client = Aws::EC2::Client.new(region: m_region)

begin

  if ( m_live == true )
    my_ec2_client = Aws::EC2::Client.new(region: m_region)
    m_resp = my_ec2_client.describe_instances({dry_run: false, filters: [{name: "instance-state-name", values: ["running"], }, ], })
    m_data = Marshal.dump(m_resp.data)
    File.write(m_storage_filename, m_data)
  else 
    m_resp_restore = File.read(m_storage_filename)
    m_resp = Marshal.load(m_resp_restore)
  end

  m_resp.reservations.each do |m_reservation|
    m_reservation.instances.each do |m_inst_tmp|
      m_inst = {}
      m_inst['ip'] = m_inst_tmp.private_ip_address
      m_inst_tmp.tags.each do |m_tag|
        m_inst[m_tag.key] = m_tag.value
      end

      # get rid of a ton of aws garbage tags
      m_inst.delete_if {|key, value| key.include? ':' }

      # add cleaned up instance hash to array of all instances
      m_all_instances << m_inst
    end
  end
rescue Aws::EC2::Errors::ServiceError
  puts 'Error calling EC2 API'
end

#pp m_resp;exit

m_all_instances.each do |m_inst|
  #pp m_inst

  m_inst["Name"] = 'noname' if ( ! m_inst["Name"] )

  if (m_inst.has_key?("Environment")) 
    m_inst["environment"] = m_inst.delete("Environment").downcase
  end
  if (m_inst.has_key?("Role")) 
    m_inst["role"] = m_inst.delete("Role").downcase
  end
  if (m_inst.has_key?("role")) 
    m_inst["role"] = m_inst["role"].downcase
  end
  if (m_inst.has_key?("name")) 
    m_inst["Name"] = m_inst.delete("name").downcase
  end
  if (m_inst["Name"].match(/^VPCPROD/))
    m_inst["Name"].gsub!('VPCPROD', '')
    m_inst["Name"].gsub!(' ', '')
    m_inst["Name"].gsub!('#', '_')
    #puts m_inst["Name"]
  end


  # standardize hostnames
  m_inst["Name"].gsub!(/[()]/, '')
  m_inst["Name"].gsub!(/^\s+/, '')
  m_inst["Name"].gsub!(/\s+$/, '')
  m_inst["Name"].gsub!(' ', '_')
  m_inst["Name"].downcase!

end

#pp m_all_instances;exit

#### delete all instances from staging; they are not monitored by Nagios

m_all_instances.delete_if { |h| h['environment'] == 'staging' }
m_all_instances.delete_if { |h| h['Name'].match(/stag/i) }
m_all_instances.delete_if { |h| h['Name'].match(/noname/i) }
#m_all_instances.delete_if { |h| h['Name'].match(/unroll/i) }
m_all_instances.delete_if { |h| h['Name'].match(/^(ugam\-slave|ugam\-test)/i) }
m_all_instances.delete_if { |h| h['Name'].match(/^vpc\-prod\-stransfer$/i) }

m_all_instances.delete_if { |h| ! h.key?('role') }
m_all_instances.delete_if { |h| h['role'].match(/^(slice-jenkins|slice-vpn|slice-data-loader|slice-pipeline|slice-test|slice-bastion)$/) }
m_all_instances.delete_if { |h| h['role'].match(/mtm/) }


m_nagios_host_template = %q|define host {
  host_name    <%= m_inst['Name'] %>
  address      <%= m_inst['ip'] %>
  use          slice-host
}

|

m_nagios_hostgroup_template = %q|define hostgroup {
  hostgroup_name  <%= m_nagios_hostgroup_name %>
  members         <%= m_hosts_joined %>
}

|



m_nagios_servicegroup_template = %q|define servicegroup {
  servicegroup_name       <%= m_nagios_hostgroup_name %>
  alias                   <%= m_nagios_hostgroup_name %>
}


|

m_groups = {}
m_renderer_host_template = ERB.new(m_nagios_host_template)
m_all_instances.each do |m_inst|
  m_hostgroup = m_inst['role']
  m_inst['nagios_host_def'] = m_renderer_host_template.result(binding)
  m_groups[m_hostgroup] = {} if ! m_groups.key?(m_hostgroup)
  m_groups[m_hostgroup]['hosts'] = [] if ! m_groups[m_hostgroup].key?('hosts')
  m_groups[m_hostgroup]['hosts'] << m_inst
end

#pp m_groups

# TODO: remove all hostgroup files previously created, for now just wipe hostgroup files away

Dir.glob("/etc/nagios/conf.d/slice/**/*_hostgroup.cfg") do |m_filename|
    File.delete m_filename
end


m_renderer_hostgr_template = ERB.new(m_nagios_hostgroup_template)
m_renderer_servicegroup_template = ERB.new(m_nagios_servicegroup_template)
m_groups.keys.each do |m_group_key|
  #pp m_group_key
  m_hosts = []
  m_groups[m_group_key]['hosts'].each do |m_host|
    m_hosts << m_host['Name']
  end
  m_hosts_joined = m_hosts.join(',')
  m_nagios_hostgroup_name = m_group_key
  m_component = (  m_group_key.split('-')[1] ) ? m_group_key.split('-')[1] : 'general'
  #puts m_component
  m_groups[m_group_key]["nagios_hostgroup_def"] = m_renderer_hostgr_template.result(binding)
  m_groups[m_group_key]['servicegroup'] = m_renderer_servicegroup_template.result(binding)
  m_host_defs = ''
  FileUtils::mkdir_p m_config['out_path']
  m_dir = m_config['out_path'] + m_group_key + '/'
  #pp 'DIR: ' + m_dir
  FileUtils::mkdir_p m_dir
  m_groups[m_group_key]['hosts'].each do |m_host|
    m_host_defs << m_host['nagios_host_def']
  end
  #pp m_host_defs
  m_host_defs << m_groups[m_group_key]['nagios_hostgroup_def']
  #puts m_host_defs
  File.write(m_dir + m_group_key + '_hostgroup.cfg', m_host_defs)
  File.write(m_dir + 'servicegroup.cfg', m_groups[m_group_key]['servicegroup']) if ( ! File.file?(m_dir + 'servicegroup.cfg' ) )
  #puts "NEXT ####################\n"
end

FileUtils.touch('/tmp/nagios_reload')

#pp m_groups
