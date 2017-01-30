#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

Generic Functions

"""
__author__ = "Zacharias El Banna"                     
__version__ = "3.1"
__status__ = "Production"

from os import remove, path as ospath, system
from time import sleep, localtime, strftime
 
################################# Generics ####################################

def pingOS(ip):
 return system("ping -c 1 -w2 " + ip + " > /dev/null 2>&1") == 0

def sysCheckResults(test):
 return "success" if test else "failure"

sysDebug = False

def sysSetDebug(astate):
 global sysDebug
 sysDebug = astate

sysLogFile = '/var/log/system/network.functions.log'

def sysSetLog(alogfile):
 global sysLogFile
 sysLogFile = alogfile
    
def sysLogMsg(amsg):
 if sysDebug: print "Log: " + amsg
 with open(sysLogFile, 'a') as f:
  f.write(unicode("{} : {}\n".format(strftime('%Y-%m-%d %H:%M:%S', localtime()), amsg)))

def sysStr2Hex(arg):
 try:
  return '0x{0:02x}'.format(int(arg))
 except:
  return '0x00'    

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
