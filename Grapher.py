
#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

Module for graph interaction

Exports:
- Grapher

"""  
__author__ = "Zacharias El Banna"
__version__ = "4.0"
__status__ = "Production"

####################################### Grapher Class ##########################################
#
#
#
#

class Grapher(object):

 def __init__(self, aconf='/etc/munin/munin.conf'):
  self._config = aconf
  self._configitems = {}
 
 def __str__(self):
  return "Config: {0}".format(self._config)

 def printHtml(self, asource):
  stop  = int(time())-300
  start = stop - 24*3600 
  print "<A HREF='munin-cgi/munin-cgi-html/static/dynazoom.html?"
  print "cgiurl_graph=/munin-cgi/munin-cgi-graph&plugin_name={0}&size_x=800&size_y=400&start_epoch={1}&stop_epoch={2}' target=sect_cont>".format(asource,str(start),str(stop))
  print "<IMG width=399 height=224 ALT='munin graph:{0}' SRC='/munin-cgi/munin-cgi-graph/{0}-day.png' /></A>".format(asource)

 def widgetCols(self, asources, aclose = False):
  lwidth = 3 if len(asources) < 3 else len(asources)
  print "<DIV CLASS='z-grapher' style='width:{}px; height:240px; float:left;'>".format(str(lwidth * 420))
  for src in asources:
   self.printHtml(src)
  if aclose: print "<A class='z-btn z-small-btn' onclick=this.parentElement.style.display='none' style='vertical-align:top;'><B>X</B></A>"
  print "</DIV>"

 def widgetRows(self, asources, aclose = False):
  lheight = 3 if len(asources) < 3 else len(asources)
  print "<DIV CLASS='z-grapher' style='width:420px; height:{}px; float:left;'>".format(str(lheight * 240))
  if aclose: print "<A class='z-btn z-small-btn' onclick=this.parentElement.style.display='none' style='float:right;'><B>X</B></A>"
  for src in asources:
   self.printHtml(src)
   print "<BR>"
  print "</DIV>"

 def getConf(self):
  with open(self._config) as conffile:
   # read until find [ ... ] then read two more lines, finally add to dict
   foundall = {}
   found = []
  
   # Modify for arbitrary length! to store more "nice" stuff with Grapher
   #
   for linen in conffile:
    line = linen.strip()
    if len(found) == 0 and line.startswith("[") and line.endswith("]"):
     found.append(line[1:-1])
    elif len(found) == 1 and line.startswith("address"):
     found.append(line[8:])
    elif len(found) == 2 and line.startswith("update"):
     found.append(line[7:10].strip())
     foundall[found[0]] = found[1:3]
     found = []
   return foundall
  
 def setConf(self, aname, astate):
  oldstate = "no" if astate == "yes" else "yes"
  with open(self._config, 'r') as conffile:
   filedata = conffile.read()
 
  pos = filedata.find("[" + aname + "]")
  old = None
  new = None
  if pos > 0:
   old = filedata[pos:pos + 100].split("[")[1]
   new = old.replace("update " + oldstate, "update " + astate, 1)
   filedata = filedata.replace(old,new)
   with open(self._config, 'w') as conffile:
    conffile.write(filedata)

 def appendConf(self, aname, aip, aupdate):
  with open(self._config, 'a') as conffile:
   conffile.write("\n")
   conffile.write("[" + aname + "]\n")
   conffile.write("address " + aip + "\n")
   conffile.write("update " + aupdate + "\n")
