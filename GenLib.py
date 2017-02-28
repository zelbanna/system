#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

Generic Library

"""
__author__ = "Zacharias El Banna"                     
__version__ = "10.0"
__status__ = "Production"

from os import remove, path as ospath, system
from time import sleep, localtime, strftime
from struct import pack, unpack
from socket import inet_ntoa, inet_aton, gethostbyname

################################# Generics ####################################

_sys_debug = False

def sys_set_debug(astate):
 global _sys_debug
 _sys_debug = astate

def sys_get_host(ahost):
 try:
  return gethostbyname(ahost)
 except:
  return None

def sys_ip2int(addr):
 return unpack("!I", inet_aton(addr))[0]
 
def sys_int2ip(addr):
 return inet_ntoa(pack("!I", addr))

def sys_ips2range(addr1,addr2):
 return map(lambda addr: inet_ntoa(pack("!I", addr)), range(unpack("!I", inet_aton(addr1))[0], unpack("!I", inet_aton(addr2))[0] + 1))

def sys_str2hex(arg):
 try:
  return '0x{0:02x}'.format(int(arg))
 except:
  return '0x00'    

def ping_os(ip):
 return system("ping -c 1 -w 1 " + ip + " > /dev/null 2>&1") == 0

def sys_get_results(test):
 return "success" if test else "failure"

def sys_log_msg(amsg, alog='/var/log/system/system.log'):
 if _sys_debug: print "Log: " + amsg
 with open(alog, 'a') as f:
  f.write(unicode("{} : {}\n".format(strftime('%Y-%m-%d %H:%M:%S', localtime()), amsg)))

#
# Lightweight argument parser, returns a dictionary with found arguments - { arg : value }
# Requires - or -- before any argument
#
def simple_arg_parser(args):
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


def sys_write_pidfile(pidfname):
 pidfile = open(pidfname,'w')
 pidfile.write(str(getpid()))
 pidfile.close()

def sys_read_pidfile(pidfname):
 pid = -1
 if ospath.isfile(pidfname):
  pidfile = open(pidfname)
  pid = pidfile.readline().strip('\n')
  pidfile.close()
 return int(pid)

def sys_release_pidfile(pidfname):
 if ospath.isfile(pidfname):
  remove(pidfname)

def sys_lock_pidfile(pidfname, sleeptime):
 while ospath.isfile(pidfname):
  sleep(sleeptime)
 sysWritePidFile(pidfname) 

def sys_file_replace(afile,old,new):
 if afile == "" or new == "" or old == "":
  return False

 filedata = None
 with open(afile, 'r') as f:
  filedata = f.read()

 filedata = filedata.replace(old,new)

 with open(afile, 'w') as f:
  f.write(filedata)
 return True
