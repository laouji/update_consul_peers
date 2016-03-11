#!/bin/env python

from __future__ import print_function
import json, re, socket, subprocess


def consulMembers():
  command = ['consul', 'members']
  process = subprocess.Popen(command, stdout=subprocess.PIPE)
  lines   = ( re.split(r'\s+', line) for line in iter(process.stdout.readline, '') )

  members = {}
  for line in lines:
    if line[2] != 'alive':
      continue

    if line[3] != 'server':
      continue

    ip_addr = re.split(r'\:', line[1])
    members[ line[0] ] = ip_addr[0]

  return members

def writePeersFile(peers_ips, filepath):
  endpoints = map ( lambda ip: ip + ':8300', peers_ips )
  json_text = json.dumps(endpoints)

  print('[info] writing to %s' % filepath)
  print("%s \n" % json_text)

  fh = open(filepath, 'w')
  print(json_text, file=fh)
  fh.close()


def syncFileRemote(ip, filepath):
    remote_path = ip + ':' + filepath
    proc = subprocess.check_call(['scp', filepath, remote_path], stderr=subprocess.STDOUT)

def consulServiceStopRemote(ip):
  subprocess.check_call(['ssh', ip, 'svc -d /service/consul'], stderr=subprocess.STDOUT)

def consulServiceStartRemote(ip):
  subprocess.check_call(['ssh', ip, 'svc -u /service/consul'], stderr=subprocess.STDOUT)


members   = consulMembers()
peers_ips = [ members[host] for host in members.keys() ]

if len(peers_ips) < 3:
  print('[error] at least 3 live peers are required to reach consensus')
  exit(1)

subprocess.check_call(['svc', '-d', '/service/consul'], stderr=subprocess.STDOUT)

filepath = '/var/lib/consul/raft/peers.json'
writePeersFile(peers_ips, filepath)

localhost = socket.gethostname()

del members[localhost]

for hostname in members.keys():
  ip_addr = members[hostname]
  print('[info] syncing peers.json on host: %s, ip: %s' % (hostname, ip_addr))

  consulServiceStopRemote(ip_addr)
  syncFileRemote(ip_addr, filepath)
  consulServiceStartRemote(ip_addr)

subprocess.check_call(['svc', '-u', '/service/consul'], stderr=subprocess.STDOUT)
