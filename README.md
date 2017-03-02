# system
System Functions module for various management tools

This is the backend lib for the web site, it offers interaction for 

- DevESXi - ESXi operations
- DevRouter: wrapper for SNMP and Netconf interaction with J-devices devices
- IPMI
- DNS

etc

A couple of major libs provide classes for the web frontend and general management:

- DevHandler: interface all generic device informartion operations - today is simple textfile based but should be SQL 
- Grapher: wrapper against graphing system
- GenLib: provide generic funcations to all the other libs (IP2Int, pidfile mgmt, logging etc)
