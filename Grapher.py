
#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

Module for graph interaction

Exports:
- Grapher

"""  
__author__ = "Zacharias El Banna"
__version__ = "5.0"
__status__ = "Production"

####################################### Grapher Class ##########################################
#
#

class Grapher(object):

 def __init__(self, aconf='/etc/munin/munin.conf'):
  self._configfile = aconf
  self._configitems = {}
 
 def __str__(self):
  return "ConfigFile:{0} ConfigKeys:[{1}]".format(self._configfile, str(self._configitems.keys()))

 def printHtml(self, asource):
  from time import time
  stop  = int(time())-300
  start = stop - 24*3600 
  print "<A HREF='munin-cgi/munin-cgi-html/static/dynazoom.html?"
  print "cgiurl_graph=/munin-cgi/munin-cgi-graph&plugin_name={0}&size_x=800&size_y=400&start_epoch={1}&stop_epoch={2}' target=sect_cont>".format(asource,str(start),str(stop))
  print "<IMG width=399 height=224 ALT='munin graph:{0}' SRC='/munin-cgi/munin-cgi-graph/{0}-day.png' /></A>".format(asource)

 def widgetCols(self, asources, aclose = False):
  lwidth = 3 if len(asources) < 3 else len(asources)
  print "<DIV CLASS='z-graph' style='width:{}px; height:240px; float:left;'>".format(str(lwidth * 420))
  for src in asources:
   self.printHtml(src)
  if aclose: print "<A class='z-btn z-small-btn' onclick=this.parentElement.style.display='none' style='vertical-align:top;'><B>X</B></A>"
  print "</DIV>"

 def widgetRows(self, asources, aclose = False):
  lheight = 3 if len(asources) < 3 else len(asources)
  print "<DIV CLASS='z-graph' style='width:420px; height:{}px; float:left;'>".format(str(lheight * 240))
  if aclose: print "<A class='z-btn z-small-btn' onclick=this.parentElement.style.display='none' style='float:right;'><B>X</B></A>"
  for src in asources:
   self.printHtml(src)
   print "<BR>"
  print "</DIV>"

 #
 # Config items contains entry: [ handler, updatestate ]
 #
 def loadConf(self):
  # read until find [ ... ] then read two more lines, finally add to dict
  with open(self._configfile) as conffile:
   # Clear old dict first..
   self._configitems = {}
   entry,handler,update = None, None, None
   extra = []
  
   # Modify for arbitrary length! to store more "nice" stuff with Grapher
   #
   for linen in conffile:
    line = linen.strip()
    if entry:
     if line.startswith("address"):
      handler = line[8:]
     elif line.startswith("update"):
      update = line[7:10].strip()
      self._configitems[entry] = [handler, update]
      entry,handler,update = None, None, None
      extra = []
    elif line.startswith("[") and line.endswith("]"):
     entry = line[1:-1]

 def getConfItem(self, aentry):
  if not self._configitems:
   self.loadConf()
  return self._configitems.get(aentry,None)

 def getEntries(self):
  if not self._configitems:
   self.loadConf()
  return self._configitems.keys()
  
 def updateConf(self, aentry, astate):
  oldstate = "no" if astate == "yes" else "yes"
  with open(self._configfile, 'r') as conffile:
   filedata = conffile.read()
 
  pos = filedata.find("[" + aentry + "]")
  old = None
  new = None
  if pos > 0:
   old = filedata[pos:pos + 100].split("[")[1]
   new = old.replace("update " + oldstate, "update " + astate, 1)
   filedata = filedata.replace(old,new)
   with open(self._configfile, 'w') as conffile:
    conffile.write(filedata)
   data = self._configitems.get(aentry,None)
   if data:
    data[1] = astate
    self._configitems[aentry] = data

 def addConf(self, aentry, aupdate, ahandler = '127.0.0.1'):
  with open(self._configfile, 'a') as conffile:
   conffile.write("\n")
   conffile.write("[" + aentry + "]\n")
   conffile.write("address " + ahandler + "\n")
   conffile.write("update " + aupdate + "\n")
  self._configitems[aentry] = [ ahandler, aupdate ]

