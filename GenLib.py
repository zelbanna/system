"""Module docstring.

Generic Library

"""
__author__ = "Zacharias El Banna"
__version__ = "1.0GA"
__status__ = "Production"

from os import remove, path as ospath, system
from time import sleep, localtime, strftime
from struct import pack, unpack
from socket import inet_ntoa, inet_aton, gethostbyname, getfqdn

################################# Generics ####################################

class GenDevice(object):
 
 # set a number of entries:
 # - _ip
 # - _hostname
 # - _domain
 # - _fqdn
 # - name? == hostname when looked up
 
 # Two options:
 # ahost and adomain is set, then FQDN = host.domain and ip is derived
 # if ahost is ip, try to lookup hostname and domain
 #
 # use _ip everywhere we need to connect, use fqdn and domain and host for display purposes
 
 def __init__(self, ahost, adomain = None, atype = "unknown"):
  self._type = atype
  if sys_is_ip(ahost):
   self._ip = ahost
   try:
    self._fqdn = getfqdn(ahost)
    self._hostname = self._fqdn.partition('.')[0]
    self._domain   = self._fqdn.partition('.')[2]
   except:
    self._fqdn = ahost
    self._hostname = ahost
    self._domain = aDomain
  else:
   # ahost is a aname, if domain is not supplied, can it be part of host? 
   if adomain:
    self._fqdn = ahost + "." + adomain
    self._hostname = ahost
    self._domain = adomain
    try:
     self._ip = gethostbyname(self._fqdn)
    except:
     self._ip = gethostbyname(ahost)
   else:
    self._fqdn = ahost
    self._hostname = self._fqdn.partition('.')[0]
    self._domain   = self._fqdn.partition('.')[2]
    try:
     self._ip = gethostbyname(ahost)
    except:
     self._ip = ahost
  if self._domain == "":
   self._domain = None

 def __str__(self):
  return "FQDN: {} IP: {} Hostname: {} Domain: {} Type:{}".format(self._fqdn, self._ip, self._hostname, self._domain, self._type)
 
 def ping_device(self):
  return ping_os(self._fqdn)

 def get_type(self):
  return self._type


class ConfObject(object):

 def __init__(self, aFilename = None):
  self._configitems = {}
  self._filename = aFilename

 def __str__(self):
  return "Configuration: - {}".format(str(self._configitems))

 def load_snmp(self):
  pass

 def load_json(self):
  try:
   self._configitems.clear()
   from json import load as json_load_file
   with open(self._filename) as conffile:
    self._configitems = json_load_file(conffile)
  except:
   pass
   
 def save_json(self):
  from json import dump as json_save_file
  with open(self._filename,'w') as conffile:
    json_save_file(self._configitems, conffile, indent = 1, sort_keys = True)

 def get_json(self):
  from json import dumps as json_get_str
  return json_get_str(self._configitems, indent = 1, sort_keys = True)

 def get_json_to_html(self):
  pass

 def get_keys(self, aTargetName = None, aTargetValue = None, aSortKey = None):
  if not aTargetName:
   keys = self._configitems.keys()
  else:
   keys = []
   for key, entry in self._configitems.iteritems():
    if entry[aTargetName] == aTargetValue:
     keys.append(key)
  keys.sort(key = aSortKey)
  return keys

 def get_entry(self, aKey):
  return self._configitems.get(aKey,None)

 def get_select_entries(self, aKeyList):
  entries = []
  for key in aKeyList:
   entries.append(self._configitems.get(key))
  return entries

 def add_entry(self, aKey, aEntry, aWriteJSON = False):
  self._configitems[aKey] = aEntry
  if aWriteConf:
   if len(self._configitems) == 1:
    self.load_json()
   self.save_json()
 
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

def sys_is_ip(addr):
 try:
  inet_aton(addr)
  return True
 except:
  return False

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
