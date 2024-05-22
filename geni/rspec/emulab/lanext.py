# Copyright (c) 2016-2024 The University of Utah

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import

from ..pg import Request, Namespaces, Link, Request, Node, Interface
import geni.namespaces as GNS
from lxml import etree as ET

class SyncE(object):
    def __init__(self):
        self._synce  = True
        pass

    def _write(self, root):
        if self._synce:
            el = ET.SubElement(root, "{%s}synce" % (Namespaces.EMULAB.name))
            el.attrib["enabled"] = "true"
            pass
        return root

Interface.EXTENSIONS.append(("SyncE", SyncE))
    
class PTP(object):
    def __init__(self):
        self._ptp  = True
        pass

    def _write(self, root):
        if self._ptp:
            el = ET.SubElement(root, "{%s}ptp" % (Namespaces.EMULAB.name))
            el.attrib["enabled"] = "true"
            pass
        return root

Interface.EXTENSIONS.append(("PTP", PTP))
    
class DualModeTrunking(object):
    # This tells the Request class to set the _parent member after creating the
    # object
    __WANTPARENT__ = True;
    
    def __init__(self, nativeVlan = None):
        self._enabled    = True
        self._nativeVlan = nativeVlan;
        pass

    @property
    def _parent(self):
        return self.node

    @_parent.setter
    def _parent(self, link):
        self.link = link
        #link.best_effort = True
        if self._nativeVlan:
            link.vlan_tagging = True
            link.link_multiplexing = True
            pass
        pass
        
    def _write(self, root):
        if self._enabled:
            el = ET.SubElement(root, "{%s}dualmodetrunking" % (Namespaces.EMULAB.name))
            el.attrib["enable"] = "true"
            if self._nativeVlan:
                el.attrib["native_vlan"] = self._nativeVlan.client_id
                pass
        pass
        return root

Link.EXTENSIONS.append(("DualModeTrunking", DualModeTrunking))
