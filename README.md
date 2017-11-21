# AWS-tools

Misc tools hitting the AWS API using Ruby, Javascript, etc. 

New addition: "snapshots" subdir has new project using Python against AWS API to do scheduled backups.

## automated*snapshot.js

WARNING: Please be very, very careful using this script, it can remove resources from your environment!

Note: I got interested in using Javascript after listening to Ryan Dahl's first video presentation on Node.

These three scripts backup AWS resources: EC2, RDS and Redshift. The duration of backups is flexible, and any backup resources older than the expired date are removed.

Of mention is that the various sections run independently of each other since Javascript does not wait to receive I/O back from the API. So, this is indeed a simple example of code running in parallel.

## build_hostgroups

This script hits the AWS API to pull in all running EC2 instances, filter out the production nodes based on tags, and then, builds Nagios hostgroups dynamically using a templating mechanism.

It can be run every five minutes (for example) on the Nagios server to update configs on-the-fly.

## check_cw_alarms

A basic script that checks the return value of a CloudWatch alarm, and outputs Nagios compatible replies.

## check_sqs

Script to check SQS levels maximum values

## og_versions

If you have versioning turned on your S3 buckets, this tool will allow you to see a diff between text type documents.

There is no built-in way to check diffs (AFAIK) using the AWS console.

## sg_explorer

This tool reads in all security group rules, and will output not only what is allowed to reach a resource in that group, but also what resource a resource can reach based on the security groups it is in.

This could and should be taken to the next level to take a single resouce as input, and show all egress/ingress permitted.

Output is via CGI, so can be run on a webserver like Apache.

## sg_inspector

Similar to sg_explorer with the exception that the output is to the terminal, not via a CGI gateway.
