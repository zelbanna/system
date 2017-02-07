#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

WWW/HTML interworking module

"""
__author__ = "Zacharias El Banna"                     
__version__ = "1.0"
__status__ = "Production"

import cgi
from sys import stdout
import urllib

################################### Web Items #######################################

class Web(object):
 
 def __init(self):
  pass
 
 def getForm(self):
  return cgi.FieldStorage()
 
 def printCGIHeader(self, atitle,abodystyle):
  print "Content-Type: text/html\r\n"
  print "<HTML><HEAD>"
  print "<TITLE>{}</TITLE>".format(atitle)
  print "<LINK REL='stylesheet' TYPE='text/css' HREF='system.css'></HEAD>"
  print "<BODY id={}>".format(abodystyle)
  stdout.flush()

 def printCGIFooter(self):
  print "</BODY></HTML>"

 def printTableLine(self, acolspan=1):
  print "<TR><TD COLSPAN={}><HR></TD></TR>".format(str(acolspan))

 def printURL(self, aurl):
  sock = urllib.urlopen(aurl)
  html = sock.read()
  sock.close()
  print html
