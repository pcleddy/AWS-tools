#!/var/lib/nagios/.rvm/wrappers/ruby-2.3.1/ruby

require 'aws-sdk'
require 'pp'
require 'erb'


# INIT I5

region = 'us-east-1'
all_instances = []
live = true
storage_filename = '/tmp/resp_encoded'
config = {'out_path' => '/etc/nagios/conf.d/slice/'}

my_ec2_client = Aws::EC2::Client.new(region: region)

begin

  if ( live == true )
    my_ec2_client = Aws::EC2::Client.new(region: region)
    resp = my_ec2_client.describe_instances({dry_run: false, filters: [{name: "instance-state-name", values: ["running"], }, ], })
    data = Marshal.dump(resp.data)
    File.write(storage_filename, data)
  else 
    resp_restore = File.read(storage_filename)
    resp = Marshal.load(resp_restore)
  end

  resp.reservations.each do |reservation|
    reservation.instances.each do |inst_tmp|
      inst = {}
      inst['ip'] = inst_tmp.private_ip_address
      inst_tmp.tags.each do |tag|
        inst[tag.key] = tag.value
      end

      # get rid of a ton of aws garbage tags
      inst.delete_if {|key, value| key.include? ':' }

      # add cleaned up instance hash to array of all instances
      all_instances << inst
    end
  end
rescue Aws::EC2::Errors::ServiceError
  puts 'Error calling EC2 API'
end

#pp resp;exit

all_instances.each do |inst|
  #pp inst

  inst["Name"] = 'noname' if ( ! inst["Name"] )

  if (inst.has_key?("Environment")) 
    inst["environment"] = inst.delete("Environment").downcase
  end
  if (inst.has_key?("Role")) 
    inst["role"] = inst.delete("Role").downcase
  end
  if (inst.has_key?("role")) 
    inst["role"] = inst["role"].downcase
  end
  if (inst.has_key?("name")) 
    inst["Name"] = inst.delete("name").downcase
  end
  if (inst["Name"].match(/^VPCPROD/))
    inst["Name"].gsub!('VPCPROD', '')
    inst["Name"].gsub!(' ', '')
    inst["Name"].gsub!('#', '_')
    #puts inst["Name"]
  end


  # standardize hostnames
  inst["Name"].gsub!(/[()]/, '')
  inst["Name"].gsub!(/^\s+/, '')
  inst["Name"].gsub!(/\s+$/, '')
  inst["Name"].gsub!(' ', '_')
  inst["Name"].downcase!

end

#pp all_instances;exit

#### delete all instances from staging; they are not monitored by Nagios

all_instances.delete_if { |h| h['environment'] == 'staging' }
all_instances.delete_if { |h| h['Name'].match(/stag/i) }
all_instances.delete_if { |h| h['Name'].match(/noname/i) }
#all_instances.delete_if { |h| h['Name'].match(/unroll/i) }
all_instances.delete_if { |h| h['Name'].match(/^(ugam\-slave|ugam\-test)/i) }
all_instances.delete_if { |h| h['Name'].match(/^vpc\-prod\-stransfer$/i) }

all_instances.delete_if { |h| ! h.key?('role') }
all_instances.delete_if { |h| h['role'].match(/^(slice-jenkins|slice-vpn|slice-data-loader|slice-pipeline|slice-test|slice-bastion)$/) }
all_instances.delete_if { |h| h['role'].match(/mtm/) }


nagios_host_template = %q|define host {
  host_name    <%= inst['Name'] %>
  address      <%= inst['ip'] %>
  use          slice-host
}

|

nagios_hostgroup_template = %q|define hostgroup {
  hostgroup_name  <%= nagios_hostgroup_name %>
  members         <%= hosts_joined %>
}

|



nagios_servicegroup_template = %q|define servicegroup {
  servicegroup_name       <%= nagios_hostgroup_name %>
  alias                   <%= nagios_hostgroup_name %>
}


|

groups = {}
renderer_host_template = ERB.new(nagios_host_template)
all_instances.each do |inst|
  hostgroup = inst['role']
  inst['nagios_host_def'] = renderer_host_template.result(binding)
  groups[hostgroup] = {} if ! groups.key?(hostgroup)
  groups[hostgroup]['hosts'] = [] if ! groups[hostgroup].key?('hosts')
  groups[hostgroup]['hosts'] << inst
end

#pp groups

# TODO: remove all hostgroup files previously created, for now just wipe hostgroup files away

Dir.glob("/etc/nagios/conf.d/slice/**/*_hostgroup.cfg") do |filename|
    File.delete filename
end


renderer_hostgr_template = ERB.new(nagios_hostgroup_template)
renderer_servicegroup_template = ERB.new(nagios_servicegroup_template)
groups.keys.each do |group_key|
  #pp group_key
  hosts = []
  groups[group_key]['hosts'].each do |host|
    hosts << host['Name']
  end
  hosts_joined = hosts.join(',')
  nagios_hostgroup_name = group_key
  component = (  group_key.split('-')[1] ) ? group_key.split('-')[1] : 'general'
  #puts component
  groups[group_key]["nagios_hostgroup_def"] = renderer_hostgr_template.result(binding)
  groups[group_key]['servicegroup'] = renderer_servicegroup_template.result(binding)
  host_defs = ''
  FileUtils::mkdir_p config['out_path']
  dir = config['out_path'] + group_key + '/'
  #pp 'DIR: ' + dir
  FileUtils::mkdir_p dir
  groups[group_key]['hosts'].each do |host|
    host_defs << host['nagios_host_def']
  end
  #pp host_defs
  host_defs << groups[group_key]['nagios_hostgroup_def']
  #puts host_defs
  File.write(dir + group_key + '_hostgroup.cfg', host_defs)
  File.write(dir + 'servicegroup.cfg', groups[group_key]['servicegroup']) if ( ! File.file?(dir + 'servicegroup.cfg' ) )
  #puts "NEXT ####################\n"
end

FileUtils.touch('/tmp/nagios_reload')

#pp groups
