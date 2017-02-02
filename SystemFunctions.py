#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

Generic Functions, exports:

- sysSetDebug
- sysLogDebug
- sysIP2Int
- sysInt2IP
- sysIPs2Range
- sysStr2Hex
- pingOS
- sysCheckResults
- sysSetLog
- sysDebug (bool)
- sysLogMsg

- simpleArgParser

- sysWritePidFile
- sysReadPidFile
- sysLockPid
- sysReleasePid
- sysFileReplace

"""
__author__ = "Zacharias El Banna"                     
__version__ = "4.2"
__status__ = "Production"

from os import remove, path as ospath, system
from time import sleep, localtime, strftime
from struct import pack, unpack
from socket import inet_ntoa, inet_aton

################################# Generics ####################################

sysDebug = False
sysLogFile = '/var/log/system/network.functions.log'

def sysSetDebug(astate):
 global sysDebug
 sysDebug = astate

def sysLogDebug(amsg):
 if sysDebug: print "Log: " + amsg

def sysIP2Int(addr):
 return unpack("!I", inet_aton(addr))[0]
 
def sysInt2IP(addr):
 return inet_ntoa(pack("!I", addr))

def sysIPs2Range(addr1,addr2):
 return map(lambda addr: inet_ntoa(pack("!I", addr)), range(unpack("!I", inet_aton(addr1))[0], unpack("!I", inet_aton(addr2))[0] + 1))

def sysStr2Hex(arg):
 try:
  return '0x{0:02x}'.format(int(arg))
 except:
  return '0x00'    

def pingOS(ip):
 return system("ping -c 1 -w 1 " + ip + " > /dev/null 2>&1") == 0

def sysCheckResults(test):
 return "success" if test else "failure"

def sysSetLog(alogfile):
 global sysLogFile
 sysLogFile = alogfile
    
def sysLogMsg(amsg):
 sysLogDebug(amsg)
 with open(sysLogFile, 'a') as f:
  f.write(unicode("{} : {}\n".format(strftime('%Y-%m-%d %H:%M:%S', localtime()), amsg)))

#
# Lightweight argument parser, returns a dictionary with found arguments - { arg : value }
# Requires - or -- before any argument
#
def simpleArgParser(args):
 # args should really be the argv
 argdict = {}
 currkey = None
 for arg in args:
  if arg.startswith('-'):
   if currkey:    
    argdict[currkey] = True
   currkey = arg.lstrip('-') 
  else:
   if currkey:         
    argdict[currkey] = arg
    currkey = None
                 
 if currkey:
  argdict[currkey] = True
 return argdict


def sysWritePidFile(pidfname):
 pidfile = open(pidfname,'w')
 pidfile.write(str(getpid()))
 pidfile.close()

def sysReadPidFile(pidfname):
 pid = -1
 if ospath.isfile(pidfname):
  pidfile = open(pidfname)
  pid = pidfile.readline().strip('\n')
  pidfile.close()
 return int(pid)

def sysReleasePidFile(pidfname):
 if ospath.isfile(pidfname):
  remove(pidfname)

def sysLockPidFile(pidfname, sleeptime):
 while ospath.isfile(pidfname):
  sleep(sleeptime)
 sysWritePidFile(pidfname) 

def sysFileReplace(afile,old,new):
 if afile == "" or new == "" or old == "":
  return False

 filedata = None
 with open(afile, 'r') as f:
  filedata = f.read()

 filedata = filedata.replace(old,new)

 with open(afile, 'w') as f:
  f.write(filedata)
 return True
            
