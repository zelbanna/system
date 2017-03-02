#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Module docstring.

Module for Rack Utility Classes (Power, UPS, Console)

Exports:
- PDU
- Console

"""  
__author__  = "Zacharias El Banna"
__version__ = "0.1"
__status__  = "Alpha"

class PDU(GenDevice):

 def __init__(self, ahost, adomain):
  GenDevice.__init__(self,ahost,adomain,'pdu')

 def __str__(self):
  return "PDU: {}".format(GenDevice.__str__(self))


class Console(GenDevice):

 def __init__(self, ahost, adomain):
  GenDevice.__init__(self,ahost,adomain,'console')

 def __str__(self):
  return "Console: {}".format(GenDevice.__str__(self))
