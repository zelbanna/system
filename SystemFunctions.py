#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

Generic Functions, exports:

- sysIP2Int
- sysInt2IP
- sysStr2Hex
- pingOS
- sysCheckResults
- sysSetDebug
- sysLogDebug
- sysSetLog
- sysDebug (bool)
- sysLogMsg

- sysWritePidFile
- sysReadPidFile
- sysLockPid
- sysReleasePid
- sysFileReplace

"""
__author__ = "Zacharias El Banna"                     
__version__ = "3.3"
__status__ = "Production"

from os import remove, path as ospath, system
from time import sleep, localtime, strftime
from struct import pack, unpack
from socket import inet_ntoa, inet_aton, gethostbyaddr

################################# Generics ####################################

def sysIP2Int(addr):
 return unpack("!I", inet_aton(addr))[0]
 
def sysInt2IP(addr):
 return inet_ntoa(pack("!I", addr))

def sysStr2Hex(arg):
 try:
  return '0x{0:02x}'.format(int(arg))
 except:
  return '0x00'    

def pingOS(ip):
 return system("ping -c 1 -w 1 " + ip + " > /dev/null 2>&1") == 0

def sysCheckResults(test):
 return "success" if test else "failure"

sysDebug = False

def sysSetDebug(astate):
 global sysDebug
 sysDebug = astate

def sysLogDebug(amsg):
 if sysDebug: print "Log: " + amsg

sysLogFile = '/var/log/system/network.functions.log'

def sysSetLog(alogfile):
 global sysLogFile
 sysLogFile = alogfile
    
def sysLogMsg(amsg):
 sysLogDebug(amsg)
 with open(sysLogFile, 'a') as f:
  f.write(unicode("{} : {}\n".format(strftime('%Y-%m-%d %H:%M:%S', localtime()), amsg)))

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
 if file == "" or new == "" or old == "":
  return False

 filedata = None
 with open(afile, 'r') as file :
  filedata = file.read()
       
 filedata = filedata.replace(old,new)
        
 with open(afile, 'w') as file:
  file.write(filedata)
 return True
            
