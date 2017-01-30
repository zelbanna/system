#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

 DNS interworking module

"""
__author__ = "Zacharias El Banna"                     
__version__ = "3.2"
__status__ = "Production"

from subprocess import check_output, check_call
from time import sleep
from PasswordContainer import loopia_username, loopia_password, loopia_domain
from SystemFunctions import sysCheckResults, sysLogMsg, sysFileReplace
from socket import gethostbyname

################################ LOOPIA DNS ###################################
#
# Change IP for a domain in loopia DNS
#
loopia_domain_server_url = 'https://api.loopia.se/RPCSERV' 

def setLoopiaIP(subdomain, newip):
 import xmlrpclib
 try:
  client = xmlrpclib.ServerProxy(uri = loopia_domain_server_url, encoding = 'utf-8')
  data = client.getZoneRecords(loopia_username, loopia_password, loopia_domain, subdomain)[0]
  oldip = data['rdata']
  data['rdata'] = newip
  status = client.updateZoneRecord(loopia_username, loopia_password, loopia_domain, subdomain, data)[0]
 except Exception as exmlrpc:
  sysLogMsg("System Error - Loopia set: " + str(exmlrpc))
  return False
 return True

#
# Get Loopia settings for subdomain
#
def getLoopiaIP(subdomain):
 import xmlrpclib
 try:
  client = xmlrpclib.ServerProxy(uri = loopia_domain_server_url, encoding = 'utf-8')
  data = client.getZoneRecords(loopia_username, loopia_password, loopia_domain, subdomain)[0]
  return data['rdata']
 except Exception as exmlrpc:
  sysLogMsg("System Error - Loopia get: " + str(exmlrpc))
  return False

def getLoopiaSuffix():
 return "." + loopia_domain

################################# OpenDNS ######################################
#
# Return external IP from opendns
#
def OpenDNSmyIP():
 from dns import resolver
 try:
  opendns = resolver.Resolver()
  opendns.nameservers = [gethostbyname('resolver1.opendns.com')]
  myiplookup = opendns.query("myip.opendns.com",'A').response.answer[0]
  return str(myiplookup).split()[4]
 except Exception as exresolve:
  sysLogMsg("OpenDNS Error - Resolve: " + str(exresolve))
  return False
 
############################### PDNS SYSTEM FUNCTIONS ##################################
#

def getPDNS():
 recursor = check_output(["sudo","/bin/grep", "^recursor","/etc/powerdns/pdns.conf"])
 return recursor.split('=')[1].split('#')[0].strip()

#
# All-in-one, runs check, verify and (if needed) set and reload pdns service
# - returns True if was in sync and False if modified
# 
def syncPDNS(dnslist):
 pdns = getPDNS()
 if not pdns in dnslist:
  sysLogMsg("System Info - updating recursor to " + dnslist[0])
  sysFileReplace('/etc/powerdns/pdns.conf', pdns, dnslist[0])
  try:
   check_call(["/usr/sbin/service","pdns","reload"])
   sleep(1)
  except Exception as svcerr:
   sysLogMsg("System Error - Reloading PowerDNS: " + str(svcerr))
  return False
 return True  
