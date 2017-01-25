#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

IPMI interworking module

- https://lime-technology.com/forum/index.php?topic=39238.0
- requires ipmitool to be installed on system and "in path"
- ipmitool -H <host> -U <username> -P <password> raw 0x3a 0x01 0x00 0x00 0x28 0x28 0x2d 0x2d 0x00 0x00

"""
__author__ = "Zacharias El Banna"                     
__version__ = "3.1"
__status__ = "Production"

from sys import argv, exit, path as syspath
from subprocess import check_output, check_call

from PasswordContainer import ipmi_username, ipmi_password
from SystemFunctions import sysCheckResults, sysStr2Hex

################################### IPMI #######################################

class IPMI(object):
 def __init__(self, ahost)
  self.hostname = ahost
  
 def printInfo(self, agrep):
  readout = check_output("ipmitool -H " + self.hostname + " -U " + ipmi_username + " -P " + ipmi_password + " sdr | grep -E '" + agrep + "'",shell=True)
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
  ipmistring = "ipmitool -H " + self.hostname + " -U " + ipmi_username + " -P " + ipmi_password + " raw 0x3a 0x01 0x00 0x00 " + rear + " " + rear + " " + front + " " + front + " 0x00 0x00"
  res = check_call(ipmistring,stdout=FNULL,stderr=FNULL,shell=True)
  print sysCheckResults(res)
