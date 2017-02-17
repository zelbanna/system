#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

The ESXi interworking module

"""
__author__ = "Zacharias El Banna"
__version__ = "6.0"
__status__ = "Production"

from PasswordContainer import esxi_username, esxi_password
from SystemFunctions import sysLogMsg, sysCheckHost, sysLockPidFile, sysReleasePidFile
from netsnmp import VarList, Varbind, Session
from select import select
from os import remove, path

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
  self._sshclient = None
  self.community = "public"
  self.vmstatemap  = { "1" : "powered on", "2" : "powered off", "3" : "suspended", "powered on" : "1", "powered off" : "2", "suspended" : "3" }
  self.backuplist = []
  self.statefile = "/var/tmp/esxi." + self.hostname + ".vmstate.log"
  self._threads = []
  
 def __str__(self):
  return str(self.hostname) + " SSHConnected:" + str(self._sshclient != None)  + " SNMP_Community:" + self.community + " Backuplist:" + str(self.backuplist) + " statefile:" + self.statefile + " Threads:" + str(map((lambda x: x.name), self._threads))

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

 #
 # ESXi ssh interaction - Connect() send, send,.. Close()
 #
 def sshConnect(self):
  if not self._sshclient:
   from paramiko import SSHClient, AutoAddPolicy, AuthenticationException
   try:
    self._sshclient = SSHClient()
    self._sshclient.set_missing_host_key_policy(AutoAddPolicy())
    self._sshclient.connect(self.hostname, username=esxi_username, password=esxi_password )
    # self._sshclient.get_transport().set_log_channel(self.hostname)
   except AuthenticationException:
    self.log("DEBUG: Authentication failed when connecting to %s" % self.hostname)
    self._sshclient = None
    return False
  return True

 def sshSend(self,amessage):
  if self._sshclient:
   output = ""
   self.log("sendESXi: [" + amessage + "]")
   stdin, stdout, stderr = self._sshclient.exec_command(amessage)
   while not stdout.channel.exit_status_ready():
    if stdout.channel.recv_ready():
     rl, wl, xl = select([stdout.channel], [], [], 0.0)
     if len(rl) > 0:
      output = output + stdout.channel.recv(4096)
   return output.rstrip('\n')
  else:
   self.log("Error: trying to send to closed channel")
   self._sshclient = None

 def sshClose(self):
  if self._sshclient:
   try:
    self._sshclient.close()
    self._sshclient = None
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
  except:
   pass
  return statelist

 def widgetVMs(self):
  pass

 #
 # Simple backup schema for ghettoVCB - assumption is that there is a file on the ESXi <abackupfile> that
 #  contains a list of names of virtual machines to backup
 # 
 def backupLoadFile(self, abackupfile):
  try:
   data = self.sshSend("cat " + abackupfile)
   self.backuplist = data.split()
  except:
   return False
  return True   
 
 def backupAddVM(self, abackupfile, avmname):
  try:
   self.loadBackupFile(abackupfile)
   if not avmname in self.backuplist:
    self.sshSend("echo '" + avmname + "' >> " + abackupfile)
  except:
   pass

 #
 # Shutdown methods to/from default statefile
 #
 #

 def threading(self, aoperation):
  import threading
  op = getattr(self, aoperation, None)
  if op:
   thread = threading.Thread(target = op)
   self._threads.append(thread)
   thread.name = aoperation
   thread.start()
   self.log("threading: Started operation [{}]".format(aoperation))
  else:
   self.log("threading: Illegal operation passed [{}]".format(aoperation))
  
 def startupVMs(self):
  from time import sleep
  # Power up everything in the statefile
  if not path.isfile(self.statefile):
   self.log("startupVMs: Has no reason to run powerUp as no VMs were shutdown..")
   return False
  
  self.createLock(2)
  self.sshConnect()

  statefilefd = open(self.statefile)
  for line in statefilefd:
   if line == "---------\n":
    self.log("startupVMs: Powerup - MARK found, wait a while for dependent")
    sleep(60)
   else:
    vm = line.strip('\n').split(',')
    if vm[2] == "1" and not vm[1] == "management" :
     esxi.sshSend("vim-cmd vmsvc/power.on " + vm[0])
  remove(sfile)
  self.sshClose()
  self.releaseLock()
  return True

 def shutdownVMs(self):
  from time import sleep
  # Power down everything and save to the statefile, APCupsd statemachine:
  #
  # 1) apcupsd calls event triggering shutdown (runlimit, timelimit)
  # 2.1) apcupsd calls doshutdown
  # 2.2) apcupsd writes /etc/apcupsd/powerfail   <<--- This triggers everything
  #
  # X) Remove doshutdown's shutdown request within apccontrol
  # X) Create a doshutdown which simply calls /usr/local/sbin/esxi-shutdown.py <esxi-host> for all esxi-hosts
  # X) Add  to  doshutdown a `shutdown -h 10`
  #
  # 3) any call to shutdown -h x will call /etc/init.d/halt within x seconds - THIS WILL TRIGGER CONTROLLED SHUTDOWN OF EVERYTHING
  # 4) /etc/init.d/halt will call /etc/apcupsd/ups-monitor
  # 5) ups-monitor checks for powerfail file and calls /etc/apcupsd/apccontrol (again) with killpower
  # 6) apccontrol killpower -> /sbin/apcupsd killpower
  # 7) UPS is signaled and start shutdown sequence ( awaiting new power feed )
  if path.isfile(self.statefile):
   self.log("shutdownVMs: Shutdown all VMs VMs are already shutdown! exit")
   return False

  deplist=[]
  freelist=[]
  self.createLock(2)

  try:
   vmlist = self.loadVMs()
   self.sshConnect()
   # Start go through all vms
   #
   for vm in vmlist:
    # Only interested in active VMs
    if vm[2] == "1":
     if vm[1].startswith("nas"):
      deplist.append(vm)
     elif vm[1] != "management":
      freelist.append(vm)
      self.sshSend("vim-cmd vmsvc/power.shutdown " + vm[0])

   # Write statelog
   #
   statefilefd = open(self.statefile,'w')
   for vm in deplist:
    statefilefd.write(vm[0]+','+ vm[1] + ',' + vm[2] +"\n")
   statefilefd.write("---------\n")
   for vm in freelist:
    statefilefd.write(vm[0]+','+ vm[1] + ',' + vm[2] +"\n")
   statefilefd.close()
 
   # Shutdown VMs that has a dependence
   #
   sleep(20)
   for vm in deplist:
    self.sshSend("vim-cmd vmsvc/power.shutdown " + vm[0])

   # Powering off machines that doesn't respond too well to guest shutdowns
   #
   sleep(60)
   vmlist = self.loadVMs()
   for vm in vmlist:
    if vm[2] == "1":
     if vm[1].startswith("nas"):
      self.log("Shutdown of NAS vm not completed..")
     elif not vm[1] == "management":
      self.sshSend("vim-cmd vmsvc/power.off " + vm[0])

   # Done, finish off local machine
   #
   self.sshClose()
   self.releaseLock()
   self.log("shutdownVMs: Done! Ready for powerloss, awaiting system halt")
  except Exception as vmerror:
   self.log("ERROR: " + str(vmerror))
