#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

The ESXi interworking module

"""
__author__ = "Zacharias El Banna"
__version__ = "1.0GA"
__status__ = "Production"

from PasswordContainer import esxi_username, esxi_password
from GenLib import GenDevice, sys_log_msg, sys_lock_pidfile, sys_release_pidfile, sys_get_host, sys_is_ip
from netsnmp import VarList, Varbind, Session
from select import select
from os import remove, path

########################################### ESXi ############################################
#
# ESXi command interaction
#

class ESXi(GenDevice):

 _vmstatemap  = { "1" : "powered on", "2" : "powered off", "3" : "suspended", "powered on" : "1", "powered off" : "2", "suspended" : "3" }

 @classmethod
 def get_state_str(cls,astate):
  return cls._vmstatemap[astate]
  
 #
 # Each ESXi Server has an IP and probably KVM means for out of band access.
 # Here I assume kvm IP is reachable through DNS by adding '-' and KVM type to FQDN:
 # <hostname>-[kvm|ipmi|amt].<domain>
 #
 def __init__(self,ahost,adomain=None):
  if ahost and adomain:
   self.name   = ahost
   self._kvmip = None
   GenDevice.__init__(self,ahost,adomain,'esxi')
  elif sys_is_ip(ahost):
   self.name   = "unknown"
   self._kvmip = ahost
   GenDevice.__init__(self,ahost,None,'esxi')
  else:
   fqdn = ahost.split('.')
   self.name  = fqdn[0]
   domain = None if len(fqdn) < 2 else ".".join(fqdn[1:])
   self._kvmip  = None
   GenDevice.__init__(self,fqdn[0],domain,'esxi')
  self._sshclient = None
  self.community = "public"
  self.backuplist = []
  self.statefile = "/var/tmp/esxi." + self.name + ".vmstate.log"
  self._threads = {}
  
 def __str__(self):
  return str(self.name) + " SSHConnected:" + str(self._sshclient != None)  + " SNMP_Community:" + self.community + " Backuplist:" + str(self.backuplist) + " statefile:" + self.statefile + " Threads:" + str(self._threads.keys())

 def log(self,amsg):
  sys_log_msg(amsg, "/var/log/network/" + self.name + ".operations.log")

 def threading(self, aoperation):
  from threading import Thread
  op = getattr(self, aoperation, None)
  if op:
   thread = Thread(target = op)
   self._threads['aoperation'] = thread
   thread.name = aoperation
   thread.start()
   self.log("threading: Started operation [{}]".format(aoperation))
  else:
   self.log("threading: Illegal operation passed [{}]".format(aoperation))

 # Different FQDN for KVM types
 def get_kvm_ip(self, adefaulttype = 'ipmi'):
  if self._kvmip:
   return self._kvmip
  elif self._domain:
   for type in ['amt','ipmi','kvm']:
    ip = sys_get_host("{0}-{1}.{2}".format(self.name,type,self._domain))
    if ip:
     self._kvmip = ip + ":16992" if type == 'amt' else ip
     break
   else:
    # No DNS found
    ip = "{}-{}.{}".format(self.name,adefaulttype,self._domain)
    self._kvmip = ip + ":16992" if adefaulttype == "amt" else ip
  return self._kvmip

 def create_lock(self,atime):
  sys_lock_pidfile("/tmp/esxi." + self.name + ".vm.pid",atime)

 def release_lock(self):
  sys_release_pidfile("/tmp/esxi." + self.name + ".vm.pid")

 #
 # ESXi ssh interaction - Connect() send, send,.. Close()
 #
 def ssh_connect(self):
  if not self._sshclient:
   from paramiko import SSHClient, AutoAddPolicy, AuthenticationException
   try:
    self._sshclient = SSHClient()
    self._sshclient.set_missing_host_key_policy(AutoAddPolicy())
    self._sshclient.connect(self._fqdn, username=esxi_username, password=esxi_password )
   except AuthenticationException:
    self.log("DEBUG: Authentication failed when connecting to %s" % self._fqdn)
    self._sshclient = None
    return False
  return True

 def ssh_send(self,amessage):
  if self._sshclient:
   output = ""
   self.log("ssh_send: [" + amessage + "]")
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

 def ssh_close(self):
  if self._sshclient:
   try:
    self._sshclient.close()
    self._sshclient = None
   except Exception as err:
    self.log( "Close error: " + str(err))

 def get_id_vm(self, aname):
  try:
   vmnameobjs = VarList(Varbind('.1.3.6.1.4.1.6876.2.1.1.2'))
   session = Session(Version = 2, DestHost = self._fqdn, Community = self.community, UseNumeric = 1, Timeout = 100000, Retries = 2)
   session.walk(vmnameobjs)
   for result in vmnameobjs:
    if result.val == aname:
     return int(result.iid)
  except:
   pass
  return -1
 
 def get_state_vm(self, aid):
  try:
   vmstateobj = VarList(Varbind(".1.3.6.1.4.1.6876.2.1.1.6." + str(aid)))
   session = Session(Version = 2, DestHost = self._fqdn, Community = self.community, UseNumeric = 1, Timeout = 100000, Retries = 2)
   session.get(vmstateobj)
   return vmstateobj[0].val
  except:
   pass
  return "unknown"

 def get_vms(self):
  #
  # Returns a list with tuples of strings: [ vm.id, vm.name, vm.powerstate, vm.to_be_backedup ]
  #
  statelist=[]
  try:
   vmnameobjs = VarList(Varbind('.1.3.6.1.4.1.6876.2.1.1.2'))
   vmstateobjs = VarList(Varbind('.1.3.6.1.4.1.6876.2.1.1.6'))
   session = Session(Version = 2, DestHost = self._fqdn, Community = self.community, UseNumeric = 1, Timeout = 100000, Retries = 2)
   session.walk(vmnameobjs)
   session.walk(vmstateobjs)
   index = 0
   for result in vmnameobjs:
    statetuple = [result.iid, result.val, ESXi.get_state_str(vmstateobjs[index].val)]
    statetuple.append(result.val in self.backuplist)
    statelist.append(statetuple)
    index = index + 1
  except:
   pass
  return statelist

 #
 # Simple backup schema for ghettoVCB - assumption is that there is a file on the ESXi <abackupfile> that
 #  contains a list of names of virtual machines to backup
 # 
 def backup_load_file(self, abackupfile):
  try:
   data = self.ssh_send("cat " + abackupfile)
   self.backuplist = data.split()
  except:
   return False
  return True   
 
 def backup_add_vm(self, abackupfile, avmname):
  try:
   self.backup_load_file(abackupfile)
   if not avmname in self.backuplist:
    self.ssh_send("echo '" + avmname + "' >> " + abackupfile)
  except:
   pass

 #
 # Shutdown methods to/from default statefile
 #
 #

 def startup_vms(self):
  from time import sleep
  # Power up everything in the statefile
  if not path.isfile(self.statefile):
   self.log("startup_vms: Has no reason to run powerUp as no VMs were shutdown..")
   return False
  
  self.create_lock(2)
  self.ssh_connect()

  statefilefd = open(self.statefile)
  for line in statefilefd:
   if line == "---------\n":
    self.log("startup_vms: Powerup - MARK found, wait a while for dependent")
    sleep(60)
   else:
    vm = line.strip('\n').split(',')
    if vm[2] == "1" and not vm[1] == "management" :
     esxi.ssh_send("vim-cmd vmsvc/power.on " + vm[0])
  remove(sfile)
  self.ssh_close()
  self.release_lock()
  return True

 def shutdown_vms(self, aExceptlist):
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
   self.log("shutdown_vms: Shutdown all VMs VMs are already shutdown! exit")
   return False

  deplist=[]
  freelist=[]
  self.create_lock(2)

  try:
   vmlist = self.getVMs()
   self.ssh_connect()
   # Start go through all vms
   #
   for vm in vmlist:
    # Only interested in active VMs
    if vm[2] == "1":
     if vm[1].startswith("svc-nas"):
      deplist.append(vm)
     elif vm[1] not in aExceptlist:
      freelist.append(vm)
      self.ssh_send("vim-cmd vmsvc/power.shutdown " + vm[0])

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
    self.ssh_send("vim-cmd vmsvc/power.shutdown " + vm[0])

   # Powering off machines that doesn't respond too well to guest shutdowns
   #
   sleep(60)
   vmlist = self.get_vms()
   for vm in vmlist:
    if vm[2] == "1":
     if vm[1].startswith("svc-nas"):
      self.log("shutdown_vms: Shutdown of NAS vm not completed..")
     elif vm[1].startswith("pulse"):
      self.ssh_send("vim-cmd vmsvc/power.off " + vm[0])
      self.log("shutdown_vms: powering off machine: {}!".format(vm[0]))
     elif vm[1] not in aExceptlist:
      # Correct? or pass?
      self.ssh_send("vim-cmd vmsvc/power.suspend " + vm[0])
      self.log("shutdown_vms: suspending machine: {}!".format(vm[0]))

   # Done, finish off local machine
   #
   self.ssh_close()
   self.release_lock()
   self.log("shutdown_vms: Done! Ready for powerloss, awaiting system halt")
  except Exception as vmerror:
   self.log("ERROR: " + str(vmerror))
