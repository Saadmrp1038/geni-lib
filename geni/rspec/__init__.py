# Copyright (c) 2013  Barnstormer Softworks, Ltd.

from __future__ import absolute_import

from lxml import etree as ET
import geni.namespaces as GNS

class RSpec (object):
  def __init__ (self, rtype):
    self.NSMAP = {}
    self._loclist = []
    self.addNamespace(GNS.XSNS)
    self.type = rtype

  def addNamespace (self, ns, prefix = ""):
    if prefix != "":
      self.NSMAP[prefix] = ns.name
    else:
      self.NSMAP[ns.prefix] = ns.name

    if ns.location is not None:
      self._loclist.append(ns.name)
      self._loclist.append(ns.location)

  def getDOM (self):
    rspec = ET.Element("rspec", nsmap = self.NSMAP)
    rspec.attrib["{%s}schemaLocation" % (GNS.XSNS.name)] = " ".join(self._loclist)
    rspec.attrib["type"] = self.type
    return rspec
