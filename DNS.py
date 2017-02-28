#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

 DNS interworking module

"""
__author__ = "Zacharias El Banna"                     
__version__ = "3.2"
__status__ = "Production"

from PasswordContainer import loopia_username, loopia_password, loopia_domain
from GenLib import sys_log_msg, sys_file_replace
from subprocess import check_output, check_call
from time import sleep
from socket import gethostbyname

################################ LOOPIA DNS ###################################
#
# Change IP for a domain in loopia DNS
#
loopia_domain_server_url = 'https://api.loopia.se/RPCSERV' 

def set_loopia_ip(subdomain, newip):
 import xmlrpclib
 try:
  client = xmlrpclib.ServerProxy(uri = loopia_domain_server_url, encoding = 'utf-8')
  data = client.getZoneRecords(loopia_username, loopia_password, loopia_domain, subdomain)[0]
  oldip = data['rdata']
  data['rdata'] = newip
  status = client.updateZoneRecord(loopia_username, loopia_password, loopia_domain, subdomain, data)[0]
 except Exception as exmlrpc:
  sys_log_msg("System Error - Loopia set: " + str(exmlrpc))
  return False
 return True

#
# Get Loopia settings for subdomain
#
def get_loopia_ip(subdomain):
 import xmlrpclib
 try:
  client = xmlrpclib.ServerProxy(uri = loopia_domain_server_url, encoding = 'utf-8')
  data = client.getZoneRecords(loopia_username, loopia_password, loopia_domain, subdomain)[0]
  return data['rdata']
 except Exception as exmlrpc:
  sys_log_msg("System Error - Loopia get: " + str(exmlrpc))
  return False

def get_loopia_suffix():
 return "." + loopia_domain

################################# OpenDNS ######################################
#
# Return external IP from opendns
#
def opendns_my_ip():
 from dns import resolver
 try:
  opendns = resolver.Resolver()
  opendns.nameservers = [gethostbyname('resolver1.opendns.com')]
  myiplookup = opendns.query("myip.opendns.com",'A').response.answer[0]
  return str(myiplookup).split()[4]
 except Exception as exresolve:
  sys_log_msg("OpenDNS Error - Resolve: " + str(exresolve))
  return False
 
############################### PDNS SYSTEM FUNCTIONS ##################################
#

def get_pdns():
 recursor = check_output(["sudo","/bin/grep", "^recursor","/etc/powerdns/pdns.conf"])
 return recursor.split('=')[1].split('#')[0].strip()

#
# All-in-one, runs check, verify and (if needed) set and reload pdns service
# - returns True if was in sync and False if modified
# 
def sync_pdns(dnslist):
 pdns = get_pdns()
 if not pdns in dnslist:
  sys_log_msg("System Info - updating recursor to " + dnslist[0])
  sys_file_replace('/etc/powerdns/pdns.conf', pdns, dnslist[0])
  try:
   check_call(["/usr/sbin/service","pdns","reload"])
   sleep(1)
  except Exception as svcerr:
   sys_log_msg("System Error - Reloading PowerDNS: " + str(svcerr))
  return False
 return True  
