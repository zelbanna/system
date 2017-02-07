#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

The ESXi interworking module

"""
__author__ = "Zacharias El Banna"
__version__ = "4.0"
__status__ = "Production"

from PasswordContainer import esxi_username, esxi_password
from SystemFunctions import sysLogMsg, sysCheckHost
from netsnmp import VarList, Varbind, Session
from select import select

########################################### ESXi ############################################
#
# ESXi command interaction
#

class ESXi(object):
 
 #
 # Each ESXi Server has an IP and probably KVM means for out of band access.
 # Here I assume kvm IP is reachable through DNS by adding '-' and KVM type to FQDN:
 # <hostname>-[kvm|ipmi|amt].<domain>
 #
 def __init__(self,aesxihost, akvm=None):
  fqdn = aesxihost.split('.')
  self.hostname  = fqdn[0]
  if len(fqdn) == 2:
   self.domain = fqdn[1]
  else:
   self.domain = None
  self.kvm = akvm
  self.sshclient = None
  self.community = "public"
  self.vmstatemap  = { "1" : "powered on", "2" : "powered off", "3" : "suspended", "powered on" : "1", "powered off" : "2", "suspended" : "3" }
  self.backuplist = []

 def __str__(self):
  return str(self.hostname) + " SNMP_Community:" + str(self.community) + " SSHclient:" + str(self.sshclient) + " Backuplist:" + str(self.backuplist)
   
 def log(self,amsg):
  sysLogMsg(amsg, "/var/log/network/" + self.hostname + ".operations.log")

 # Check different FQDN for KVM types
 def getKVMType(self, adefault = None):
  if self.kvm:
   return self.kvm
  elif self.domain:
   for type in ['amt','ipmi','kvm']:
    if sysCheckHost("{}-{}.{}".format(self.hostname,type,self.domain)):
     self.kvm = type
     return type
  return adefault

 def createLock(self,atime):
  sysLockPidFile("/tmp/esxi." + self.hostname + ".vm.pid",atime)

 def releaseLock(self):
  sysReleasePidFile("/tmp/esxi." + self.hostname + ".vm.pid")

 def sshConnect(self):
  from paramiko import SSHClient, AutoAddPolicy, AuthenticationException
  try:
   self.sshclient = SSHClient()
   self.sshclient.set_missing_host_key_policy(AutoAddPolicy())
   self.sshclient.connect(self.hostname, username=esxi_username, password=esxi_password )
   # self.sshclient.get_transport().set_log_channel(self.hostname)
  except AuthenticationException:
   print "DEBUG: Authentication failed when connecting to %s" % self.hostname
   return False
  return True

 def sshSend(self,amessage):
  if not self.sshclient == None:
   output = ""
   self.log("sendESXi: [" + amessage + "]")
   stdin, stdout, stderr = self.sshclient.exec_command(amessage)
   while not stdout.channel.exit_status_ready():
    # Only print data if there is data to read in the channel
    if stdout.channel.recv_ready():
     rl, wl, xl = select([stdout.channel], [], [], 0.0)
     if len(rl) > 0:
      output = output + stdout.channel.recv(4096)
   return output.rstrip('\n')
  else:
   self.log("Error: trying to send to closed channel")

 def sshClose(self):
  if not self.sshclient == None:
   try:
    self.sshclient.close()
    self.sshclient = None
   except Exception as err:
    self.log( "Close error: " + str(err))

 def getIdVM(self, aname):
  try:
   vmnameobjs = VarList(Varbind('.1.3.6.1.4.1.6876.2.1.1.2'))
   session = Session(Version = 2, DestHost = self.hostname, Community = self.community, UseNumeric = 1, Timeout = 100000, Retries = 2)
   session.walk(vmnameobjs)
   for result in vmnameobjs:
    if result.val == aname:
     return int(result.iid)
  except:
   pass
  return -1

 def getStateStr(self, astate):
  return self.vmstatemap[astate]
 
 def getStateVM(self, aid):
  try:
   vmstateobj = VarList(Varbind(".1.3.6.1.4.1.6876.2.1.1.6." + str(aid)))
   session = Session(Version = 2, DestHost = self.hostname, Community = self.community, UseNumeric = 1, Timeout = 100000, Retries = 2)
   session.get(vmstateobj)
   return vmstateobj[0].val
  except:
   pass
  return "unknown"

 def loadVMs(self):
  #
  # Returns a list with tuples of strings: [ vm.id, vm.name, vm.powerstate, vm.to_be_backedup ]
  #
  statelist=[]
  try:
   vmnameobjs = VarList(Varbind('.1.3.6.1.4.1.6876.2.1.1.2'))
   vmstateobjs = VarList(Varbind('.1.3.6.1.4.1.6876.2.1.1.6'))

   session = Session(Version = 2, DestHost = self.hostname, Community = self.community, UseNumeric = 1, Timeout = 100000, Retries = 2)
   session.walk(vmnameobjs)
   session.walk(vmstateobjs)

   index = 0
   for result in vmnameobjs:
    statetuple = [result.iid, result.val, self.vmstatemap[vmstateobjs[index].val]]
    statetuple.append(result.val in self.backuplist)
    statelist.append(statetuple)
    index = index + 1
  except Exception as exception_error:
   print "DEBUG " + str(exception_error)
  return statelist

 def backupLoadFile(self, abackupfile):
  #
  # BackupFile contains list of vm names to backup
  #
  try:
   data = self.sshSend("cat " + abackupfile)
   self.backuplist = data.split()
  except:
   return False
  return True   
 
 def backupAddVM(self, abackupfile, avmname):
  #
  # Assume not loaded Backup file?
  #
  try:
   self.loadBackupFile(abackupfile)
   if not avmname in self.backuplist:
    self.sshSend("echo '" + avmname + "' >> " + abackupfile)
  except:
   pass
