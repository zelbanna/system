#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

The ESXi interworking module

"""
__author__ = "Zacharias El Banna"
__version__ = "3.0"
__status__ = "Production"

from sys import argv, exit, stdout, path as syspath
from os import getpid, remove, path as ospath
from time import sleep, strftime, localtime
from select import select

import PasswordContainer as PC
from SystemFunctions import sysDebug, setDebug

########################################### ESXi ############################################
#
# ESXi command interaction
#

revmap   = { 1 : "powered on", 2 : "powered off", 3 : "suspended" }
statemap = { "powered on" : 1, "powered off" : 2, "suspended" : 3 }

class ESXi(object):
 
 def __init__(self,aesxihost):
  self.hostname = aesxihost
  self.sshclient = None

 def log(self,amsg):
  if sysDebug: print "Log: " + amsg
  with open("/var/log/network/" + self.hostname + ".operations.log", 'a') as f:
   f.write(unicode("{} ({}): {}\n".format(strftime('%Y-%m-%d %H:%M:%S', localtime()), str(getpid()).zfill(5), amsg)))

 def createLock(self,atime):
  sysLockPidFile("/tmp/esxi." + self.hostname + ".vm.pid",atime)

 def releaseLock(self):
  sysReleasePidFile("/tmp/esxi." + self.hostname + ".vm.pid")

 def sshConnect(self):
  from paramiko import SSHClient, AutoAddPolicy, AuthenticationException

  try:
   self.sshclient = SSHClient()
   self.sshclient.set_missing_host_key_policy(AutoAddPolicy())
   self.sshclient.connect(self.hostname, username=PC.esxi_username, password=PC.esxi_password )
   # self.sshclient.get_transport().set_log_channel(self.hostname)
  except AuthenticationException:
   print "DEBUG: Authentication failed when connecting to %s" % self.hostname
   exit(1)

 def sshSend(self,amessage):
  if not self.sshclient == None:
   self.log("sendESXi: [" + amessage + "]")
   stdin, stdout, stderr = self.sshclient.exec_command(amessage)
   while not stdout.channel.exit_status_ready():
    # Only print data if there is data to read in the channel
    if stdout.channel.recv_ready():
     rl, wl, xl = select([stdout.channel], [], [], 0.0)
     if len(rl) > 0:
      print stdout.channel.recv(4096),
  else:
   self.log("Error: trying to send to closed channel")

 def sshClose(self):
  try:
   self.sshclient.close()
   self.sshclient = None
  except Exception as err:
   self.log( "Close error: " + str(err))

 #
 # Returns a list with tuples: [ vm.id, vm.name, vm.powerstate ]
 #
 def loadVMs(self):
  from netsnmp import VarList, Varbind, Session
  statelist=[]
  try:
   vmnameobjs = VarList(Varbind('.1.3.6.1.4.1.6876.2.1.1.2'))
   vmstateobjs = VarList(Varbind('.1.3.6.1.4.1.6876.2.1.1.6'))

   session = Session(Version = 2, DestHost = self.hostname, Community = "public", UseNumeric = 1, Timeout = 100000, Retries = 2)
   session.walk(vmnameobjs)
   session.walk(vmstateobjs)

   index = 0
   for result in vmnameobjs:
    currstate = vmstateobjs[index].val
    statelist.append([result.iid, result.val, statemap[currstate]])
    index = index + 1
  except Exception as exception_error:
   print "DEBUG " + str(exception_error)
  return statelist
