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
 
 def __init__(self, atitle):
  self._title = atitle
 
 def getForm(self):
  return cgi.FieldStorage()
 
 def printCGIHeader(self):
  print "Content-Type: text/html\r\n"
  print "<HEAD>"
  print "<TITLE>{}</TITLE>".format(self._title)
  print "<LINK REL='stylesheet' TYPE='text/css' HREF='system.css'>"
  print "</HEAD>"
  stdout.flush()

 def printTableLine(self, acolspan=1):
  print "<TR><TD COLSPAN={}><HR></TD></TR>".format(str(acolspan))

 def printURL(self, aurl):
  sock = urllib.urlopen(aurl)
  html = sock.read()
  sock.close()
  print html
