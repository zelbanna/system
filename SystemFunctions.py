#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

Generic Functions

"""
__author__ = "Zacharias El Banna"                     
__version__ = "3.0"
__status__ = "Production"

from os import remove, path as ospath
from time import sleep

################################# Generics ####################################

def sysCheckResults(test):
 return "success" if test else "failure"

sysDebug = False

def sysSetDebug(astate):
 global sysDebug
 sysDebug = astate

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
