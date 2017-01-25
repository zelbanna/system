#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

System, ESXi, IPMI, DNS and networking interworking module

- One can use other modules imported by this one "nested :-)

"""
__author__ = "Zacharias El Banna"                     
__version__ = "3.0"
__status__ = "Production"

from sys import argv, exit, path as syspath
from subprocess import check_output, check_call

syspath.append('/etc')
import PasswordContainer as PC
import SystemFunctions import sysCheckResults, sysStr2Hex

################################### IPMI #######################################

class IPMI(object):
 def __init__(self, ahost)
  self.hostname = ahost
  
 def printInfo(self, agrep):
  readout = check_output("ipmitool -H " + self.hostname + " -U " + PC.ipmi_username + " -P " + PC.ipmi_password + " sdr | grep -E '" + agrep + "'",shell=True)
  for fanline in readout.split('\n'):
   if fanline is not "":
    fan = fanline.split()
    print fan[0] + "\t" + fan[3] + " " + fan[4]

 def setFans(self, arear, afront):
  from io import open
  from os import devnull
  FNULL = open(devnull, 'w')
  rear  = sysStr2Hex(arear)
  front = sysStr2Hex(afront)
  ipmistring = "ipmitool -H " + self.hostname + " -U " + PC.ipmi_username + " -P " + PC.ipmi_password + " raw 0x3a 0x01 0x00 0x00 " + rear + " " + rear + " " + front + " " + front + " 0x00 0x00"
  res = check_call(ipmistring,stdout=FNULL,stderr=FNULL,shell=True)
  print sysCheckResults(res)
